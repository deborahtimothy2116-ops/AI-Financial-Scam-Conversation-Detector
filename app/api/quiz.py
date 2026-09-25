"""Spot-the-Scam quiz: practise telling SAFE, SUSPICIOUS and SCAM messages apart."""

import random
from typing import List, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.exceptions import NotFoundError
from app.schemas.analysis import VERDICT_LABELS, verdict_for_score
from app.schemas.common import APIResponse
from app.services.highlighter import find_highlights
from app.services.scam_detector import scam_detector
from app.utils.quiz_bank import QUIZ_BANK, QUIZ_BY_ID, quiz_analysis_text

router = APIRouter(prefix="/quiz", tags=["Spot-the-Scam Quiz"])


class QuizQuestion(BaseModel):
    id: str
    channel: str
    sender: str
    message: str


class QuizAnswerRequest(BaseModel):
    question_id: str
    guess: Literal["SAFE", "SUSPICIOUS", "SCAM"]


class QuizAnswerResult(BaseModel):
    question_id: str
    guess: str
    correct: bool
    answer: str
    answer_label: str
    lesson: str
    risk_score: float
    red_flags: List[str]
    highlights: List[dict]


@router.get("/questions", response_model=APIResponse[List[QuizQuestion]])
async def get_quiz_questions(count: int = Query(5, ge=1, le=len(QUIZ_BANK))):
    """Return a random set of practice messages (answers are not included)."""
    picked = random.sample(QUIZ_BANK, count)
    return APIResponse(
        message="Quiz questions ready",
        data=[QuizQuestion(**{k: q[k] for k in ("id", "channel", "sender", "message")}) for q in picked],
    )


@router.post("/answer", response_model=APIResponse[QuizAnswerResult])
async def answer_quiz_question(payload: QuizAnswerRequest):
    """Check a guess and explain the answer using the live detector."""
    question = QUIZ_BY_ID.get(payload.question_id)
    if not question:
        raise NotFoundError("Quiz question")

    result = await scam_detector.analyze(quiz_analysis_text(question))
    answer = question["answer"]
    return APIResponse(
        message="Answer checked",
        data=QuizAnswerResult(
            question_id=question["id"],
            guess=payload.guess,
            correct=payload.guess == answer,
            answer=answer,
            answer_label=VERDICT_LABELS[answer],
            lesson=question["lesson"],
            risk_score=result["risk_score"],
            red_flags=[i.title for i in result["indicators"]],
            highlights=find_highlights(question["message"]),
        ),
    )
