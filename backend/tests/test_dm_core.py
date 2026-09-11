import os
import unittest
import uuid
from fastapi.testclient import TestClient

# Use mock LLM provider during test runs so it is deterministic and offline
os.environ["LLM_PROVIDER"] = "mock"

from app.main import app
from app.database import SessionLocal, Base, engine
from app.rate_limiter import clear_rate_limits
from app import models


class TestDMCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    def setUp(self):
        clear_rate_limits()
        self.email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        self.password = "password123"

        # Register user
        reg_res = self.client.post("/api/auth/register", json={
            "email": self.email,
            "password": self.password,
            "native_language_code": "en",
            "learning_language_code": "es",
        })
        self.assertEqual(reg_res.status_code, 200, reg_res.text)
        self.token = reg_res.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Mark user verified for core DM testing
        db = SessionLocal()
        user = db.query(models.User).filter_by(email=self.email).first()
        user.email_verified = True
        db.commit()
        db.close()

    def test_onboarding_flow(self):
        # 1. Complete onboarding
        onboard_res = self.client.post("/api/auth/onboarding", headers=self.headers, json={
            "learning_language_code": "es",
            "native_language_code": "en",
            "proficiency_level": "beginner",
            "learning_goal": "casual",
            "display_name": "Alex",
        })
        self.assertEqual(onboard_res.status_code, 200)
        data = onboard_res.json()
        self.assertTrue(data["onboarding_completed"])
        self.assertEqual(data["proficiency_level"], "beginner")
        self.assertEqual(data["learning_goal"], "casual")
        self.assertEqual(data["display_name"], "Alex")

        # Check me endpoint reflects it
        me_res = self.client.get("/api/auth/me", headers=self.headers)
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["display_name"], "Alex")

    def test_active_conversation_and_first_message(self):
        # Complete onboarding for Spanish
        self.client.post("/api/auth/onboarding", headers=self.headers, json={
            "learning_language_code": "es",
            "proficiency_level": "beginner",
            "learning_goal": "casual",
        })

        # Fetch active conversation
        active_res = self.client.get("/api/conversations/active", headers=self.headers)
        self.assertEqual(active_res.status_code, 200)
        active_data = active_res.json()
        self.assertEqual(active_data["persona_name"], "Sofia")
        self.assertEqual(active_data["language_code"], "es")
        self.assertGreaterEqual(len(active_data["messages"]), 1)
        self.assertEqual(active_data["messages"][0]["sender"], "ai")
        self.assertIn("Sofia", active_data["messages"][0]["content"])

    def test_send_message_and_subtle_correction(self):
        # Setup conversation
        active_res = self.client.get("/api/conversations/active", headers=self.headers)
        convo_id = active_res.json()["conversation_id"]

        # Send a message with a common beginner mistake ("soy hambriento")
        chat_res = self.client.post(f"/api/conversations/{convo_id}/chat", headers=self.headers, json={
            "content": "¡Hola! soy hambriento mucho"
        })
        self.assertEqual(chat_res.status_code, 200)
        chat_data = chat_res.json()

        # Verify AI message exists
        self.assertTrue(chat_data["ai_message"])
        # Verify subtle correction was generated
        self.assertIsNotNone(chat_data["correction"])
        self.assertEqual(chat_data["correction"]["better"], "Tengo hambre")
        self.assertIn("tener hambre", chat_data["correction"]["explanation"].lower())
        self.assertGreater(chat_data["xp_awarded"], 0)

    def test_empty_message_rejected(self):
        active_res = self.client.get("/api/conversations/active", headers=self.headers)
        convo_id = active_res.json()["conversation_id"]

        # Send empty message
        empty_res = self.client.post(f"/api/conversations/{convo_id}/chat", headers=self.headers, json={
            "content": "   "
        })
        self.assertEqual(empty_res.status_code, 400)

    def test_message_persistence_across_reloads(self):
        active_res = self.client.get("/api/conversations/active", headers=self.headers)
        convo_id = active_res.json()["conversation_id"]

        # Send message
        self.client.post(f"/api/conversations/{convo_id}/chat", headers=self.headers, json={
            "content": "Me gusta la música"
        })

        # Reload conversation
        reload_res = self.client.get("/api/conversations/active", headers=self.headers)
        self.assertEqual(reload_res.status_code, 200)
        msgs = reload_res.json()["messages"]
        user_msgs = [m for m in msgs if m["sender"] == "user"]
        self.assertGreaterEqual(len(user_msgs), 1)
        self.assertEqual(user_msgs[-1]["content"], "Me gusta la música")

    def test_free_tier_limits_and_pro_upgrade(self):
        active_res = self.client.get("/api/conversations/active", headers=self.headers)
        convo_id = active_res.json()["conversation_id"]

        # Check initial usage
        usage_res = self.client.get("/api/usage", headers=self.headers)
        self.assertEqual(usage_res.status_code, 200)
        self.assertEqual(usage_res.json()["tier"], "free")
        self.assertFalse(usage_res.json()["is_pro"])

        # Artificially set daily_messages_count to 20 to test limit enforcement
        db = SessionLocal()
        user = db.query(models.User).filter_by(email=self.email).first()
        user.daily_messages_count = 20
        import datetime as dt
        user.last_message_date = dt.date.today()
        db.commit()
        db.close()

        # Next message should be rejected with 429
        blocked_res = self.client.post(f"/api/conversations/{convo_id}/chat", headers=self.headers, json={
            "content": "One more message please"
        })
        self.assertEqual(blocked_res.status_code, 429)

        # Client-side fake upgrade is rejected
        fake_upgrade_res = self.client.post("/api/usage/upgrade", headers=self.headers, json={"tier": "pro"})
        self.assertEqual(fake_upgrade_res.status_code, 400)

        # Upgrade to Pro authoritatively via DB (simulating verified webhook)
        db = SessionLocal()
        user = db.query(models.User).filter_by(email=self.email).first()
        user.subscription_tier = "pro"
        user.subscription_status = "active"
        db.commit()
        db.close()

        # Check usage now reflects Pro
        usage_res = self.client.get("/api/usage", headers=self.headers)
        self.assertTrue(usage_res.json()["is_pro"])

        # Now message should succeed because user is Pro
        pro_chat_res = self.client.post(f"/api/conversations/{convo_id}/chat", headers=self.headers, json={
            "content": "Now I am Pro!"
        })
        self.assertEqual(pro_chat_res.status_code, 200)

    def test_reset_conversation(self):
        reset_res = self.client.post("/api/conversations/reset", headers=self.headers)
        self.assertEqual(reset_res.status_code, 200)
        data = reset_res.json()
        self.assertEqual(len(data["messages"]), 1)
        self.assertEqual(data["messages"][0]["sender"], "ai")

    def test_analytics_and_funnel(self):
        # Track custom event
        track_res = self.client.post("/api/analytics/event", headers=self.headers, json={
            "event_name": "upgrade_clicked",
            "properties": {"source": "limit_modal"}
        })
        self.assertEqual(track_res.status_code, 200)

        # Get funnel stats with auth header
        funnel_res = self.client.get("/api/analytics/funnel", headers=self.headers)
        self.assertEqual(funnel_res.status_code, 200)
        funnel = funnel_res.json()
        self.assertGreaterEqual(funnel["signups"], 1)
        self.assertGreaterEqual(funnel["upgrade_clicked"], 1)


if __name__ == "__main__":
    unittest.main()
