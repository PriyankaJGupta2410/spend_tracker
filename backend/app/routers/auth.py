"""Auth routes: register, login, me."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import config, security
from ..database import get_db
from ..models import User
from ..services.auth import get_user_by_username,create_user
from ..schemas.auth import LoginRequest, Token, UserCreate, UserOut
from ..security import DUMMY_HASH, create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- public routes ----------

@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    user = create_user(db, payload.username, hash_password(payload.password))
    if user is None:
        raise StarletteHTTPException(409, "Username is already taken")
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_username(db, payload.username)
    # Always run a bcrypt check, and give one generic message for both failure cases.
    password_ok = verify_password(payload.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not password_ok:
        raise StarletteHTTPException(
            401, "Invalid username or password", headers={"WWW-Authenticate": "Bearer"}
        )
    return Token(
        access_token=create_access_token(user.id),
        expires_in=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ---------- protected routes (JWT required) ----------

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
