from datetime import timedelta

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import log_change, log_event
from app.core.config import settings
from app.core.db import DbSession
from app.core.deps import SessionUser
from app.core.responses import ok
from app.core.security import (
    DUMMY_HASH,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    create_session_token,
    hash_password,
    needs_rehash,
    utcnow,
    verify_password,
)
from app.models import User
from app.schemas.auth import ChangePasswordIn, LoginIn, UserOut
from app.schemas.response import ApiResponse

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(SESSION_COOKIE, create_session_token(user), max_age=SESSION_MAX_AGE,
                        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")


def _fail(db: Session, body: LoginIn, user: User | None, reason: str):
    log_event(db, "LOGIN_FAILED", user=user, username=body.username, notes=reason)
    db.commit()
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Λάθος όνομα χρήστη ή κωδικός")


@router.post("/login", response_model=ApiResponse[UserOut])
def login(body: LoginIn, response: Response, db: DbSession):
    # UPDLOCK: δύο ταυτόχρονες δοκιμές για τον ίδιο χρήστη δεν χάνουν μέτρημα αποτυχιών
    user = db.scalar(select(User).where(User.Username == body.username)
                     .with_hint(User, "WITH (UPDLOCK, ROWLOCK)", "mssql"))
    now = utcnow()

    if user is None:
        verify_password(DUMMY_HASH, body.password)
        _fail(db, body, None, "άγνωστος χρήστης")
    if not user.Is_Active:
        _fail(db, body, user, "ανενεργός λογαριασμός")
    if user.Locked_Until and user.Locked_Until > now:
        _fail(db, body, user, "κλειδωμένος λογαριασμός")

    if not verify_password(user.Password_Hash, body.password):
        user.Failed_Logins += 1
        if user.Failed_Logins >= settings.max_failed_logins:
            user.Failed_Logins = 0
            user.Locked_Until = now + timedelta(minutes=settings.lockout_minutes)
            log_event(db, "LOCK", user=user, table=User.__tablename__, key=f"User_ID={user.User_ID}",
                      notes=f"{settings.max_failed_logins} λάθος κωδικοί")
        _fail(db, body, user, "λάθος κωδικός")

    if needs_rehash(user.Password_Hash):
        user.Password_Hash = hash_password(body.password)
    user.Failed_Logins = 0
    user.Locked_Until = None
    user.Last_Login_At = now
    log_event(db, "LOGIN", user=user)
    db.commit()

    _set_session_cookie(response, user)
    return ok(user)


@router.post("/logout", response_model=ApiResponse[None])
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return ok(message="Αποσυνδέθηκες")


@router.get("/me", response_model=ApiResponse[UserOut])
def me(user: SessionUser):
    return ok(user)


@router.post("/change-password", response_model=ApiResponse[None])
def change_password(body: ChangePasswordIn, response: Response,
                    user: SessionUser, db: DbSession):
    if not verify_password(user.Password_Hash, body.current_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ο τρέχων κωδικός δεν είναι σωστός")
    if body.new_password == body.current_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ο νέος κωδικός πρέπει να διαφέρει από τον τρέχοντα")

    user.Password_Hash = hash_password(body.new_password)
    user.Must_Change_Password = False
    user.Updated_By = user.Username
    log_change(db, user, User.__tablename__, f"User_ID={user.User_ID}", {}, {}, notes="αλλαγή κωδικού")
    db.commit()

    # Ο νέος κωδικός ακυρώνει όλα τα παλιά cookies· αυτό το session παίρνει καινούριο.
    _set_session_cookie(response, user)
    return ok(message="Ο κωδικός άλλαξε")
