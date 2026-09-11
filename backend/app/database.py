from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()

db_url = settings.database_url
# Convert postgres:// to postgresql:// for SQLAlchemy 2.0
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = db_url.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
else:
    # Production PostgreSQL / Neon serverless pool settings
    engine = create_engine(
        db_url,
        pool_pre_ping=True,      # Detect dropped/recycled serverless connections
        pool_recycle=300,        # Recycle idle connections every 5 minutes
        pool_size=10,            # Sensible baseline pool
        max_overflow=20,         # Allow burst traffic
        pool_timeout=30,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def migrate_db():
    """Ensure newly added columns and tables exist in existing development and test databases."""
    with engine.connect() as conn:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        if "users" in table_names:
            user_cols = {c["name"] for c in inspector.get_columns("users")}

            if "email_verified" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0"))
            if "stripe_customer_id" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(255)"))
            if "stripe_subscription_id" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(255)"))
            if "subscription_status" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN subscription_status VARCHAR(32) DEFAULT 'inactive'"))
            if "subscription_period_end" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN subscription_period_end DATETIME"))

            if "proficiency_level" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN proficiency_level VARCHAR(32) DEFAULT 'beginner'"))
            if "learning_goal" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN learning_goal VARCHAR(64) DEFAULT 'casual'"))
            if "onboarding_completed" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT 0"))
            if "subscription_tier" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN subscription_tier VARCHAR(16) DEFAULT 'free'"))
            if "daily_messages_count" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN daily_messages_count INTEGER DEFAULT 0"))
            if "last_message_date" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_message_date DATE"))
            if "auto_translate" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN auto_translate BOOLEAN DEFAULT 0"))

        if "conversations" in table_names:
            convo_cols = {c["name"]: c for c in inspector.get_columns("conversations")}
            if "language_code" not in convo_cols:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN language_code VARCHAR(8)"))
            if "persona_name" not in convo_cols:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN persona_name VARCHAR(64) DEFAULT 'Sofia'"))
            if "topic" not in convo_cols:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN topic VARCHAR(128) DEFAULT 'Casual Chat'"))

        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
