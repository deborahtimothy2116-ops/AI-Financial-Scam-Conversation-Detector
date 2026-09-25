"""OCR Service Abstraction with Multi-Engine Support (Windows Media OCR + Tesseract + OpenCV)."""

from abc import ABC, abstractmethod
import io
import os
import shutil
from typing import Optional, Tuple
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import winocr
except ImportError:
    winocr = None

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import OCRProcessingError


class BaseOCRService(ABC):
    """Abstract interface for Optical Character Recognition services."""

    @abstractmethod
    async def extract_text(self, image_bytes: bytes, language: Optional[str] = None) -> Tuple[str, float]:
        """Extract text and confidence score from image bytes.
        
        Returns:
            Tuple of (extracted_text, average_confidence_score_0_to_100)
        """
        pass


class MultiEngineOCRService(BaseOCRService):
    """Production-grade multi-engine OCR service.
    
    Supports:
    1. Windows Media OCR (winocr) - Native on Windows 10/11, zero binary install needed.
    2. Tesseract OCR (pytesseract) - Standard on Linux/Docker environments.
    3. OpenCV Image Processing - Grayscale, scaling, bilateral noise removal, thresholding.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.tesseract_cmd = tesseract_cmd or settings.TESSERACT_CMD
        self._tesseract_available = self._check_tesseract()
        self._winocr_available = winocr is not None

        logger.info(
            f"OCR Engines initialized: winocr={self._winocr_available}, "
            f"tesseract={self._tesseract_available}"
        )

    def _check_tesseract(self) -> bool:
        """Check if pytesseract and the tesseract binary are available."""
        if pytesseract is None:
            return False

        if self.tesseract_cmd and os.path.exists(self.tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            return True

        which_tesseract = shutil.which("tesseract")
        if which_tesseract:
            pytesseract.pytesseract.tesseract_cmd = which_tesseract
            return True

        windows_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for path in windows_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                return True

        return False

    def is_available(self) -> bool:
        """Check if at least one OCR engine is ready."""
        return self._winocr_available or self._tesseract_available

    def preprocess_image_for_ocr(self, pil_img: Image.Image) -> Image.Image:
        """Preprocess PIL image for optimal OCR extraction."""
        # Convert to RGB if RGBA/P
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        # Scale up small images for better small-font chat recognition
        w, h = pil_img.size
        if w < 1200 or h < 1200:
            scale = max(2.0, 1200.0 / max(w, h))
            new_w = int(w * scale)
            new_h = int(h * scale)
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.BICUBIC)

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(pil_img)
        enhanced = enhancer.enhance(1.8)

        # Subtle sharpness boost
        sharpener = ImageEnhance.Sharpness(enhanced)
        return sharpener.enhance(1.5)

    def preprocess_opencv(self, image_bytes: bytes) -> np.ndarray:
        """OpenCV binarization pipeline for Tesseract."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img = np.array(pil_img)[:, :, ::-1]

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        if w < 1000 or h < 1000:
            gray = cv2.resize(gray, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)

        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    async def extract_text(self, image_bytes: bytes, language: Optional[str] = None) -> Tuple[str, float]:
        """Extract text from screenshot image using available OCR engines."""
        extracted_text = ""
        confidence = 0.0

        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            raise OCRProcessingError(f"Invalid image format: {str(e)}")

        # 1. Try Windows Media OCR (native on Windows)
        if self._winocr_available:
            try:
                processed_pil = self.preprocess_image_for_ocr(pil_img)
                res = await winocr.recognize_pil(processed_pil)
                if hasattr(res, "text") and res.text:
                    raw_text = res.text.strip()
                elif hasattr(res, "lines"):
                    raw_text = " ".join(line.text for line in res.lines).strip()
                else:
                    raw_text = str(res).strip()

                if len(raw_text) > 3:
                    extracted_text = raw_text
                    confidence = 88.0
                    logger.info(f"WinOCR extracted {len(extracted_text)} characters successfully.")
                    return extracted_text, confidence
            except Exception as e:
                logger.warning(f"WinOCR extraction attempt encountered error: {str(e)}. Trying next engine...")

        # 2. Try Tesseract OCR
        if self._tesseract_available:
            try:
                processed_cv = self.preprocess_opencv(image_bytes)
                lang_param = "eng"
                if language:
                    lang_map = {
                        "en": "eng",
                        "hi": "hin+eng",
                        "ta": "tam+eng",
                        "tam": "tam",
                        "te": "tel",
                    }
                    lang_param = lang_map.get(language.lower(), "eng")

                ocr_data = pytesseract.image_to_data(
                    processed_cv,
                    lang=lang_param,
                    output_type=pytesseract.Output.DICT,
                    config="--psm 6 --oem 3",
                )
                words = []
                confs = []
                for i in range(len(ocr_data["text"])):
                    w = ocr_data["text"][i].strip()
                    c = float(ocr_data["conf"][i])
                    if w and c > 0:
                        words.append(w)
                        confs.append(c)

                if words:
                    extracted_text = " ".join(words).strip()
                    confidence = float(np.mean(confs)) if confs else 75.0
                    logger.info(f"Tesseract OCR extracted {len(extracted_text)} characters.")
                    return extracted_text, confidence
            except Exception as e:
                logger.warning(f"Tesseract OCR attempt failed: {str(e)}")

        # 3. Direct unscaled PIL fallback scan with WinOCR
        if self._winocr_available:
            try:
                res_raw = await winocr.recognize_pil(pil_img)
                raw_t = res_raw.text.strip() if hasattr(res_raw, "text") else ""
                if raw_t:
                    return raw_t, 75.0
            except Exception:
                pass

        # If any extraction produced meaningful text
        if extracted_text and len(extracted_text.strip()) > 3:
            return extracted_text.strip(), max(confidence, 65.0)

        if not extracted_text.strip():
            raise OCRProcessingError(
                "Could not detect any readable text in the uploaded screenshot. "
                "Please make sure the screenshot is clear and contains visible text, or paste the message directly."
            )

        return extracted_text.strip(), confidence


# Export TesseractOCRService alias for backward compatibility
TesseractOCRService = MultiEngineOCRService

# Global singleton instance
ocr_service: BaseOCRService = MultiEngineOCRService()

