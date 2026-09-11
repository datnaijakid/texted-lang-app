import datetime as dt
import json
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user, get_current_verified_user
from app.routers.auth import is_user_pro
from app import models, schemas
from app.llm_client import build_system_prompt, get_ai_reply

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

TURNS_TO_COMPLETE = 6
XP_PER_TURN = 10
XP_COMPLETION_BONUS = 40


def _known_words(db: Session, user_id: str, exclude_ids: List[str]) -> List[str]:
    rows = (
        db.query(models.Vocabulary.term)
        .join(models.UserVocabProgress, models.UserVocabProgress.vocabulary_id == models.Vocabulary.id)
        .filter(models.UserVocabProgress.user_id == user_id, models.UserVocabProgress.repetitions > 0)
        .filter(models.Vocabulary.id.notin_(exclude_ids) if exclude_ids else True)
        .all()
    )
    return [r[0] for r in rows]


def _lesson_words(db: Session, lesson_id: str):
    lesson_words = (
        db.query(models.LessonWord)
        .options(joinedload(models.LessonWord.vocabulary))
        .filter_by(lesson_id=lesson_id)
        .all()
    )
    return [lw.vocabulary for lw in lesson_words]


def _bump_streak_and_xp(db: Session, user: models.User, xp: int):
    today = dt.date.today()
    daily = db.query(models.DailyProgress).filter_by(user_id=user.id, date=today).first()
    if not daily:
        daily = models.DailyProgress(user_id=user.id, date=today, lessons_completed=0, xp_earned=0)
        db.add(daily)

    if user.last_activity_date != today:
        if user.last_activity_date == today - dt.timedelta(days=1):
            user.current_streak += 1
        else:
            user.current_streak = 1
        user.longest_streak = max(user.longest_streak, user.current_streak)
        user.last_activity_date = today

    daily.lessons_completed += 1
    daily.xp_earned += xp
    user.xp += xp


@router.post("/start/{lesson_id}", response_model=schemas.StartConversationResponse)
def start_conversation(
    lesson_id: str,
    current_user: models.User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    lesson = (
        db.query(models.Lesson)
        .options(joinedload(models.Lesson.scenario))
        .filter_by(id=lesson_id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    words = _lesson_words(db, lesson_id)
    new_word_terms = [w.term for w in words]
    known = _known_words(db, current_user.id, exclude_ids=[w.id for w in words])

    learning_lang = db.query(models.Language).filter_by(code=current_user.learning_language_code).first()
    native_lang = db.query(models.Language).filter_by(code=current_user.native_language_code).first()

    system_prompt = build_system_prompt(
        scenario_title=lesson.scenario.title,
        ai_persona=lesson.scenario.ai_persona or "",
        learning_language_name=learning_lang.name if learning_lang else "the target language",
        native_language_name=native_lang.name if native_lang else "English",
        known_words=known,
        new_words=new_word_terms,
    )

    opening = get_ai_reply(system_prompt, history=[], user_message="(start the conversation)", new_words=new_word_terms)

    conversation = models.Conversation(user_id=current_user.id, lesson_id=lesson_id)
    db.add(conversation)
    db.flush()
    db.add(models.Message(conversation_id=conversation.id, sender="ai", content=opening))
    db.commit()

    return schemas.StartConversationResponse(
        conversation_id=conversation.id,
        scenario_title=lesson.scenario.title,
        messaging_style=lesson.scenario.messaging_style,
        opening_message=opening,
    )


@router.get("/{conversation_id}/messages", response_model=List[schemas.MessageOut])
def get_messages(
    conversation_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convo = db.query(models.Conversation).filter_by(id=conversation_id, user_id=current_user.id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return (
        db.query(models.Message)
        .filter_by(conversation_id=conversation_id)
        .order_by(models.Message.created_at)
        .all()
    )


@router.post("/{conversation_id}/messages", response_model=schemas.SendMessageResponse)
def send_message(
    conversation_id: str,
    payload: schemas.SendMessageRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convo = (
        db.query(models.Conversation)
        .options(joinedload(models.Conversation.lesson).joinedload(models.Lesson.scenario))
        .filter_by(id=conversation_id, user_id=current_user.id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if convo.status == "completed":
        raise HTTPException(status_code=400, detail="Conversation already completed")

    words = _lesson_words(db, convo.lesson_id)
    new_word_terms = [w.term for w in words]
    known = _known_words(db, current_user.id, exclude_ids=[w.id for w in words])

    learning_lang = db.query(models.Language).filter_by(code=current_user.learning_language_code).first()
    native_lang = db.query(models.Language).filter_by(code=current_user.native_language_code).first()

    system_prompt = build_system_prompt(
        scenario_title=convo.lesson.scenario.title,
        ai_persona=convo.lesson.scenario.ai_persona or "",
        learning_language_name=learning_lang.name if learning_lang else "the target language",
        native_language_name=native_lang.name if native_lang else "English",
        known_words=known,
        new_words=new_word_terms,
    )

    history_rows = (
        db.query(models.Message)
        .filter_by(conversation_id=conversation_id)
        .order_by(models.Message.created_at)
        .all()
    )
    history = [
        {"role": "assistant" if m.sender == "ai" else "user", "content": m.content}
        for m in history_rows
    ]

    db.add(models.Message(conversation_id=conversation_id, sender="user", content=payload.content))
    convo.turns_completed += 1

    ai_reply = get_ai_reply(system_prompt, history=history, user_message=payload.content, new_words=new_word_terms)
    db.add(models.Message(conversation_id=conversation_id, sender="ai", content=ai_reply))

    xp = XP_PER_TURN
    complete = convo.turns_completed >= TURNS_TO_COMPLETE
    if complete:
        convo.status = "completed"
        convo.completed_at = dt.datetime.utcnow()
        xp += XP_COMPLETION_BONUS
        _bump_streak_and_xp(db, current_user, xp)

    db.commit()

    return schemas.SendMessageResponse(
        user_feedback=None,
        ai_message=ai_reply,
        conversation_complete=complete,
        xp_awarded=xp,
    )


# ==============================================================================
# Instagram-DM Conversational Experience Endpoints
# ==============================================================================

FREE_DAILY_LIMIT = 20


def _check_and_update_usage(db: Session, user: models.User) -> int:
    today = dt.date.today()
    if user.last_message_date != today:
        user.daily_messages_count = 0
        user.last_message_date = today
    return user.daily_messages_count


def _track_event(db: Session, user_id: Optional[str], event_name: str, properties: Optional[dict] = None):
    try:
        ev = models.AnalyticsEvent(
            user_id=user_id,
            event_name=event_name,
            properties=json.dumps(properties or {}),
        )
        db.add(ev)
    except Exception:
        pass


@router.get("/active", response_model=schemas.ActiveConversationResponse)
def get_active_conversation(
    current_user: models.User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    lang_code = current_user.learning_language_code or "es"
    from app.llm_client import get_persona_for_language, PERSONAS
    persona = get_persona_for_language(lang_code)

    convo = (
        db.query(models.Conversation)
        .filter_by(user_id=current_user.id, status="active", language_code=lang_code)
        .order_by(models.Conversation.created_at.desc())
        .first()
    )

    if not convo:
        # Check if there is any legacy conversation with null language_code
        legacy_convo = (
            db.query(models.Conversation)
            .filter(
                models.Conversation.user_id == current_user.id,
                models.Conversation.status == "active",
                models.Conversation.language_code.is_(None),
            )
            .order_by(models.Conversation.created_at.desc())
            .first()
        )
        if legacy_convo:
            legacy_convo.language_code = lang_code
            legacy_convo.persona_name = persona["name"]
            legacy_convo.topic = persona["topic"]
            db.commit()
            convo = legacy_convo

    from app.llm_client import get_opening_message
    expected_opening = get_opening_message(persona, current_user.proficiency_level)

    if convo:
        # If conversation is still at greeting stage (0 user messages), sync to the user's current level
        msgs = db.query(models.Message).filter_by(conversation_id=convo.id).all()
        user_msgs = [m for m in msgs if m.sender == "user"]
        if len(user_msgs) == 0 and len(msgs) > 0:
            msgs[0].content = expected_opening
            db.commit()

    if not convo:
        convo = models.Conversation(
            user_id=current_user.id,
            language_code=lang_code,
            persona_name=persona["name"],
            topic=persona["topic"],
            status="active",
        )
        db.add(convo)
        db.flush()

        opening = models.Message(
            conversation_id=convo.id,
            sender="ai",
            content=expected_opening,
            feedback=None,
        )
        db.add(opening)
        db.commit()
        db.refresh(convo)

    messages = (
        db.query(models.Message)
        .filter_by(conversation_id=convo.id)
        .order_by(models.Message.created_at)
        .all()
    )

    # Dynamic contextual suggested replies
    from app.llm_client import generate_suggested_replies
    last_ai_msg = None
    for m in reversed(messages):
        if m.sender == "ai":
            last_ai_msg = m.content
            break

    suggested = generate_suggested_replies(
        persona,
        last_ai_msg or expected_opening,
        current_user.proficiency_level or "beginner",
    )
    suggested_replies = [schemas.SuggestedReply(**r) for r in suggested]

    return schemas.ActiveConversationResponse(
        conversation_id=convo.id,
        language_code=convo.language_code or lang_code,
        persona_name=convo.persona_name or persona["name"],
        persona_bio=persona.get("bio"),
        topic=convo.topic or "Casual Chat",
        messages=messages,
        suggested_replies=suggested_replies,
    )


@router.post("/reset", response_model=schemas.ActiveConversationResponse)
def reset_conversation(
    current_user: models.User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    lang_code = current_user.learning_language_code or "es"
    from app.llm_client import get_persona_for_language
    persona = get_persona_for_language(lang_code)

    # Mark existing active conversations as completed
    active_convos = (
        db.query(models.Conversation)
        .filter_by(user_id=current_user.id, status="active")
        .all()
    )
    for c in active_convos:
        c.status = "completed"
        c.completed_at = dt.datetime.utcnow()

    # Create fresh conversation
    new_convo = models.Conversation(
        user_id=current_user.id,
        language_code=lang_code,
        persona_name=persona["name"],
        topic=persona["topic"],
        status="active",
    )
    db.add(new_convo)
    db.flush()

    from app.llm_client import get_opening_message, generate_suggested_replies
    opening_text = get_opening_message(persona, current_user.proficiency_level)

    opening = models.Message(
        conversation_id=new_convo.id,
        sender="ai",
        content=opening_text,
        feedback=None,
    )
    db.add(opening)
    db.commit()

    suggested = generate_suggested_replies(
        persona,
        opening_text,
        current_user.proficiency_level or "beginner",
    )
    suggested_replies = [schemas.SuggestedReply(**r) for r in suggested]

    return schemas.ActiveConversationResponse(
        conversation_id=new_convo.id,
        language_code=lang_code,
        persona_name=persona["name"],
        persona_bio=persona.get("bio"),
        topic=new_convo.topic,
        messages=[opening],
        suggested_replies=suggested_replies,
    )


@router.post("/{conversation_id}/chat", response_model=schemas.ChatSendMessageResponse)
def chat_dm(
    conversation_id: str,
    payload: schemas.ChatSendMessageRequest,
    current_user: models.User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    text = payload.content.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    convo = db.query(models.Conversation).filter_by(id=conversation_id, user_id=current_user.id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Authoritative usage limits enforcement for free tier
    is_pro = is_user_pro(current_user)
    today_count = _check_and_update_usage(db, current_user)

    if not is_pro and today_count >= FREE_DAILY_LIMIT:
        _track_event(db, current_user.id, "hit_limit", {"today_count": today_count})
        db.commit()
        raise HTTPException(
            status_code=429,
            detail=f"Daily free limit reached ({FREE_DAILY_LIMIT}/{FREE_DAILY_LIMIT} messages). Upgrade to Pro for unlimited texting!"
        )

    from app.llm_client import get_persona_for_language, get_ai_chat_response

    lang_code = convo.language_code or current_user.learning_language_code or "es"
    persona = get_persona_for_language(lang_code)

    native_lang = db.query(models.Language).filter_by(code=current_user.native_language_code).first()
    native_lang_name = native_lang.name if native_lang else "English"

    # Save user message
    user_msg = models.Message(
        conversation_id=conversation_id,
        sender="user",
        content=text,
        feedback=None,
    )
    db.add(user_msg)
    convo.turns_completed = (convo.turns_completed or 0) + 1
    current_user.daily_messages_count = today_count + 1

    # Fetch recent history
    history_rows = (
        db.query(models.Message)
        .filter_by(conversation_id=conversation_id)
        .order_by(models.Message.created_at.desc())
        .limit(12)
        .all()
    )
    history_rows.reverse()
    history = [
        {"role": "assistant" if m.sender == "ai" else "user", "content": m.content}
        for m in history_rows[:-1]  # exclude just-added user message because it's passed separately
    ]

    # Generate response
    ai_result = get_ai_chat_response(
        persona=persona,
        history=history,
        user_message=text,
        proficiency_level=current_user.proficiency_level or "beginner",
        learning_goal=current_user.learning_goal or "casual",
        native_language_name=native_lang_name,
    )

    ai_reply_text = ai_result.get("reply", "...")
    correction_data = ai_result.get("correction")

    # Store correction on user message feedback if available
    correction_out = None
    if correction_data and isinstance(correction_data, dict):
        correction_out = schemas.CorrectionOut(
            original=correction_data.get("original", text),
            better=correction_data.get("better", ""),
            explanation=correction_data.get("explanation", ""),
        )
        user_msg.feedback = json.dumps(correction_data)

    ai_msg = models.Message(
        conversation_id=conversation_id,
        sender="ai",
        content=ai_reply_text,
        feedback=None,
    )
    db.add(ai_msg)

    # Award XP and streak
    xp = 10
    _bump_streak_and_xp(db, current_user, xp)

    # Milestone analytics
    total_user_msgs = (
        db.query(models.Message)
        .join(models.Conversation, models.Conversation.id == models.Message.conversation_id)
        .filter(models.Conversation.user_id == current_user.id, models.Message.sender == "user")
        .count()
    ) + 1

    if total_user_msgs == 1:
        _track_event(db, current_user.id, "first_user_message")
    elif total_user_msgs == 5:
        _track_event(db, current_user.id, "message_5")
    elif total_user_msgs == 10:
        _track_event(db, current_user.id, "message_10")

    db.commit()
    db.refresh(user_msg)
    db.refresh(ai_msg)

    messages_remaining = 9999 if is_pro else max(0, FREE_DAILY_LIMIT - current_user.daily_messages_count)
    can_send = is_pro or (messages_remaining > 0)

    from app.llm_client import generate_suggested_replies
    suggested = ai_result.get("suggested_replies")
    if not suggested:
        suggested = generate_suggested_replies(
            persona,
            ai_reply_text,
            current_user.proficiency_level or "beginner",
        )
    suggested_replies = [schemas.SuggestedReply(**r) for r in suggested]

    return schemas.ChatSendMessageResponse(
        user_message_id=user_msg.id,
        ai_message_id=ai_msg.id,
        ai_message=ai_reply_text,
        correction=correction_out,
        xp_awarded=xp,
        messages_remaining=messages_remaining,
        can_send=can_send,
        subscription_tier=current_user.subscription_tier or "free",
        suggested_replies=suggested_replies,
    )


@router.post("/translate", response_model=schemas.TranslateResponse)
def translate_message(
    payload: schemas.TranslateRequest,
    current_user: models.User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    LANG_MAP = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "it": "Italian",
        "de": "German",
        "pt": "Portuguese",
        "ja": "Japanese",
    }
    target_code = payload.target_language_code or current_user.native_language_code or "en"
    target_name = LANG_MAP.get(target_code)
    if not target_name:
        lang = db.query(models.Language).filter_by(code=target_code).first()
        target_name = lang.name if lang else "English"

    from app.llm_client import get_translation
    translated = get_translation(payload.text, target_name)

    return schemas.TranslateResponse(
        original_text=payload.text,
        translated_text=translated,
        target_language_name=target_name,
    )
