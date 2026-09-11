from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app import models, schemas
from app.matching import grade_answer
from app.srs import get_or_create_progress, review_word

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("", response_model=List[schemas.LessonSummary])
def list_lessons(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lessons = (
        db.query(models.Lesson)
        .join(models.Scenario)
        .filter(models.Scenario.language_code == current_user.learning_language_code)
        .order_by(models.Lesson.order_index)
        .all()
    )
    result = []
    for lesson in lessons:
        word_count = db.query(models.LessonWord).filter_by(lesson_id=lesson.id).count()
        result.append(
            schemas.LessonSummary(
                id=lesson.id,
                title=lesson.title,
                scenario_title=lesson.scenario.title,
                word_count=word_count,
            )
        )
    return result


@router.get("/{lesson_id}", response_model=schemas.LessonOut)
def get_lesson(
    lesson_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = (
        db.query(models.Lesson)
        .options(joinedload(models.Lesson.scenario))
        .filter(models.Lesson.id == lesson_id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    lesson_words = (
        db.query(models.LessonWord)
        .options(joinedload(models.LessonWord.vocabulary))
        .filter_by(lesson_id=lesson_id)
        .order_by(models.LessonWord.order_index)
        .all()
    )
    words = [lw.vocabulary for lw in lesson_words]

    return schemas.LessonOut(
        id=lesson.id,
        title=lesson.title,
        scenario=lesson.scenario,
        words=words,
    )


@router.post("/{lesson_id}/memory-check", response_model=schemas.MemoryCheckResult)
def memory_check(
    lesson_id: str,
    answer: schemas.MemoryCheckAnswer,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vocab = db.query(models.Vocabulary).filter_by(id=answer.vocabulary_id).first()
    if not vocab:
        raise HTTPException(status_code=404, detail="Vocabulary item not found")

    grade = grade_answer(answer.answer, vocab.term)

    progress = get_or_create_progress(db, current_user.id, vocab.id)
    review_word(progress, correct=grade.correct)

    if not grade.correct:
        exists = (
            db.query(models.SavedWord)
            .filter_by(user_id=current_user.id, vocabulary_id=vocab.id, reason="mistake")
            .first()
        )
        if not exists:
            db.add(models.SavedWord(user_id=current_user.id, vocabulary_id=vocab.id, reason="mistake"))

    db.commit()

    return schemas.MemoryCheckResult(
        vocabulary_id=vocab.id,
        correct=grade.correct,
        almost=grade.almost,
        correct_answer=vocab.term,
        message=grade.message,
    )
