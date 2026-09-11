"""
Seeds enough data to run the MVP end to end: English -> French,
one scenario ("Meeting a new friend online") with a full lesson.

Run with: python -m app.seed_data
"""
from app.database import SessionLocal, engine, Base
from app import models


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        langs = [
            ("en", "English"),
            ("es", "Spanish"),
            ("fr", "French"),
            ("it", "Italian"),
            ("de", "German"),
            ("ja", "Japanese"),
        ]
        for code, name in langs:
            if not db.query(models.Language).filter_by(code=code).first():
                db.add(models.Language(code=code, name=name))
        db.commit()

        scenario = (
            db.query(models.Scenario)
            .filter_by(language_code="fr", title="French basics: meeting someone new")
            .first()
        )
        if scenario:
            scenario.description = "Camille has just texted the learner because she is excited to get to know them."
            scenario.ai_persona = (
                "You are 'Camille', a friendly 24-year-old from Paris who has just texted the learner "
                "because you are eager to get to know them. Open with: 'Bonjour ! Je m'appelle Camille. "
                "Enchantée ! Comment tu t'appelles ?' Keep every message short, warm, and limited to "
                "beginner French introductions."
            )
            db.commit()
            print("French demo content already seeded, updated scenario details.")
            return

        scenario = models.Scenario(
            language_code="fr",
            title="French basics: meeting someone new",
            description="Camille has just texted the learner because she is excited to get to know them.",
            messaging_style="dm",
            ai_persona=(
                "You are 'Camille', a friendly 24-year-old from Paris who has just texted the learner "
                "because you are eager to get to know them. Open with: 'Bonjour ! Je m'appelle Camille. "
                "Enchantée ! Comment tu t'appelles ?' Keep every message short, warm, and limited to "
                "beginner French introductions."
            ),
            order_index=0,
        )
        db.add(scenario)
        db.flush()

        lesson = models.Lesson(scenario_id=scenario.id, title="Say hello and introduce yourself", order_index=0)
        db.add(lesson)
        db.flush()

        vocab_data = [
            ("bonjour", "hello / good morning", "bohn-ZHOOR", "Bonjour ! Comment ça va ?", "Hello! How are you?", None),
            ("salut", "hi / bye", "sah-LUU", "Salut, Camille !", "Hi, Camille!", None),
            ("comment ça va ?", "how are you?", "koh-MAH sah VAH", "Bonjour ! Comment ça va aujourd'hui ?", "Hello! How are you today?", None),
            ("ça va bien", "I'm well", "sah VAH byen", "Ça va bien, merci.", "I'm well, thanks.", None),
            ("je m'appelle", "my name is", "zhuh mah-PELL", "Je m'appelle Alex.", "My name is Alex.", "I call myself"),
            ("enchanté(e)", "nice to meet you", "ahn-shahn-TAY", "Enchantée, Camille.", "Nice to meet you, Camille.", "delighted"),
            ("tu viens d'où ?", "where are you from?", "tew VYEN DOO", "Tu viens d'où ?", "Where are you from?", None),
            ("j'habite à", "I live in", "zhah-BEET ah", "J'habite à Toronto.", "I live in Toronto.", None),
            ("j'aime", "I like", "zhem", "J'aime la musique.", "I like music.", None),
            ("moi aussi", "me too", "mwah oh-SEE", "Moi aussi, j'aime la musique !", "Me too, I like music!", None),
        ]

        for i, (term, translation, pron, ex, ex_t, literal) in enumerate(vocab_data):
            v = models.Vocabulary(
                language_code="fr",
                term=term,
                translation=translation,
                pronunciation=pron,
                example_sentence=ex,
                example_translation=ex_t,
                literal_meaning=literal,
                frequency_rank=i + 1,
            )
            db.add(v)
            db.flush()
            db.add(models.LessonWord(lesson_id=lesson.id, vocabulary_id=v.id, order_index=i))

        db.commit()
        print("Seeded languages, one scenario, one lesson, and 10 vocabulary words.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
