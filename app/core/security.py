from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.database.models import User
from app.database.session import get_session


# OAuth2 Bearer token scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
)


# PASSWORD UTILITIES

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password using bcrypt."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    password_bytes = password.encode("utf-8")[:72]  # bcrypt max size
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


# JWT TOKEN CREATION

def create_access_token(
    data: dict, expire_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    expire = (
        datetime.utcnow() + expire_delta
        if expire_delta
        else datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()  # issued at time
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


# AUTH HELPERS

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Return current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        # Ensure user_id is valid UUID
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Fetch user
    result = await session.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# ROLE-BASED ACCESS CONTROL

def require_role(required_role: str):
    """Generic role checker dependency."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user
    return role_checker


async def get_current_buyer(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only buyers can access this"
        )
    return current_user


async def get_current_seller(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "seller":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can access this"
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this"
        )
    return current_user
