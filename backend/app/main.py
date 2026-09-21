import datetime as dt
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from . import config, services
from .auth import (DUMMY_HASH, create_access_token, get_current_user, hash_password,
                   verify_password)
from .database import get_db, init_db
from .models import User
from .schemas import (ExpenseCreate, ExpenseOut, LoginRequest, Summary, Token, UserCreate,
                      UserOut)

MONTH_PATTERN = r"^(19|20)\d{2}-(0[1-9]|1[0-2])$"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Spend Tracker API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------- consistent error shape: {"error", "message", "details"?} ----------

@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    details = [
        {
            "field": ".".join(str(p) for p in err["loc"][1:]) or str(err["loc"][0]),
            "message": err["msg"].removeprefix("Value error, "),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "message": "Invalid request", "details": details},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "message": exc.detail},
        headers=getattr(exc, "headers", None),
    )


# ---------- public routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    user = services.create_user(db, payload.username, hash_password(payload.password))
    if user is None:
        raise StarletteHTTPException(409, "Username is already taken")
    return user


@app.post("/auth/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = services.get_user_by_username(db, payload.username)
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

@app.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(payload: ExpenseCreate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return services.create_expense(
        db, user_id=user.id, amount=payload.amount, category=payload.category,
        note=payload.note, date=payload.date,
    )


@app.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(
    category: str | None = Query(default=None, max_length=50),
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise StarletteHTTPException(422, "start_date must be on or before end_date")
    return services.list_expenses(
        db, user_id=user.id, category=category, start_date=start_date, end_date=end_date,
        limit=limit, offset=offset,
    )


@app.get("/summary", response_model=Summary)
def summary(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN, examples=["2026-09"]),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return services.build_summary(db, user.id, month or services.current_month())
