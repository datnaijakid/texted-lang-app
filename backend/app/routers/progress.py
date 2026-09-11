from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app import models, schemas

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("", response_model=schemas.ProgressOut)
def get_progress(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    words_learning = (
        db.query(models.UserVocabProgress)
        .filter_by(user_id=current_user.id)
        .filter(models.UserVocabProgress.repetitions > 0)
        .filter(models.UserVocabProgress.repetitions < 5)
        .count()
    )
    words_mastered = (
        db.query(models.UserVocabProgress)
        .filter_by(user_id=current_user.id)
        .filter(models.UserVocabProgress.repetitions >= 5)
        .count()
    )
    return schemas.ProgressOut(
        current_streak=current_user.current_streak,
        longest_streak=current_user.longest_streak,
        xp=current_user.xp,
        words_learning=words_learning,
        words_mastered=words_mastered,
    )
