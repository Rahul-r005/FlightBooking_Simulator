import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .database import SessionLocal, SessionModel, UserModel
from .schemas import LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])

SESSION_COOKIE = "__Host-SkyBookSession"
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "12"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        310_000,
    ).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return salt.hex() + "$" + _hash_password(password, salt)


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    candidate = _hash_password(password, salt)
    return hmac.compare_digest(candidate, digest)


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _set_session_cookie(response: Response, token: str) -> None:
    secure = os.getenv("ENVIRONMENT", "production").lower() != "development"
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=SESSION_TTL_HOURS * 3600,
    )


def _create_session(db: Session, user: UserModel) -> str:
    raw_token = secrets.token_urlsafe(32)
    db.add(
        SessionModel(
            token_digest=_token_digest(raw_token),
            user_id=user.user_id,
            expires_at=_utc_now() + timedelta(hours=SESSION_TTL_HOURS),
        )
    )
    return raw_token


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(lambda: SessionLocal()),
) -> UserModel:
    try:
        if not session_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please sign in to continue.",
            )

        session = (
            db.query(SessionModel)
            .filter(
                SessionModel.token_digest == _token_digest(session_token),
                SessionModel.expires_at > _utc_now(),
            )
            .first()
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please sign in to continue.",
            )

        user = db.get(UserModel, session.user_id)
        if not user or user.suspended:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is unavailable.",
            )
        return user
    finally:
        db.close()


def require_admin(user: UserModel = Depends(get_current_user)) -> UserModel:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return user


@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: RegisterRequest, response: Response, db: Session = Depends(lambda: SessionLocal())):
    try:
        email = request.email.lower().strip()
        if db.query(UserModel).filter(UserModel.email == email).first():
            raise HTTPException(status_code=409, detail="An account with that email already exists.")

        user = UserModel(
            email=email,
            full_name=request.full_name.strip(),
            password_hash=hash_password(request.password),
            role="user",
            suspended=False,
        )
        db.add(user)
        db.flush()
        token = _create_session(db, user)
        db.commit()
        _set_session_cookie(response, token)
        return user
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create the account.") from exc
    finally:
        db.close()


@router.post("/login", response_model=UserResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(lambda: SessionLocal())):
    try:
        user = (
            db.query(UserModel)
            .filter(UserModel.email == request.email.lower().strip())
            .first()
        )
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        if user.suspended:
            raise HTTPException(status_code=403, detail="This account has been suspended.")

        token = _create_session(db, user)
        db.commit()
        _set_session_cookie(response, token)
        return user
    finally:
        db.close()


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(lambda: SessionLocal()),
):
    try:
        if session_token:
            session = (
                db.query(SessionModel)
                .filter(SessionModel.token_digest == _token_digest(session_token))
                .first()
            )
            if session:
                db.delete(session)
                db.commit()
        response.delete_cookie(
            SESSION_COOKIE,
            path="/",
            secure=os.getenv("ENVIRONMENT", "production").lower() != "development",
            httponly=True,
            samesite="lax",
        )
        return {"message": "Signed out."}
    finally:
        db.close()


@router.get("/me", response_model=UserResponse)
def current_user(user: UserModel = Depends(get_current_user)):
    return user
