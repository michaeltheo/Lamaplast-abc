import json

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models import AuditLog, User

# Δεν γράφονται ποτέ στο audit: ο κωδικός και οι στήλες που είναι ήδη audit.
_SKIPPED = {"Password_Hash", "Created_At", "Created_By", "Updated_At", "Updated_By"}


def snapshot(obj) -> dict:
    """Οι τιμές των στηλών ενός αντικειμένου, για το before/after του log_change."""
    return {a.key: getattr(obj, a.key) for a in inspect(obj).mapper.column_attrs if a.key not in _SKIPPED}


def log_event(db: Session, action: str, *, user: User | None = None, username: str | None = None,
              table: str | None = None, key: str | None = None, changes: dict | None = None,
              notes: str | None = None) -> None:
    """Προσθέτει γραμμή στο tbl_AuditLog. Το commit το κάνει ο καλών, μαζί με την αλλαγή."""
    db.add(AuditLog(
        User_ID=user.User_ID if user else None,
        Username=(user.Username if user else username or "")[:50] or None,
        Action=action,
        Table_Name=table,
        Record_Key=key,
        Changes_JSON=json.dumps(changes, ensure_ascii=False, default=str) if changes else None,
        Notes=notes,
    ))


def log_change(db: Session, user: User | None, table: str, key: str,
               before: dict | None, after: dict | None, notes: str | None = None) -> None:
    """before=None → INSERT, after=None → DELETE, αλλιώς UPDATE με μόνο όσα πεδία άλλαξαν."""
    action = "INSERT" if before is None else "DELETE" if after is None else "UPDATE"
    before = {k: v for k, v in (before or {}).items() if k not in _SKIPPED}
    after = {k: v for k, v in (after or {}).items() if k not in _SKIPPED}
    changes = {k: [before.get(k), after.get(k)] for k in sorted(before.keys() | after.keys())
               if before.get(k) != after.get(k)}
    if action == "UPDATE" and not changes and notes is None:
        return
    log_event(db, action, user=user, table=table, key=key, changes=changes, notes=notes)
