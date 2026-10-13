"""Εργασίες διαχείρισης από τη γραμμή εντολών.

    python -m app.cli create-admin
"""
import argparse
import sys
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import log_event, snapshot
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import User


def create_admin(db: Session, username: str, full_name: str, password: str) -> User:
    if not username or len(username) > 50:
        raise ValueError("Το όνομα χρήστη πρέπει να έχει 1-50 χαρακτήρες")
    if len(password) < settings.min_password_length:
        raise ValueError(f"Ο κωδικός πρέπει να έχει τουλάχιστον {settings.min_password_length} χαρακτήρες")
    if db.scalar(select(User).where(User.Username == username)) is not None:
        raise ValueError(f"Ο χρήστης «{username}» υπάρχει ήδη")

    user = User(Username=username, Full_Name=full_name, Role="ADMIN", Password_Hash=hash_password(password),
                Is_Active=True, Must_Change_Password=False, Failed_Logins=0, Created_By="cli")
    db.add(user)
    db.flush()
    changes = {field: [None, value] for field, value in snapshot(user).items() if value is not None}
    log_event(db, "INSERT", username="cli", table=User.__tablename__, key=f"User_ID={user.User_ID}",
              changes=changes, notes="create-admin")
    db.commit()
    return user


def _create_admin_command() -> int:
    username = input("Όνομα χρήστη: ").strip()
    full_name = input("Ονοματεπώνυμο: ").strip()
    # getpass: ο κωδικός δεν φαίνεται στην οθόνη και δεν μένει στο ιστορικό του shell
    password = getpass("Κωδικός: ")
    if password != getpass("Επανάληψη κωδικού: "):
        print("Οι κωδικοί δεν ταιριάζουν.", file=sys.stderr)
        return 1
    with SessionLocal() as db:
        try:
            user = create_admin(db, username, full_name or username, password)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
    print(f"Δημιουργήθηκε ο ADMIN «{user.Username}».")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_subparsers(dest="command", required=True).add_parser("create-admin", help="Δημιουργεί τον πρώτο ADMIN")
    parser.parse_args()
    return _create_admin_command()


if __name__ == "__main__":
    sys.exit(main())
