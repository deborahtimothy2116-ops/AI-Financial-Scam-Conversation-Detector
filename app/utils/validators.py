"""Input and file upload security validation utilities."""

import io
from typing import Tuple
from PIL import Image
from fastapi import UploadFile
from app.core.config import settings
from app.core.exceptions import FileProcessingError, ValidationError


# Magic bytes signatures for common image formats
IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",  # RIFF....WEBP
    b"BM": "bmp",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
}


def validate_text_input(text: str) -> str:
    """Validate and sanitize raw text input."""
    if not text or not text.strip():
        raise ValidationError("Input text cannot be empty.")
    
    cleaned = text.strip()
    if len(cleaned) > settings.MAX_TEXT_LENGTH_CHARS:
        raise ValidationError(
            f"Input text exceeds maximum allowed length of {settings.MAX_TEXT_LENGTH_CHARS} characters."
        )
    return cleaned


async def validate_image_upload(file: UploadFile) -> Tuple[bytes, str, int]:
    """Validate uploaded image file type, size, and integrity.
    
    Returns:
        Tuple of (file_bytes, detected_mime_type, file_size_bytes)
    """
    if not file.filename:
        raise FileProcessingError("No filename provided for uploaded file.")

    # Check extension
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise FileProcessingError(
            f"Invalid file extension '.{ext}'. Allowed formats: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # Read bytes with size safety check
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise FileProcessingError("Uploaded file is empty.")

    if file_size > max_bytes:
        raise FileProcessingError(
            f"File size ({file_size / (1024*1024):.2f}MB) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # Verify MIME type header
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in settings.ALLOWED_IMAGE_MIME_TYPES:
        # If content_type was generic octet-stream, we will verify through magic bytes
        if content_type != "application/octet-stream":
            raise FileProcessingError(
                f"Unsupported MIME type '{content_type}'. Allowed types: {', '.join(settings.ALLOWED_IMAGE_MIME_TYPES)}"
            )

    # Validate image integrity and magic bytes with PIL
    try:
        image_stream = io.BytesIO(content)
        with Image.open(image_stream) as img:
            img.verify()  # Verifies file integrity without decoding whole image
            img_format = (img.format or "PNG").lower()
            detected_mime = f"image/{img_format if img_format != 'jpg' else 'jpeg'}"
    except Exception as e:
        raise FileProcessingError(f"Uploaded file is not a valid image or is corrupted: {str(e)}")

    # Reset file cursor just in case
    await file.seek(0)
    return content, detected_mime, file_size
