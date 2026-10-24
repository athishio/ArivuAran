"""
Privacy-first SQLite storage for Arivaran.
Never stores raw phone numbers, message text, URLs, or audio files.
Uses SHA-256 with a secret SALT to hash sender IDs.
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any

DB_NAME = "arivaran.db"
SALT = os.getenv("SALT", "arivaran_default_salt_2026")


def get_db_path() -> str:
    """Returns database path, honoring ARIVARAN_DB_PATH environment variable if set."""
    return os.getenv("ARIVARAN_DB_PATH", DB_NAME)


def hash_sender(phone: str) -> str:
    """Computes SHA-256 hash of phone number + secret SALT."""
    raw = f"{phone}{SALT}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target = db_path or get_db_path()
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the database tables with parameterized schema."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                sender_hash TEXT NOT NULL,
                msg_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                verdict TEXT NOT NULL,
                fired_rules TEXT NOT NULL,
                feedback TEXT DEFAULT NULL,
                is_test INTEGER DEFAULT 0
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sender ON checks (sender_hash)")

        # Persistent user preferences: stores ONLY salted sender_hash + language
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_prefs (
                sender_hash TEXT PRIMARY KEY,
                language TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_test INTEGER DEFAULT 0
            )
        """)

        # Migration: ensure is_test column exists in both tables
        cursor.execute("PRAGMA table_info(checks)")
        cols = [r[1] for r in cursor.fetchall()]
        if "is_test" not in cols:
            cursor.execute("ALTER TABLE checks ADD COLUMN is_test INTEGER DEFAULT 0")

        cursor.execute("PRAGMA table_info(user_prefs)")
        pcols = [r[1] for r in cursor.fetchall()]
        if "is_test" not in pcols:
            cursor.execute("ALTER TABLE user_prefs ADD COLUMN is_test INTEGER DEFAULT 0")

        conn.commit()


def get_user_language(sender_hash: str, db_path: Optional[str] = None) -> Optional[str]:
    """Retrieves saved language ('ta' or 'en') for the salted sender hash."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM user_prefs WHERE sender_hash = ?", (sender_hash,))
        row = cursor.fetchone()
        return row["language"] if row else None


def set_user_language(sender_hash: str, language: str, is_test: int = 0, db_path: Optional[str] = None) -> None:
    """Saves or updates preferred language for the salted sender hash."""
    ts = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_prefs (sender_hash, language, updated_at, is_test)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(sender_hash) DO UPDATE SET
                language = excluded.language,
                updated_at = excluded.updated_at,
                is_test = excluded.is_test
        """, (sender_hash, language, ts, is_test))
        conn.commit()


def delete_user_language(sender_hash: str, db_path: Optional[str] = None) -> bool:
    """Deletes saved language preference for the salted sender hash on /delete."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_prefs WHERE sender_hash = ?", (sender_hash,))
        conn.commit()
        return cursor.rowcount > 0


def log_check(
    sender_hash: str,
    msg_type: str,
    score: int,
    verdict: str,
    fired_rules: list,
    is_test: int = 0,
    db_path: Optional[str] = None
) -> int:
    """
    Logs check results without storing message content.
    Returns the newly inserted row ID.
    """
    ts = datetime.now(timezone.utc).isoformat()
    rules_json = json.dumps(fired_rules)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO checks (ts, sender_hash, msg_type, score, verdict, fired_rules, is_test)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ts, sender_hash, msg_type, score, verdict, rules_json, is_test))
        conn.commit()
        return cursor.lastrowid


def set_feedback(check_id: int, feedback: str, db_path: Optional[str] = None) -> bool:
    """Updates user feedback ('correct' or 'wrong') for a check."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE checks
            SET feedback = ?
            WHERE id = ?
        """, (feedback, check_id))
        conn.commit()
        return cursor.rowcount > 0


def last_check_id(sender_hash: str, db_path: Optional[str] = None) -> Optional[int]:
    """Finds the ID of the most recent check from this sender hash."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM checks
            WHERE sender_hash = ?
            ORDER BY id DESC
            LIMIT 1
        """, (sender_hash,))
        row = cursor.fetchone()
        return row["id"] if row else None


def log_feedback(sender_hash: str, feedback_text: str, db_path: Optional[str] = None) -> bool:
    """Updates feedback for the sender's most recent check."""
    cid = last_check_id(sender_hash, db_path=db_path)
    if cid:
        return set_feedback(cid, feedback_text, db_path=db_path)
    return False


def get_stats(include_tests: bool = False, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Aggregates counts per verdict for analytics (filters out test rows by default)."""
    where_clause = "" if include_tests else "WHERE is_test = 0"
    fb_where_clause = "WHERE feedback IS NOT NULL" if include_tests else "WHERE feedback IS NOT NULL AND is_test = 0"

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT verdict, COUNT(*) as count
            FROM checks
            {where_clause}
            GROUP BY verdict
        """)
        counts = {row["verdict"]: row["count"] for row in cursor.fetchall()}

        cursor.execute(f"""
            SELECT feedback, COUNT(*) as count
            FROM checks
            {fb_where_clause}
            GROUP BY feedback
        """)
        feedback_counts = {row["feedback"]: row["count"] for row in cursor.fetchall()}

        return {
            "verdict_counts": counts,
            "feedback_counts": feedback_counts
        }