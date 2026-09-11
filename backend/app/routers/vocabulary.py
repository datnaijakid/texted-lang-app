from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app import models, schemas

router = APIRouter(prefix="/api/vocabulary", tags=["vocabulary"])


@router.get("/search", response_model=List[schemas.VocabularyOut])
def search_vocabulary(
    q: str = Query(min_length=1),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    like = f"%{q.lower()}%"
    return (
        db.query(models.Vocabulary)
        .filter(models.Vocabulary.language_code == current_user.learning_language_code)
        .filter(models.Vocabulary.term.ilike(like))
        .limit(20)
        .all()
    )


@router.get("/notebook", response_model=List[schemas.SavedWordOut])
def get_notebook(
    reason: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(models.SavedWord)
        .options(joinedload(models.SavedWord.vocabulary))
        .filter_by(user_id=current_user.id)
    )
    if reason:
        query = query.filter_by(reason=reason)
    return query.order_by(models.SavedWord.created_at.desc()).all()


@router.post("/notebook/{vocabulary_id}/favorite")
def save_favorite(
    vocabulary_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exists = (
        db.query(models.SavedWord)
        .filter_by(user_id=current_user.id, vocabulary_id=vocabulary_id, reason="favorite")
        .first()
    )
    if not exists:
        db.add(models.SavedWord(user_id=current_user.id, vocabulary_id=vocabulary_id, reason="favorite"))
        db.commit()
    return {"status": "saved"}


@router.post("/save-custom")
def save_custom_word(
    payload: schemas.SaveCustomWordRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lang_code = payload.language_code or current_user.learning_language_code or "es"
    clean_term = payload.term.strip()
    clean_trans = payload.translation.strip()

    vocab = (
        db.query(models.Vocabulary)
        .filter(models.Vocabulary.language_code == lang_code)
        .filter(models.Vocabulary.term.ilike(clean_term))
        .first()
    )
    if not vocab:
        vocab = models.Vocabulary(
            language_code=lang_code,
            term=clean_term,
            translation=clean_trans,
        )
        db.add(vocab)
        db.flush()

    exists = (
        db.query(models.SavedWord)
        .filter_by(user_id=current_user.id, vocabulary_id=vocab.id)
        .first()
    )
    if not exists:
        db.add(models.SavedWord(user_id=current_user.id, vocabulary_id=vocab.id, reason="favorite"))
        db.commit()

    return {"status": "saved", "vocabulary_id": vocab.id}
