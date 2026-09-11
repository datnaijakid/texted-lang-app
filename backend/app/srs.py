import datetime as dt

from app import models


def review_word(progress: models.UserVocabProgress, correct: bool) -> None:
    """
    Simplified SM-2. Called every time a word is tested (Memory Check or in conversation).
    Mutates the given UserVocabProgress row in place; caller commits.
    """
    progress.times_seen += 1
    progress.last_reviewed_at = dt.datetime.utcnow()

    if correct:
        progress.repetitions += 1
        progress.confidence = min(1.0, progress.confidence + 0.15)

        if progress.repetitions == 1:
            progress.interval_days = 1
        elif progress.repetitions == 2:
            progress.interval_days = 3
        else:
            progress.interval_days = round(progress.interval_days * progress.ease_factor, 2)

        progress.ease_factor = max(1.3, progress.ease_factor + 0.05)
    else:
        progress.times_missed += 1
        progress.repetitions = 0
        progress.interval_days = 0.5  # review again soon (within the same day / next session)
        progress.ease_factor = max(1.3, progress.ease_factor - 0.2)
        progress.confidence = max(0.0, progress.confidence - 0.25)

    progress.next_review_at = dt.datetime.utcnow() + dt.timedelta(days=progress.interval_days)


def get_or_create_progress(db, user_id: str, vocabulary_id: str) -> models.UserVocabProgress:
    progress = (
        db.query(models.UserVocabProgress)
        .filter_by(user_id=user_id, vocabulary_id=vocabulary_id)
        .first()
    )
    if not progress:
        progress = models.UserVocabProgress(user_id=user_id, vocabulary_id=vocabulary_id)
        db.add(progress)
        db.flush()
    return progress
