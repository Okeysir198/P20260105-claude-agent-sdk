"""SQLite user database module for authentication.

Provides user storage and authentication functionality using SQLite.
Uses bcrypt for secure password hashing.
"""

import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import bcrypt

from agent.core.storage import get_data_dir

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_FILENAME = "users.db"


@dataclass
class DbUser:
    """Data class representing a user in the database."""
    id: str
    username: str
    password_hash: str
    full_name: Optional[str]
    role: str
    created_at: Optional[str]
    last_login: Optional[str]
    is_active: bool


def _get_database_path() -> Path:
    """Get the path to the SQLite database file."""
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / DATABASE_FILENAME


def _get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory configured."""
    db_path = _get_database_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Bcrypt hashed password string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _verify_password_hash(password: str, password_hash: str) -> bool:
    """Verify a password against its hash.

    Args:
        password: Plain text password to verify
        password_hash: Bcrypt hashed password

    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )
    except (ValueError, TypeError) as e:
        logger.error(f"Password verification error: {e}")
        return False


def init_database() -> None:
    """Initialize the database schema and create default users if they don't exist.

    Creates the users table and inserts default admin and test users
    if they are not already present.
    """
    db_path = _get_database_path()
    logger.info(f"Initializing user database at: {db_path}")

    try:
        conn = _get_connection()
        cursor = conn.cursor()

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'user',
                created_at TEXT,
                last_login TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Create index on username for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
        """)

        conn.commit()
        logger.info("Database schema initialized successfully")

        # Insert default users if they don't exist
        _create_default_users(conn)

        conn.close()

    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise


def _create_default_users(conn: sqlite3.Connection) -> None:
    """Create default users if they don't already exist.

    Passwords are loaded from environment variables:
    - CLI_PASSWORD: Password for admin user
    - CLI_TESTER_PASSWORD: Password for tester user

    Users are only created if their respective password env var is set.

    Args:
        conn: Active database connection
    """
    cursor = conn.cursor()

    # Load passwords from environment - no hardcoded defaults for security
    admin_password = os.getenv("CLI_PASSWORD")
    tester_password = os.getenv("CLI_TESTER_PASSWORD")

    default_users = []

    if admin_password:
        default_users.append({
            "username": "admin",
            "password": admin_password,
            "role": "admin",
            "full_name": "Administrator"
        })
    else:
        logger.warning("CLI_PASSWORD not set - admin user will not be created")

    if tester_password:
        default_users.append({
            "username": "tester",
            "password": tester_password,
            "role": "user",
            "full_name": "Test User"
        })
    else:
        logger.warning("CLI_TESTER_PASSWORD not set - tester user will not be created")

    if not default_users:
        logger.warning(
            "No default users created. Set CLI_PASSWORD and/or CLI_TESTER_PASSWORD in .env"
        )
        return

    for user_data in default_users:
        # Check if user already exists
        cursor.execute(
            "SELECT id FROM users WHERE username = ?",
            (user_data["username"],)
        )

        if cursor.fetchone() is None:
            # User doesn't exist, create them
            user_id = str(uuid.uuid4())
            password_hash = hash_password(user_data["password"])
            created_at = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO users (id, username, password_hash, full_name, role, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                user_id,
                user_data["username"],
                password_hash,
                user_data["full_name"],
                user_data["role"],
                created_at
            ))

            logger.info(f"Created default user: {user_data['username']} (role: {user_data['role']})")

    conn.commit()


def get_user_by_username(username: str) -> Optional[DbUser]:
    """Get a user by their username.

    Args:
        username: The username to look up

    Returns:
        DbUser object if found, None otherwise
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, password_hash, full_name, role, created_at, last_login, is_active
            FROM users
            WHERE username = ?
        """, (username,))

        row = cursor.fetchone()
        conn.close()

        if row is None:
            logger.debug(f"User not found: {username}")
            return None

        return DbUser(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            role=row["role"],
            created_at=row["created_at"],
            last_login=row["last_login"],
            is_active=bool(row["is_active"])
        )

    except sqlite3.Error as e:
        logger.error(f"Database error getting user {username}: {e}")
        return None


def verify_password(username: str, password: str) -> bool:
    """Verify a user's password.

    Args:
        username: The username to verify
        password: The plain text password to check

    Returns:
        True if username exists and password is correct, False otherwise
    """
    user = get_user_by_username(username)

    if user is None:
        logger.warning(f"Password verification failed: user not found - {username}")
        return False

    if not user.is_active:
        logger.warning(f"Password verification failed: user inactive - {username}")
        return False

    if _verify_password_hash(password, user.password_hash):
        logger.debug(f"Password verified successfully for user: {username}")
        return True

    logger.warning(f"Password verification failed: incorrect password - {username}")
    return False


def update_last_login(user_id: str) -> None:
    """Update the last login timestamp for a user.

    Args:
        user_id: The user's ID
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()

        last_login = datetime.now().isoformat()

        cursor.execute("""
            UPDATE users
            SET last_login = ?
            WHERE id = ?
        """, (last_login, user_id))

        conn.commit()
        conn.close()

        if cursor.rowcount > 0:
            logger.debug(f"Updated last login for user: {user_id}")
        else:
            logger.warning(f"No user found to update last login: {user_id}")

    except sqlite3.Error as e:
        logger.error(f"Database error updating last login for {user_id}: {e}")
