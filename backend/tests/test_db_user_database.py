"""
Unit tests for user_database.py module.

Tests cover:
- Database initialization
- User creation (admin and regular users)
- User authentication
- User lookup by username
- Password hashing and verification
- Update last login
- All error paths

Uses in-memory SQLite database for isolation.
"""
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import bcrypt

from api.db.user_database import (
    DbUser,
    _create_default_users,
    _get_connection,
    _get_database_path,
    _verify_password_hash,
    get_db_connection,
    get_user_by_username,
    hash_password,
    init_database,
    update_last_login,
    verify_password,
)


class TestHashPassword:
    """Test password hashing functionality."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_is_different_each_time(self):
        """Test that hashing the same password produces different hashes (due to salt)."""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different salts produce different hashes

    def test_hash_password_contains_bcrypt_format(self):
        """Test that hashed password follows bcrypt format."""
        password = "test_password_123"
        hashed = hash_password(password)

        # Bcrypt hashes start with $2b$, $2a$, or $2y$
        assert hashed.startswith("$2")

    def test_hash_password_with_empty_string(self):
        """Test hashing an empty password."""
        password = ""
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0


class TestVerifyPasswordHash:
    """Test password verification functionality."""

    def test_verify_correct_password(self):
        """Test verification with correct password."""
        password = "test_password_123"
        hashed = hash_password(password)

        result = _verify_password_hash(password, hashed)
        assert result is True

    def test_verify_incorrect_password(self):
        """Test verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        result = _verify_password_hash(wrong_password, hashed)
        assert result is False

    def test_verify_with_empty_password(self):
        """Test verification with empty password."""
        password = ""
        hashed = hash_password(password)

        result = _verify_password_hash("", hashed)
        assert result is True

    def test_verify_with_invalid_hash(self):
        """Test verification with invalid hash format."""
        password = "test_password_123"
        invalid_hash = "invalid_hash_format"

        result = _verify_password_hash(password, invalid_hash)
        assert result is False

    def test_verify_with_none_values(self):
        """Test verification with None values raises AttributeError (uncaught bug)."""
        # The current implementation only catches ValueError and TypeError
        # but None.encode() raises AttributeError, which is NOT caught.
        # This documents the actual behavior - a bug in the implementation.
        with pytest.raises(AttributeError):
            _verify_password_hash(None, "some_hash")

        with pytest.raises(AttributeError):
            _verify_password_hash("password", None)


class TestGetDatabasePath:
    """Test database path resolution."""

    @patch("api.db.user_database.get_data_dir")
    def test_get_database_path_creates_directory(self, mock_get_data_dir, tmp_path):
        """Test that _get_database_path creates data directory if it doesn't exist."""
        mock_data_dir = tmp_path / "test_data"
        mock_get_data_dir.return_value = mock_data_dir

        # Directory shouldn't exist yet
        assert not mock_data_dir.exists()

        db_path = _get_database_path()

        # Directory should be created
        assert mock_data_dir.exists()
        assert db_path == mock_data_dir / "users.db"

    @patch("api.db.user_database.get_data_dir")
    def test_get_database_path_returns_correct_path(self, mock_get_data_dir, tmp_path):
        """Test that _get_database_path returns correct path."""
        mock_data_dir = tmp_path / "test_data"
        mock_data_dir.mkdir(parents=True, exist_ok=True)
        mock_get_data_dir.return_value = mock_data_dir

        db_path = _get_database_path()

        assert db_path == mock_data_dir / "users.db"
        assert isinstance(db_path, Path)


class TestGetConnection:
    """Test database connection functionality."""

    @patch("api.db.user_database._get_database_path")
    def test_get_connection_creates_connection(self, mock_db_path, tmp_path):
        """Test that _get_connection creates a valid connection."""
        db_file = tmp_path / "test_users.db"
        mock_db_path.return_value = db_file

        conn = _get_connection()

        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row
        conn.close()

    @patch("api.db.user_database._get_database_path")
    def test_get_connection_with_row_factory(self, mock_db_path, tmp_path):
        """Test that connection has row factory configured."""
        db_file = tmp_path / "test_users.db"
        mock_db_path.return_value = db_file

        conn = _get_connection()

        # Create a test table and insert data
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'test')")
        conn.commit()

        # Query with row factory
        cursor = conn.execute("SELECT * FROM test WHERE id = 1")
        row = cursor.fetchone()

        # Row should support both index and column access
        assert row[0] == 1
        assert row["id"] == 1
        assert row["name"] == "test"

        conn.close()


class TestGetDbConnection:
    """Test context manager for database connections."""

    @patch("api.db.user_database._get_connection")
    def test_get_db_connection_yields_connection(self, mock_get_conn):
        """Test that get_db_connection yields a valid connection."""
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_get_conn.return_value = mock_conn

        with get_db_connection() as conn:
            assert conn is mock_conn

        # Verify connection was closed
        mock_conn.close.assert_called_once()

    @patch("api.db.user_database._get_connection")
    def test_get_db_connection_closes_on_exception(self, mock_get_conn):
        """Test that connection is closed even when exception occurs."""
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_get_conn.return_value = mock_conn

        with pytest.raises(ValueError):
            with get_db_connection() as conn:
                raise ValueError("Test error")

        # Verify connection was still closed
        mock_conn.close.assert_called_once()


class TestInitDatabase:
    """Test database initialization."""

    @patch("api.db.user_database._create_default_users")
    @patch("api.db.user_database._get_database_path")
    def test_init_database_creates_users_table(self, mock_db_path, mock_create_users, tmp_path):
        """Test that init_database creates the users table."""
        db_file = tmp_path / "test_init.db"
        mock_db_path.return_value = db_file

        init_database()

        # Verify table exists
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        # Check that users table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        result = cursor.fetchone()
        assert result is not None

        # Check table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "id" in columns
        assert "username" in columns
        assert "password_hash" in columns
        assert "full_name" in columns
        assert "role" in columns
        assert "created_at" in columns
        assert "last_login" in columns
        assert "is_active" in columns

        conn.close()

    @patch("api.db.user_database._create_default_users")
    @patch("api.db.user_database._get_database_path")
    def test_init_database_creates_username_index(self, mock_db_path, mock_create_users, tmp_path):
        """Test that init_database creates index on username."""
        db_file = tmp_path / "test_init_index.db"
        mock_db_path.return_value = db_file

        init_database()

        # Verify index exists
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_users_username'"
        )
        result = cursor.fetchone()

        assert result is not None
        assert result[0] == "idx_users_username"

        conn.close()

    @patch("api.db.user_database._create_default_users")
    @patch("api.db.user_database._get_database_path")
    def test_init_database_is_idempotent(self, mock_db_path, mock_create_users, tmp_path):
        """Test that init_database can be called multiple times safely."""
        db_file = tmp_path / "test_idempotent.db"
        mock_db_path.return_value = db_file

        # Call init_database twice
        init_database()
        init_database()

        # Should not raise any errors
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        # Table should exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        result = cursor.fetchone()
        assert result is not None

        conn.close()

    @patch("api.db.user_database._create_default_users")
    @patch("api.db.user_database._get_database_path")
    def test_init_database_calls_create_default_users(self, mock_db_path, mock_create_users, tmp_path):
        """Test that init_database calls _create_default_users."""
        db_file = tmp_path / "test_create_users.db"
        mock_db_path.return_value = db_file

        init_database()

        # Should have called _create_default_users once
        mock_create_users.assert_called_once()

        # Get the connection that was passed to _create_default_users
        call_args = mock_create_users.call_args
        assert call_args is not None

        # Should have been called with a connection
        assert len(call_args[0]) == 1
        conn = call_args[0][0]
        assert isinstance(conn, sqlite3.Connection)


class TestCreateDefaultUsers:
    """Test default user creation."""

    @patch("api.db.user_database._get_database_path")
    def test_create_default_users_with_no_env_vars(self, mock_db_path, tmp_path, monkeypatch):
        """Test that no users are created when env vars are not set."""
        db_file = tmp_path / "test_no_users.db"
        mock_db_path.return_value = db_file

        # Ensure env vars are not set
        monkeypatch.delenv("CLI_ADMIN_PASSWORD", raising=False)
        monkeypatch.delenv("CLI_TESTER_PASSWORD", raising=False)

        # Initialize database
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        # Create table manually
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
        conn.commit()

        # Call _create_default_users
        _create_default_users(conn)

        # Verify no users were created
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        assert count == 0

        conn.close()

    @patch("api.db.user_database._get_database_path")
    def test_create_default_admin_user(self, mock_db_path, tmp_path, monkeypatch):
        """Test creating admin user with env var set."""
        db_file = tmp_path / "test_admin_user.db"
        mock_db_path.return_value = db_file

        # Set admin password
        monkeypatch.setenv("CLI_ADMIN_PASSWORD", "admin_password_123")
        monkeypatch.delenv("CLI_TESTER_PASSWORD", raising=False)

        # Initialize database
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        # Create table manually
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
        conn.commit()

        # Call _create_default_users
        _create_default_users(conn)

        # Verify admin user was created
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        row = cursor.fetchone()

        assert row is not None
        assert row[1] == "admin"  # username
        assert row[3] == "Administrator"  # full_name
        assert row[4] == "admin"  # role
        assert row[7] == 1  # is_active

        # Verify password is hashed correctly
        password_valid = _verify_password_hash("admin_password_123", row[2])
        assert password_valid

        conn.close()

    @patch("api.db.user_database._get_database_path")
    def test_create_default_tester_user(self, mock_db_path, tmp_path, monkeypatch):
        """Test creating tester user with env var set."""
        db_file = tmp_path / "test_tester_user.db"
        mock_db_path.return_value = db_file

        # Set tester password
        monkeypatch.delenv("CLI_ADMIN_PASSWORD", raising=False)
        monkeypatch.setenv("CLI_TESTER_PASSWORD", "tester_password_123")

        # Initialize database
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        # Create table manually
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
        conn.commit()

        # Call _create_default_users
        _create_default_users(conn)

        # Verify tester user was created
        cursor.execute("SELECT * FROM users WHERE username = 'tester'")
        row = cursor.fetchone()

        assert row is not None
        assert row[1] == "tester"  # username
        assert row[3] == "Test User"  # full_name
        assert row[4] == "user"  # role
        assert row[7] == 1  # is_active

        # Verify password is hashed correctly
        password_valid = _verify_password_hash("tester_password_123", row[2])
        assert password_valid

        conn.close()

    @patch("api.db.user_database._get_database_path")
    def test_create_default_users_both(self, mock_db_path, tmp_path, monkeypatch):
        """Test creating both admin and tester users."""
        db_file = tmp_path / "test_both_users.db"
        mock_db_path.return_value = db_file

        # Set both passwords
        monkeypatch.setenv("CLI_ADMIN_PASSWORD", "admin_password_123")
        monkeypatch.setenv("CLI_TESTER_PASSWORD", "tester_password_123")

        # Initialize database
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        # Create table manually
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
        conn.commit()

        # Call _create_default_users
        _create_default_users(conn)

        # Verify both users were created
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        assert count == 2

        conn.close()

    @patch("api.db.user_database._get_database_path")
    def test_create_default_users_idempotent(self, mock_db_path, tmp_path, monkeypatch):
        """Test that calling _create_default_users twice doesn't duplicate users."""
        db_file = tmp_path / "test_idempotent_users.db"
        mock_db_path.return_value = db_file

        # Set admin password
        monkeypatch.setenv("CLI_ADMIN_PASSWORD", "admin_password_123")
        monkeypatch.delenv("CLI_TESTER_PASSWORD", raising=False)

        # Initialize database
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        # Create table manually
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
        conn.commit()

        # Call _create_default_users twice
        _create_default_users(conn)
        _create_default_users(conn)

        # Verify only one admin user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        count = cursor.fetchone()[0]
        assert count == 1

        conn.close()


class TestGetUserByUsername:
    """Test user lookup by username."""

    @patch("api.db.user_database._get_database_path")
    def test_get_existing_user(self, mock_db_path, tmp_path):
        """Test getting an existing user."""
        db_file = tmp_path / "test_get_user.db"
        mock_db_path.return_value = db_file

        # Create database and insert test user
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
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

        user_id = str(uuid.uuid4())
        password_hash = hash_password("test_password")
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, full_name, role, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (user_id, "testuser", password_hash, "Test User", "user", "2024-01-01T00:00:00"))
        conn.commit()
        conn.close()

        # Get user
        user = get_user_by_username("testuser")

        assert user is not None
        assert isinstance(user, DbUser)
        assert user.id == user_id
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.role == "user"
        assert user.created_at == "2024-01-01T00:00:00"
        assert user.is_active is True

    @patch("api.db.user_database._get_database_path")
    def test_get_nonexistent_user(self, mock_db_path, tmp_path):
        """Test getting a user that doesn't exist."""
        db_file = tmp_path / "test_get_nonexistent.db"
        mock_db_path.return_value = db_file

        # Create empty database
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
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
        conn.close()

        # Get user
        user = get_user_by_username("nonexistent")

        assert user is None

    @patch("api.db.user_database._get_database_path")
    def test_get_user_with_all_fields(self, mock_db_path, tmp_path):
        """Test getting user with all fields populated."""
        db_file = tmp_path / "test_get_user_all_fields.db"
        mock_db_path.return_value = db_file

        # Create database and insert test user
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
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

        user_id = str(uuid.uuid4())
        password_hash = hash_password("test_password")
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, full_name, role, created_at, last_login, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            user_id,
            "testuser",
            password_hash,
            "Test User",
            "admin",
            "2024-01-01T00:00:00",
            "2024-01-02T12:00:00"
        ))
        conn.commit()
        conn.close()

        # Get user
        user = get_user_by_username("testuser")

        assert user is not None
        assert user.last_login == "2024-01-02T12:00:00"
        assert user.role == "admin"

    @patch("api.db.user_database._get_database_path")
    def test_get_user_with_none_fields(self, mock_db_path, tmp_path):
        """Test getting user with optional fields as None."""
        db_file = tmp_path / "test_get_user_none_fields.db"
        mock_db_path.return_value = db_file

        # Create database and insert test user
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
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

        user_id = str(uuid.uuid4())
        password_hash = hash_password("test_password")
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, full_name, role, created_at, is_active)
            VALUES (?, ?, ?, NULL, ?, NULL, 1)
        """, (user_id, "testuser", password_hash, "user"))
        conn.commit()
        conn.close()

        # Get user
        user = get_user_by_username("testuser")

        assert user is not None
        assert user.full_name is None
        assert user.created_at is None
        assert user.last_login is None

    @patch("api.db.user_database._get_database_path")
    def test_get_user_with_inactive_status(self, mock_db_path, tmp_path):
        """Test getting an inactive user."""
        db_file = tmp_path / "test_get_inactive_user.db"
        mock_db_path.return_value = db_file

        # Create database and insert inactive user
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
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

        user_id = str(uuid.uuid4())
        password_hash = hash_password("test_password")
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, full_name, role, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (user_id, "inactive_user", password_hash, "Inactive User", "user", "2024-01-01T00:00:00"))
        conn.commit()
        conn.close()

        # Get user
        user = get_user_by_username("inactive_user")

        assert user is not None
        assert user.is_active is False


class TestVerifyPassword:
    """Test password verification functionality."""

    @patch("api.db.user_database.get_user_by_username")
    def test_verify_password_with_correct_credentials(self, mock_get_user):
        """Test password verification with correct username and password."""
        # Mock user
        password_hash = hash_password("correct_password")
        mock_user = DbUser(
            id="user123",
            username="testuser",
            password_hash=password_hash,
            full_name="Test User",
            role="user",
            created_at="2024-01-01T00:00:00",
            last_login=None,
            is_active=True
        )
        mock_get_user.return_value = mock_user

        result = verify_password("testuser", "correct_password")

        assert result is True

    @patch("api.db.user_database.get_user_by_username")
    def test_verify_password_with_incorrect_password(self, mock_get_user):
        """Test password verification with incorrect password."""
        # Mock user
        password_hash = hash_password("correct_password")
        mock_user = DbUser(
            id="user123",
            username="testuser",
            password_hash=password_hash,
            full_name="Test User",
            role="user",
            created_at="2024-01-01T00:00:00",
            last_login=None,
            is_active=True
        )
        mock_get_user.return_value = mock_user

        result = verify_password("testuser", "wrong_password")

        assert result is False

    @patch("api.db.user_database.get_user_by_username")
    def test_verify_password_with_nonexistent_user(self, mock_get_user):
        """Test password verification with nonexistent username."""
        mock_get_user.return_value = None

        result = verify_password("nonexistent", "password")

        assert result is False

    @patch("api.db.user_database.get_user_by_username")
    def test_verify_password_with_inactive_user(self, mock_get_user):
        """Test password verification with inactive user."""
        # Mock inactive user
        password_hash = hash_password("correct_password")
        mock_user = DbUser(
            id="user123",
            username="testuser",
            password_hash=password_hash,
            full_name="Test User",
            role="user",
            created_at="2024-01-01T00:00:00",
            last_login=None,
            is_active=False
        )
        mock_get_user.return_value = mock_user

        result = verify_password("testuser", "correct_password")

        assert result is False

    @patch("api.db.user_database.get_user_by_username")
    def test_verify_password_with_empty_password(self, mock_get_user):
        """Test password verification with empty password."""
        # Mock user with empty password hash
        password_hash = hash_password("")
        mock_user = DbUser(
            id="user123",
            username="testuser",
            password_hash=password_hash,
            full_name="Test User",
            role="user",
            created_at="2024-01-01T00:00:00",
            last_login=None,
            is_active=True
        )
        mock_get_user.return_value = mock_user

        result = verify_password("testuser", "")

        assert result is True

    @patch("api.db.user_database.get_user_by_username")
    def test_verify_password_with_corrupted_hash(self, mock_get_user):
        """Test password verification with corrupted password hash."""
        # Mock user with corrupted hash
        mock_user = DbUser(
            id="user123",
            username="testuser",
            password_hash="corrupted_hash_value",
            full_name="Test User",
            role="user",
            created_at="2024-01-01T00:00:00",
            last_login=None,
            is_active=True
        )
        mock_get_user.return_value = mock_user

        result = verify_password("testuser", "password")

        assert result is False


class TestUpdateLastLogin:
    """Test last login timestamp update."""

    @patch("api.db.user_database._get_database_path")
    def test_update_last_login_success(self, mock_db_path, tmp_path):
        """Test successful update of last login timestamp."""
        db_file = tmp_path / "test_update_login.db"
        mock_db_path.return_value = db_file

        # Create database and insert test user
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
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

        user_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, full_name, role, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (user_id, "testuser", "hash", "Test User", "user", "2024-01-01T00:00:00"))
        conn.commit()
        conn.close()

        # Update last login
        update_last_login(user_id)

        # Verify update
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT last_login FROM users WHERE id = ?", (user_id,))
        last_login = cursor.fetchone()[0]

        assert last_login is not None
        # Should be a valid ISO format timestamp
        datetime.fromisoformat(last_login)

        conn.close()

    @patch("api.db.user_database._get_database_path")
    def test_update_last_login_nonexistent_user(self, mock_db_path, tmp_path):
        """Test updating last login for nonexistent user (should not raise error)."""
        db_file = tmp_path / "test_update_login_nonexistent.db"
        mock_db_path.return_value = db_file

        # Create empty database
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
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
        conn.close()

        # Should not raise error
        update_last_login("nonexistent_user_id")

    @patch("api.db.user_database._get_database_path")
    def test_update_last_login_overwrites_existing(self, mock_db_path, tmp_path):
        """Test that update_last_login overwrites existing timestamp."""
        db_file = tmp_path / "test_update_login_overwrite.db"
        mock_db_path.return_value = db_file

        # Create database and insert test user with existing last_login
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
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

        user_id = str(uuid.uuid4())
        old_login = "2024-01-01T00:00:00"
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, full_name, role, created_at, last_login, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (user_id, "testuser", "hash", "Test User", "user", "2024-01-01T00:00:00", old_login))
        conn.commit()
        conn.close()

        # Update last login
        update_last_login(user_id)

        # Verify update
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT last_login FROM users WHERE id = ?", (user_id,))
        new_login = cursor.fetchone()[0]

        assert new_login != old_login
        assert new_login > old_login

        conn.close()


class TestDbUserDataclass:
    """Test DbUser dataclass."""

    def test_db_user_creation(self):
        """Test creating a DbUser instance."""
        user = DbUser(
            id="user123",
            username="testuser",
            password_hash="hash123",
            full_name="Test User",
            role="user",
            created_at="2024-01-01T00:00:00",
            last_login="2024-01-02T00:00:00",
            is_active=True
        )

        assert user.id == "user123"
        assert user.username == "testuser"
        assert user.password_hash == "hash123"
        assert user.full_name == "Test User"
        assert user.role == "user"
        assert user.created_at == "2024-01-01T00:00:00"
        assert user.last_login == "2024-01-02T00:00:00"
        assert user.is_active is True

    def test_db_user_with_optional_fields(self):
        """Test creating DbUser with optional fields as None."""
        user = DbUser(
            id="user123",
            username="testuser",
            password_hash="hash123",
            full_name=None,
            role="user",
            created_at=None,
            last_login=None,
            is_active=False
        )

        assert user.full_name is None
        assert user.created_at is None
        assert user.last_login is None
        assert user.is_active is False


class TestIntegration:
    """Integration tests for the complete user database flow."""

    @patch("api.db.user_database._get_database_path")
    def test_complete_user_lifecycle(self, mock_db_path, tmp_path, monkeypatch):
        """Test complete user lifecycle: init, create, authenticate, update login."""
        db_file = tmp_path / "test_lifecycle.db"
        mock_db_path.return_value = db_file

        # Set admin password
        monkeypatch.setenv("CLI_ADMIN_PASSWORD", "admin_password_123")
        monkeypatch.delenv("CLI_TESTER_PASSWORD", raising=False)

        # Initialize database
        init_database()

        # Verify admin user exists
        user = get_user_by_username("admin")
        assert user is not None
        assert user.username == "admin"
        assert user.role == "admin"
        assert user.is_active is True

        # Verify password works
        assert verify_password("admin", "admin_password_123") is True
        assert verify_password("admin", "wrong_password") is False

        # Update last login
        update_last_login(user.id)

        # Verify last login was updated
        updated_user = get_user_by_username("admin")
        assert updated_user.last_login is not None

    @patch("api.db.user_database._get_database_path")
    def test_multiple_users_operations(self, mock_db_path, tmp_path):
        """Test operations with multiple users in database."""
        db_file = tmp_path / "test_multiple_users.db"
        mock_db_path.return_value = db_file

        # Initialize database
        init_database()

        # Manually insert multiple users
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        users = [
            ("user1", "pass1", "User One", "user"),
            ("user2", "pass2", "User Two", "admin"),
            ("user3", "pass3", "User Three", "user"),
        ]

        for username, password, full_name, role in users:
            user_id = str(uuid.uuid4())
            password_hash = hash_password(password)
            cursor.execute("""
                INSERT INTO users (id, username, password_hash, full_name, role, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (user_id, username, password_hash, full_name, role, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        # Verify all users can be retrieved
        for username, password, full_name, role in users:
            user = get_user_by_username(username)
            assert user is not None
            assert user.username == username
            assert user.full_name == full_name
            assert user.role == role
            assert verify_password(username, password) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
