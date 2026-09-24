from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.copilot.agent import answer
from app.db.session import get_db

router = APIRouter(prefix="/api")


class Ask(BaseModel):
    question: str
    context_well: int | None = None


@router.post("/copilot")
def copilot(body: Ask, db: Session = Depends(get_db)):
    return answer(db, body.question, body.context_well)
