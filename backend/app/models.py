import datetime as dt
import uuid

from sqlalchemy import (
    Column, String, Integer, Boolean, ForeignKey, DateTime, Text, Float, Date, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Language(Base):
    """Seed table: 'en', 'fr', etc. Kept generic so more languages drop in later."""
    __tablename__ = "languages"

    code = Column(String(8), primary_key=True)  # e.g. "en", "fr"
    name = Column(String(64), nullable=False)   # e.g. "English", "French"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(64), nullable=True)

    email_verified = Column(Boolean, default=False, nullable=False)

    native_language_code = Column(String(8), ForeignKey("languages.code"), nullable=True)
    learning_language_code = Column(String(8), ForeignKey("languages.code"), nullable=True)

    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(Date, nullable=True)
    xp = Column(Integer, default=0)

    proficiency_level = Column(String(32), default="beginner")  # starter | beginner | intermediate | advanced
    learning_goal = Column(String(64), default="casual")        # casual | natural | vocab | grammar | confidence | work
    onboarding_completed = Column(Boolean, default=False)

    # Subscription & Billing
    subscription_tier = Column(String(16), default="free")      # free | pro
    subscription_status = Column(String(32), default="inactive", nullable=False)  # active | trialing | past_due | canceled | inactive
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    subscription_period_end = Column(DateTime, nullable=True)

    daily_messages_count = Column(Integer, default=0)
    last_message_date = Column(Date, nullable=True)
    auto_translate = Column(Boolean, default=False)

    created_at = Column(DateTime, default=dt.datetime.utcnow)

    native_language = relationship("Language", foreign_keys=[native_language_code])
    learning_language = relationship("Language", foreign_keys=[learning_language_code])


class EmailVerificationCode(Base):
    """6-digit verification codes for verifying email address ownership."""
    __tablename__ = "email_verification_codes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    code_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User")


class PasswordResetCode(Base):
    """6-digit verification codes for secure password resets."""
    __tablename__ = "password_reset_codes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    code_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User")


class Vocabulary(Base):
    """A single word/phrase in the target language."""
    __tablename__ = "vocabulary"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    language_code = Column(String(8), ForeignKey("languages.code"), nullable=False, index=True)

    term = Column(String(255), nullable=False, index=True)  # e.g. "bonjour"
    translation = Column(String(255), nullable=False)       # e.g. "friend"
    pronunciation = Column(String(255), nullable=True)       # e.g. "ah-MEE-go"
    example_sentence = Column(Text, nullable=True)           # e.g. "Bonjour, Camille !"
    example_translation = Column(Text, nullable=True)        # e.g. "Hello, Camille!"
    literal_meaning = Column(Text, nullable=True)             # optional
    frequency_rank = Column(Integer, nullable=True)           # lower = more common


class Scenario(Base):
    """A texting scenario, e.g. 'Ordering food', 'Meeting someone'."""
    __tablename__ = "scenarios"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    language_code = Column(String(8), ForeignKey("languages.code"), nullable=False, index=True)
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    messaging_style = Column(String(32), default="imessage")  # imessage | whatsapp | dm
    ai_persona = Column(Text, nullable=True)  # system-prompt flavor text for the AI character
    order_index = Column(Integer, default=0)


class Lesson(Base):
    """A daily lesson built around one Scenario, containing a set of vocabulary."""
    __tablename__ = "lessons"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    scenario_id = Column(String(36), ForeignKey("scenarios.id"), nullable=False, index=True)
    title = Column(String(128), nullable=False)
    order_index = Column(Integer, default=0)

    scenario = relationship("Scenario")


class LessonWord(Base):
    """Join table: which vocabulary words belong to which lesson, in teaching order."""
    __tablename__ = "lesson_words"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    lesson_id = Column(String(36), ForeignKey("lessons.id"), nullable=False, index=True)
    vocabulary_id = Column(String(36), ForeignKey("vocabulary.id"), nullable=False, index=True)
    order_index = Column(Integer, default=0)

    vocabulary = relationship("Vocabulary")

    __table_args__ = (UniqueConstraint("lesson_id", "vocabulary_id", name="uq_lesson_word"),)


class UserVocabProgress(Base):
    """Per-user SRS state for a single vocabulary item (simplified SM-2)."""
    __tablename__ = "user_vocab_progress"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    vocabulary_id = Column(String(36), ForeignKey("vocabulary.id"), nullable=False, index=True)

    ease_factor = Column(Float, default=2.5)
    interval_days = Column(Float, default=0)
    repetitions = Column(Integer, default=0)
    confidence = Column(Float, default=0.0)  # 0-1, rolling
    times_seen = Column(Integer, default=0)
    times_missed = Column(Integer, default=0)

    next_review_at = Column(DateTime, default=dt.datetime.utcnow, index=True)
    last_reviewed_at = Column(DateTime, nullable=True)

    vocabulary = relationship("Vocabulary")

    __table_args__ = (UniqueConstraint("user_id", "vocabulary_id", name="uq_user_vocab"),)


class SavedWord(Base):
    """Personal vocabulary notebook entry (favorite / mistake / recently learned)."""
    __tablename__ = "saved_words"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    vocabulary_id = Column(String(36), ForeignKey("vocabulary.id"), nullable=False, index=True)
    reason = Column(String(32), default="learned")  # learned | mistake | favorite
    created_at = Column(DateTime, default=dt.datetime.utcnow, index=True)

    vocabulary = relationship("Vocabulary")


class Conversation(Base):
    """One chat session for a user (open-ended DM or within a lesson)."""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(String(36), ForeignKey("lessons.id"), nullable=True)
    language_code = Column(String(8), ForeignKey("languages.code"), nullable=True, index=True)
    persona_name = Column(String(64), default="Sofia")
    topic = Column(String(128), default="Casual Chat")

    status = Column(String(16), default="active", index=True)  # active | completed
    turns_completed = Column(Integer, default=0)
    created_at = Column(DateTime, default=dt.datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    lesson = relationship("Lesson")
    language = relationship("Language")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    sender = Column(String(8), nullable=False)  # "user" | "ai"
    content = Column(Text, nullable=False)
    feedback = Column(Text, nullable=True)  # JSON or text containing subtle correction / explanation
    created_at = Column(DateTime, default=dt.datetime.utcnow, index=True)


class DailyProgress(Base):
    """One row per user per calendar day a lesson/conversation was completed. Powers streaks."""
    __tablename__ = "daily_progress"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    lessons_completed = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_day"),)


class AnalyticsEvent(Base):
    """Lightweight product analytics events for measuring onboarding, engagement, and conversion."""
    __tablename__ = "analytics_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    event_name = Column(String(64), nullable=False, index=True)
    properties = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=dt.datetime.utcnow, index=True)
