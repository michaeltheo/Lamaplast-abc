import hashlib
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.models import User

from .config import settings

SESSION_COOKIE = "abc_session"
SESSION_MAX_AGE = settings.session_hours * 3600

_hasher = PasswordHasher()  # argon2id με τις προτεινόμενες παραμέτρους της βιβλιοθήκης
_serializer = URLSafeTimedSerializer(settings.secret_key, salt="session")


def utcnow() -> datetime:
    """Η βάση κρατάει UTC χωρίς ζώνη ώρας (DATETIME2)."""
    return datetime.now(UTC).replace(tzinfo=None)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# Για άγνωστο username κάνουμε έλεγχο πάνω σε αυτό, ώστε η απάντηση να αργεί το ίδιο
# και να μη φαίνεται ποια usernames υπάρχουν.
DUMMY_HASH = hash_password("no-such-user")


def _fingerprint(user: User) -> str:
    """Αλλάζει όταν αλλάξει ο κωδικός → τα παλιά cookies παύουν να ισχύουν."""
    return hashlib.sha256(user.Password_Hash.encode()).hexdigest()[:16]


def create_session_token(user: User) -> str:
    return _serializer.dumps({"uid": user.User_ID, "fp": _fingerprint(user)})


def read_session_token(token: str) -> dict | None:
    try:
        return _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except BadSignature:  # καλύπτει και το ληγμένο (SignatureExpired)
        return None


def token_matches_user(data: dict, user: User) -> bool:
    return data.get("fp") == _fingerprint(user)
