"""Shared FastAPI dependencies: current user / current admin from JWTs."""
import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_token
from app.models import AdminUser, User, UserStatus

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise _unauthorized()
    try:
        payload = decode_token(creds.credentials, expected_type="user")
    except pyjwt.PyJWTError:
        raise _unauthorized("Invalid token")
    user = await db.get(User, int(payload["sub"]))
    if user is None:
        raise _unauthorized("User not found")
    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")
    return user


async def get_current_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    if creds is None:
        raise _unauthorized()
    try:
        payload = decode_token(creds.credentials, expected_type="admin_access")
    except pyjwt.PyJWTError:
        raise _unauthorized("Invalid token")
    admin = await db.get(AdminUser, int(payload["sub"]))
    if admin is None or admin.status != "ACTIVE":
        raise _unauthorized("Admin not found")
    return admin
