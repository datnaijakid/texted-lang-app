import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


# ---- Auth ----

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: Optional[str] = Field(None, max_length=64)
    native_language_code: Optional[str] = "en"
    learning_language_code: Optional[str] = "fr"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: EmailStr
    display_name: Optional[str]
    native_language_code: Optional[str]
    learning_language_code: Optional[str]
    current_streak: int
    longest_streak: int
    xp: int
    proficiency_level: Optional[str] = "beginner"
    learning_goal: Optional[str] = "casual"
    onboarding_completed: bool = False
    email_verified: bool = False
    subscription_tier: str = "free"
    subscription_status: str = "inactive"
    is_pro: bool = False
    daily_messages_count: int = 0
    auto_translate: bool = False

    class Config:
        from_attributes = True


class OnboardingRequest(BaseModel):
    learning_language_code: str
    native_language_code: Optional[str] = "en"
    proficiency_level: str = "beginner"
    learning_goal: str = "casual"
    display_name: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    learning_language_code: Optional[str] = None
    native_language_code: Optional[str] = None
    proficiency_level: Optional[str] = None
    learning_goal: Optional[str] = None
    auto_translate: Optional[bool] = None


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    target_language_code: Optional[str] = None


class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    target_language_name: str


class SaveCustomWordRequest(BaseModel):
    term: str
    translation: str
    language_code: Optional[str] = None


# ---- Lessons ----

class VocabularyOut(BaseModel):
    id: str
    term: str
    translation: str
    pronunciation: Optional[str]
    example_sentence: Optional[str]
    example_translation: Optional[str]
    literal_meaning: Optional[str]

    class Config:
        from_attributes = True


class ScenarioOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    messaging_style: str

    class Config:
        from_attributes = True


class LessonOut(BaseModel):
    id: str
    title: str
    scenario: ScenarioOut
    words: List[VocabularyOut]

    class Config:
        from_attributes = True


class LessonSummary(BaseModel):
    id: str
    title: str
    scenario_title: str
    word_count: int


# ---- Memory check ----

class MemoryCheckAnswer(BaseModel):
    vocabulary_id: str
    answer: str


class MemoryCheckResult(BaseModel):
    vocabulary_id: str
    correct: bool
    almost: bool  # close but had a typo/missing accent
    correct_answer: str
    message: str


# ---- Conversation ----

class StartConversationResponse(BaseModel):
    conversation_id: str
    scenario_title: str
    messaging_style: str
    opening_message: str


class SendMessageRequest(BaseModel):
    content: str


class SendMessageResponse(BaseModel):
    user_feedback: Optional[str]
    ai_message: str
    conversation_complete: bool
    xp_awarded: int


class MessageOut(BaseModel):
    id: str
    sender: str
    content: str
    feedback: Optional[str] = None
    created_at: dt.datetime

    class Config:
        from_attributes = True


class CorrectionOut(BaseModel):
    original: str
    better: str
    explanation: str


class SuggestedReply(BaseModel):
    label: str
    text: str
    translation: Optional[str] = None


class ActiveConversationResponse(BaseModel):
    conversation_id: str
    language_code: str
    persona_name: str
    persona_bio: Optional[str] = None
    topic: str
    messages: List[MessageOut]
    suggested_replies: List[SuggestedReply] = []


class ChatSendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class ChatSendMessageResponse(BaseModel):
    user_message_id: str
    ai_message_id: str
    ai_message: str
    correction: Optional[CorrectionOut] = None
    xp_awarded: int
    messages_remaining: int
    can_send: bool
    subscription_tier: str
    suggested_replies: List[SuggestedReply] = []


class UsageStatusOut(BaseModel):
    tier: str
    is_pro: bool
    messages_today: int
    daily_limit: int
    messages_remaining: int
    can_send: bool


class CreateCheckoutSessionRequest(BaseModel):
    price_id: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class PortalSessionResponse(BaseModel):
    portal_url: str


class UpgradeRequest(BaseModel):
    tier: str = "pro"


class AnalyticsEventRequest(BaseModel):
    event_name: str
    properties: Optional[dict] = None


class FunnelStatsOut(BaseModel):
    signups: int
    onboarding_completed: int
    first_user_message: int
    message_5: int
    message_10: int
    hit_limit: int
    upgrade_clicked: int
    upgraded: int


# ---- Progress / Vocab notebook ----

class ProgressOut(BaseModel):
    current_streak: int
    longest_streak: int
    xp: int
    words_learning: int
    words_mastered: int


class SavedWordOut(BaseModel):
    vocabulary: VocabularyOut
    reason: str
    created_at: dt.datetime

    class Config:
        from_attributes = True
