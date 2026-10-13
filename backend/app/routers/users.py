from typing import Annotated

from app.core.audit import log_change, log_event, snapshot
from app.core.db import DbSession
from app.core.deps import require_role
from app.core.pagination import Pagination, paginate
from app.core.security import hash_password
from app.core.responses import ok
from app.models import User, UserPermission
from app.schemas.auth import UserOut
from app.schemas.pagination import Page
from app.schemas.users import PermissionIn, UserCreate, UserUpdate
from app.schemas.response import ApiResponse
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

router = APIRouter(prefix="/api/users", tags=["Users"])

AdminUser = Annotated[User, Depends(require_role("ADMIN"))]


def _key(user: User) -> str:
    return f"User_ID={user.User_ID}"


def _get_or_404(db: DbSession, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ο χρήστης δεν βρέθηκε")
    return user


@router.get("", response_model=ApiResponse[Page[UserOut]])
def list_users(p: Pagination, db: DbSession, admin: AdminUser):
    return ok(paginate(db, select(User).order_by(User.Username), p))


@router.post("", response_model=ApiResponse[UserOut], status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: DbSession, admin: AdminUser):
    if db.scalar(select(User).where(User.Username == body.Username)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Το όνομα χρήστη υπάρχει ήδη")

    user = User(**body.model_dump(exclude={"password"}), Password_Hash=hash_password(body.password),
                Is_Active=True, Must_Change_Password=True, Failed_Logins=0, Created_By=admin.Username)
    db.add(user)
    db.flush()
    log_change(db, admin, User.__tablename__, _key(user), None, snapshot(user))
    db.commit()
    return ok(user, status.HTTP_201_CREATED)


@router.put("/{user_id}", response_model=ApiResponse[UserOut])
def update_user(user_id: int, body: UserUpdate, db: DbSession, admin: AdminUser):
    user = _get_or_404(db, user_id)
    fields = body.model_dump(exclude_unset=True, exclude={"password", "unlock"})

    # Αρκεί αυτός ο έλεγχος για να μένει πάντα ένας ενεργός ADMIN: όποιος κάνει την αλλαγή είναι ADMIN.
    if user.User_ID == admin.User_ID and (
            fields.get("Role", "ADMIN") != "ADMIN" or fields.get("Is_Active", True) is False):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Δεν μπορείς να αφαιρέσεις τον ρόλο ADMIN ή να απενεργοποιήσεις τον εαυτό σου")

    if body.unlock and (user.Locked_Until or user.Failed_Logins):
        user.Locked_Until, user.Failed_Logins = None, 0
        log_event(db, "UNLOCK", user=admin, table=User.__tablename__, key=_key(user))

    before = snapshot(user)
    for field, value in fields.items():
        if value is None and field != "Email":
            continue
        setattr(user, field, value)
    notes = None
    if body.password is not None:
        user.Password_Hash = hash_password(body.password)
        user.Must_Change_Password = True
        notes = "επαναφορά κωδικού"
    user.Updated_By = admin.Username
    log_change(db, admin, User.__tablename__, _key(user), before, snapshot(user), notes=notes)
    db.commit()
    return ok(user)


@router.put("/{user_id}/permissions", response_model=ApiResponse[UserOut])
def set_permissions(user_id: int, body: list[PermissionIn], db: DbSession, admin: AdminUser):
    user = _get_or_404(db, user_id)
    wanted = {p.Module: p.Can_Edit for p in body}
    if len(wanted) != len(body):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Η ίδια ενότητα δόθηκε δύο φορές")

    before = {p.Module: p.Can_Edit for p in user.permissions}
    current = {p.Module: p for p in user.permissions}
    for module, can_edit in wanted.items():
        if module in current:
            current[module].Can_Edit = can_edit
            current[module].Updated_By = admin.Username
        else:
            current[module] = UserPermission(Module=module, Can_Edit=can_edit, Created_By=admin.Username)
    user.permissions = [current[m] for m in sorted(wanted)]

    log_change(db, admin, UserPermission.__tablename__, _key(user), before, wanted)
    db.commit()
    return ok(user)
