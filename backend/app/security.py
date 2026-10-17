"""Auth utilities: password hashing, JWT creation and verification."""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

DEV_USER_EMAIL = "dev@local"


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _get_or_create_dev_user(db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.email == DEV_USER_EMAIL).first()
    if not user:
        user = models.User(email=DEV_USER_EMAIL, hashed_password="", full_name="Dev User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    # No token → return dev user
    if not token:
        return _get_or_create_dev_user(db)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email:
            user = db.query(models.User).filter(models.User.email == email).first()
            if user:
                return user
    except JWTError:
        pass
    return _get_or_create_dev_user(db)
