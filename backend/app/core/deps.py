from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.models import User

from .db import DbSession
from .security import SESSION_COOKIE, read_session_token, token_matches_user


def _forbidden() -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, "Δεν έχεις δικαίωμα για αυτή την ενέργεια")


def get_session_user(request: Request, db: DbSession) -> User:
    """Ο χρήστης του session cookie. Διαβάζεται από τη βάση σε κάθε request,
    ώστε απενεργοποίηση ή αλλαγή ρόλου να ισχύει αμέσως."""
    data = read_session_token(request.cookies.get(SESSION_COOKIE, ""))
    user = db.get(User, data["uid"]) if data else None
    if user is None or not user.Is_Active or not token_matches_user(data, user):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Απαιτείται σύνδεση")
    return user


SessionUser = Annotated[User, Depends(get_session_user)]


def get_current_user(user: SessionUser) -> User:
    """Όπως το get_session_user, αλλά πρώτα πρέπει να έχει αλλάξει τον προσωρινό κωδικό."""
    if user.Must_Change_Password:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Πρέπει πρώτα να αλλάξεις τον κωδικό σου")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    def dependency(user: CurrentUser) -> User:
        if user.Role not in roles:
            raise _forbidden()
        return user
    return dependency


def require_module(module: str, edit: bool = False):
    """ADMIN: όλα. Οι υπόλοιποι: μόνο ενότητες που τους άνοιξε ο Admin· αλλαγές μόνο EXPERT με Can_Edit."""
    def dependency(user: CurrentUser) -> User:
        if user.Role == "ADMIN":
            return user
        permission = next((p for p in user.permissions if p.Module == module), None)
        if permission is None or (edit and not (user.Role == "EXPERT" and permission.Can_Edit)):
            raise _forbidden()
        return user
    return dependency
