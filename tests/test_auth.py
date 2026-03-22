import unittest
from unittest.mock import patch, MagicMock
from datetime import timedelta


# ── helpers ──────────────────────────────────────────────────────────────────

def make_app_config():
    """Return a minimal config object that auth.py needs."""
    cfg = MagicMock()
    cfg.secret_key = "test-secret-key-that-is-long-enough-for-hs256"
    cfg.algorithm = "HS256"
    cfg.access_token_expire_minutes = 30
    return cfg


# ── Test: Password Hashing ────────────────────────────────────────────────────

class TestPasswordHashing(unittest.TestCase):
    """bcrypt hash / verify using the bcrypt library directly."""

    def setUp(self):
        import bcrypt
        self.bcrypt = bcrypt

    def test_hash_is_not_plaintext(self):
        password = "mysecretpassword"
        hashed = self.bcrypt.hashpw(password.encode(), self.bcrypt.gensalt())
        self.assertNotEqual(password.encode(), hashed)

    def test_correct_password_verifies(self):
        password = "mysecretpassword"
        hashed = self.bcrypt.hashpw(password.encode(), self.bcrypt.gensalt())
        result = self.bcrypt.checkpw(password.encode(), hashed)
        self.assertTrue(result)

    def test_wrong_password_fails(self):
        password = "mysecretpassword"
        hashed = self.bcrypt.hashpw(password.encode(), self.bcrypt.gensalt())
        result = self.bcrypt.checkpw(b"wrongpassword", hashed)
        self.assertFalse(result)

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses a random salt — same input should produce different hashes."""
        password = "mysecretpassword"
        hash1 = self.bcrypt.hashpw(password.encode(), self.bcrypt.gensalt())
        hash2 = self.bcrypt.hashpw(password.encode(), self.bcrypt.gensalt())
        self.assertNotEqual(hash1, hash2)


# ── Test: JWT Token ───────────────────────────────────────────────────────────

class TestJWTToken(unittest.TestCase):
    """Create and decode JWT tokens using python-jose."""

    def setUp(self):
        from jose import jwt
        self.jwt = jwt
        self.cfg = make_app_config()

    def _create_token(self, data: dict, expires_delta=None):
        from datetime import datetime, timezone
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta if expires_delta else timedelta(minutes=30)
        )
        to_encode.update({"exp": expire})
        return self.jwt.encode(
            to_encode,
            self.cfg.secret_key,
            algorithm=self.cfg.algorithm,
        )

    def test_token_created_successfully(self):
        token = self._create_token({"sub": "user123"})
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

    def test_token_contains_correct_subject(self):
        token = self._create_token({"sub": "user123"})
        payload = self.jwt.decode(
            token,
            self.cfg.secret_key,
            algorithms=[self.cfg.algorithm],
        )
        self.assertEqual(payload["sub"], "user123")

    def test_expired_token_raises(self):
        from jose import ExpiredSignatureError
        token = self._create_token(
            {"sub": "user123"},
            expires_delta=timedelta(seconds=-1),   # already expired
        )
        with self.assertRaises(ExpiredSignatureError):
            self.jwt.decode(
                token,
                self.cfg.secret_key,
                algorithms=[self.cfg.algorithm],
            )

    def test_tampered_token_raises(self):
        from jose import JWTError
        token = self._create_token({"sub": "user123"})
        tampered = token + "tampered"
        with self.assertRaises(JWTError):
            self.jwt.decode(
                tampered,
                self.cfg.secret_key,
                algorithms=[self.cfg.algorithm],
            )

    def test_wrong_secret_raises(self):
        from jose import JWTError
        token = self._create_token({"sub": "user123"})
        with self.assertRaises(JWTError):
            self.jwt.decode(
                token,
                "wrong-secret",
                algorithms=[self.cfg.algorithm],
            )


# ── Test: Token Payload Fields ────────────────────────────────────────────────

class TestTokenPayload(unittest.TestCase):
    """Ensure tokens carry the right claims."""

    def setUp(self):
        from jose import jwt
        self.jwt = jwt
        self.cfg = make_app_config()

    def _create_token(self, data):
        from datetime import datetime, timezone
        to_encode = data.copy()
        to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=30)
        return self.jwt.encode(
            to_encode,
            self.cfg.secret_key,
            algorithm=self.cfg.algorithm,
        )

    def test_payload_has_exp_field(self):
        token = self._create_token({"sub": "user123"})
        payload = self.jwt.decode(
            token, self.cfg.secret_key, algorithms=[self.cfg.algorithm]
        )
        self.assertIn("exp", payload)

    def test_payload_has_sub_field(self):
        token = self._create_token({"sub": "user@example.com"})
        payload = self.jwt.decode(
            token, self.cfg.secret_key, algorithms=[self.cfg.algorithm]
        )
        self.assertIn("sub", payload)
        self.assertEqual(payload["sub"], "user@example.com")

    def test_extra_claims_preserved(self):
        token = self._create_token({"sub": "user123", "role": "admin"})
        payload = self.jwt.decode(
            token, self.cfg.secret_key, algorithms=[self.cfg.algorithm]
        )
        self.assertEqual(payload.get("role"), "admin")


if __name__ == "__main__":
    unittest.main()