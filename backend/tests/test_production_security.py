import datetime as dt
import os
import unittest
import uuid
from fastapi.testclient import TestClient

os.environ["LLM_PROVIDER"] = "mock"

from app.main import app
from app.database import SessionLocal, Base, engine
from app.rate_limiter import clear_rate_limits
from app.security import hash_code, hash_password
from app import models


class TestProductionSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    def setUp(self):
        clear_rate_limits()
        self.email = f"sec_{uuid.uuid4().hex[:8]}@example.com"
        self.password = "Secur3P@ssw0rd!"

    def test_signup_creates_unverified_account_and_sets_cookie(self):
        res = self.client.post("/api/auth/register", json={
            "email": self.email,
            "password": self.password,
            "native_language_code": "en",
            "learning_language_code": "es",
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("access_token", res.json())
        # Check Set-Cookie
        self.assertIn("access_token", res.cookies)

        # Verify DB state
        db = SessionLocal()
        user = db.query(models.User).filter_by(email=self.email).first()
        self.assertIsNotNone(user)
        self.assertFalse(user.email_verified)

        # Check that verification code was generated in DB
        code_record = db.query(models.EmailVerificationCode).filter_by(user_id=user.id).first()
        self.assertIsNotNone(code_record)
        self.assertIsNone(code_record.used_at)
        db.close()

    def test_unverified_user_cannot_access_conversation(self):
        res = self.client.post("/api/auth/register", json={
            "email": self.email,
            "password": self.password,
            "native_language_code": "en",
            "learning_language_code": "es",
        })
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to access active conversation before verification
        conv_res = self.client.get("/api/conversations/active", headers=headers)
        self.assertEqual(conv_res.status_code, 403)
        self.assertIn("verify your email", conv_res.json()["detail"].lower())

    def test_email_verification_flow_and_attempt_limit(self):
        res = self.client.post("/api/auth/register", json={
            "email": self.email,
            "password": self.password,
            "native_language_code": "en",
            "learning_language_code": "es",
        })
        self.assertEqual(res.status_code, 200)

        # 1. Invalid verification code
        bad_res = self.client.post("/api/auth/verify-email", json={
            "email": self.email,
            "code": "000000",
        })
        self.assertEqual(bad_res.status_code, 400)
        self.assertIn("attempt(s) remaining", bad_res.json()["detail"])

        # Inject known code into DB
        db = SessionLocal()
        user = db.query(models.User).filter_by(email=self.email).first()
        record = db.query(models.EmailVerificationCode).filter_by(user_id=user.id).first()
        record.code_hash = hash_code("654321")
        db.commit()
        db.close()

        # 2. Correct code
        good_res = self.client.post("/api/auth/verify-email", json={
            "email": self.email,
            "code": "654321",
        })
        self.assertEqual(good_res.status_code, 200)

        # 3. User is now verified in DB
        db = SessionLocal()
        user = db.query(models.User).filter_by(email=self.email).first()
        self.assertTrue(user.email_verified)
        db.close()

    def test_password_reset_flow(self):
        # Register user
        self.client.post("/api/auth/register", json={
            "email": self.email,
            "password": self.password,
            "native_language_code": "en",
            "learning_language_code": "es",
        })

        # 1. Request forgot password
        forgot_res = self.client.post("/api/auth/forgot-password", json={"email": self.email})
        self.assertEqual(forgot_res.status_code, 200)
        self.assertIn("password reset instructions have been sent", forgot_res.json()["message"])

        # Non-existent email gets same response (enumeration protection)
        anon_res = self.client.post("/api/auth/forgot-password", json={"email": "nonexistent@example.com"})
        self.assertEqual(anon_res.status_code, 200)
        self.assertEqual(anon_res.json()["message"], forgot_res.json()["message"])

        # Set known reset code
        db = SessionLocal()
        user = db.query(models.User).filter_by(email=self.email).first()
        record = db.query(models.PasswordResetCode).filter_by(user_id=user.id).first()
        record.code_hash = hash_code("987654")
        db.commit()
        db.close()

        # 2. Reset password with weak password fails
        weak_res = self.client.post("/api/auth/reset-password", json={
            "email": self.email,
            "code": "987654",
            "new_password": "short",
        })
        self.assertEqual(weak_res.status_code, 422)  # Pydantic schema validation

        # 3. Reset with valid password and correct code
        new_pw = "BrandNewStrongP@ss99!"
        reset_res = self.client.post("/api/auth/reset-password", json={
            "email": self.email,
            "code": "987654",
            "new_password": new_pw,
        })
        self.assertEqual(reset_res.status_code, 200)

        # 4. Old password fails login
        old_login = self.client.post("/api/auth/login", data={"username": self.email, "password": self.password})
        self.assertEqual(old_login.status_code, 401)

        # 5. New password succeeds login
        new_login = self.client.post("/api/auth/login", data={"username": self.email, "password": new_pw})
        self.assertEqual(new_login.status_code, 200)

    def test_user_data_isolation(self):
        # User A
        email_a = f"usera_{uuid.uuid4().hex[:8]}@example.com"
        reg_a = self.client.post("/api/auth/register", json={
            "email": email_a,
            "password": "PasswordA123!",
            "native_language_code": "en",
            "learning_language_code": "es",
        })
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # User B
        email_b = f"userb_{uuid.uuid4().hex[:8]}@example.com"
        reg_b = self.client.post("/api/auth/register", json={
            "email": email_b,
            "password": "PasswordB123!",
            "native_language_code": "en",
            "learning_language_code": "es",
        })
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Verify both users
        db = SessionLocal()
        db.query(models.User).filter(models.User.email.in_([email_a, email_b])).update({"email_verified": True})
        db.commit()
        db.close()

        # User A gets active conversation
        conv_a = self.client.get("/api/conversations/active", headers=headers_a).json()
        convo_id_a = conv_a["conversation_id"]

        # User B attempts to chat into User A's conversation -> MUST return 404 (Not Found / isolated)
        hack_res = self.client.post(f"/api/conversations/{convo_id_a}/chat", headers=headers_b, json={
            "content": "Trying to spy on user A"
        })
        self.assertEqual(hack_res.status_code, 404)

    def test_stripe_webhook_signature_verification(self):
        from app.config import get_settings
        get_settings().stripe_webhook_secret = "whsec_test1234567890"

        # Sending arbitrary POST to /api/billing/webhook without signature header
        no_sig_res = self.client.post("/api/billing/webhook", content=b'{"type":"checkout.session.completed"}')
        self.assertEqual(no_sig_res.status_code, 400)

        # Sending invalid signature
        bad_sig_res = self.client.post(
            "/api/billing/webhook",
            content=b'{"type":"checkout.session.completed"}',
            headers={"stripe-signature": "t=12345,v1=invalidsig"},
        )
        self.assertEqual(bad_sig_res.status_code, 400)

    def test_health_and_readiness_probes(self):
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")

        ready = self.client.get("/api/ready")
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "ready")
        self.assertEqual(ready.json()["database"], "connected")


if __name__ == "__main__":
    unittest.main()
