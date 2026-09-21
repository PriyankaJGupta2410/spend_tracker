"""Business logic and queries for the auth module (users)."""
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import User


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username.strip().lower()))


def create_user(db: Session, username: str, password_hash: str) -> User | None:
    """Returns None if the username is taken. The unique index decides, so races are safe."""

    user = User(
        id=str(uuid4()),
        username=username,
        password_hash=password_hash,
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None

    db.refresh(user)
    return user
