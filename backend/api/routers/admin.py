"""Admin API router.

Provides endpoints for managing platform whitelist, settings, and users.
All endpoints require admin role.
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies.auth import require_admin
from api.models.user_auth import UserTokenPayload
from api.services.whitelist_service import get_whitelist_service
from api.services.settings_service import get_settings_service
from api.db.user_database import (
    get_db_connection,
    get_user_by_username,
    hash_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Pydantic models ---

class WhitelistEntryCreate(BaseModel):
    platform: str
    phone_number: str
    label: str = ""
    mapped_username: str = ""


class WhitelistToggle(BaseModel):
    platform: str
    enabled: bool


class SettingsUpdate(BaseModel):
    settings: dict


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    role: str = "user"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None


# --- Whitelist endpoints ---

@router.get("/whitelist")
async def get_whitelist(admin: UserTokenPayload = Depends(require_admin)):
    """Get all whitelist entries and enabled flags."""
    service = get_whitelist_service()
    return service.list_entries()


@router.post("/whitelist")
async def add_whitelist_entry(
    entry: WhitelistEntryCreate,
    admin: UserTokenPayload = Depends(require_admin),
):
    """Add a new whitelist entry."""
    service = get_whitelist_service()
    created = service.add_entry(
        platform=entry.platform,
        phone_number=entry.phone_number,
        label=entry.label,
        mapped_username=entry.mapped_username,
    )
    # Invalidate identity cache so new mappings take effect
    _invalidate_identity_cache()
    logger.info(f"Admin {admin.username} added whitelist entry: {entry.platform}:{entry.phone_number}")
    return created


@router.delete("/whitelist/{entry_id}")
async def remove_whitelist_entry(
    entry_id: str,
    admin: UserTokenPayload = Depends(require_admin),
):
    """Remove a whitelist entry by ID."""
    service = get_whitelist_service()
    if not service.remove_entry(entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")
    _invalidate_identity_cache()
    logger.info(f"Admin {admin.username} removed whitelist entry: {entry_id}")
    return {"status": "deleted"}


@router.post("/whitelist/toggle")
async def toggle_whitelist(
    toggle: WhitelistToggle,
    admin: UserTokenPayload = Depends(require_admin),
):
    """Enable or disable whitelist for a platform."""
    service = get_whitelist_service()
    service.set_enabled(toggle.platform, toggle.enabled)
    logger.info(
        f"Admin {admin.username} {'enabled' if toggle.enabled else 'disabled'} "
        f"whitelist for {toggle.platform}"
    )
    return {"platform": toggle.platform, "enabled": toggle.enabled}


# --- Settings endpoints ---

@router.get("/settings")
async def get_settings(admin: UserTokenPayload = Depends(require_admin)):
    """Get all platform settings."""
    service = get_settings_service()
    return {"platform": service.get_all()}


@router.put("/settings/platform")
async def update_platform_settings(
    body: SettingsUpdate,
    admin: UserTokenPayload = Depends(require_admin),
):
    """Update platform settings."""
    service = get_settings_service()
    service.update_all(body.settings)
    logger.info(f"Admin {admin.username} updated platform settings: {list(body.settings.keys())}")
    return {"platform": service.get_all()}


# --- User management endpoints ---

@router.get("/users")
async def list_users(admin: UserTokenPayload = Depends(require_admin)):
    """List all users."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, full_name, role, created_at, last_login, is_active FROM users ORDER BY username"
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "username": row["username"],
                "full_name": row["full_name"],
                "role": row["role"],
                "created_at": row["created_at"],
                "last_login": row["last_login"],
                "is_active": bool(row["is_active"]),
            }
            for row in rows
        ]


@router.post("/users")
async def create_user(
    user: UserCreate,
    admin: UserTokenPayload = Depends(require_admin),
):
    """Create a new user."""
    existing = get_user_by_username(user.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(user.password)
    created_at = datetime.now().isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO users (id, username, password_hash, full_name, role, created_at, is_active)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (user_id, user.username, pw_hash, user.full_name, user.role, created_at),
        )
        conn.commit()

    logger.info(f"Admin {admin.username} created user: {user.username} (role={user.role})")
    return {
        "id": user_id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "created_at": created_at,
        "is_active": True,
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    update: UserUpdate,
    admin: UserTokenPayload = Depends(require_admin),
):
    """Update a user's role, status, or password."""
    updates: list[str] = []
    params: list = []

    if update.full_name is not None:
        updates.append("full_name = ?")
        params.append(update.full_name)
    if update.role is not None:
        updates.append("role = ?")
        params.append(update.role)
    if update.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if update.is_active else 0)
    if update.password is not None:
        updates.append("password_hash = ?")
        params.append(hash_password(update.password))

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(user_id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"Admin {admin.username} updated user {user_id}: {updates}")
    return {"status": "updated"}


def _invalidate_identity_cache() -> None:
    """Invalidate the platform identity mapping cache."""
    try:
        from platforms.identity import invalidate_identity_cache
        invalidate_identity_cache()
    except ImportError:
        pass
