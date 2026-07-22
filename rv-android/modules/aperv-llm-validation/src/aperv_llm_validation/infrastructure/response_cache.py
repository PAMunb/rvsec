"""SQLite-backed LLM response cache for reproducibility and resilience."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from aperv_llm_validation.constants import CACHE_DB_NAME


class ResponseCache:
    """SQLite-backed cache for LLM responses. Thread-safe via WAL mode.

    Key: hash(screenshot_basename + prompt_name + rep_seed + temperature + resize_mode).
    Provides reproducibility (re-run reports without LLM) and resilience (SGLang restart).
    """

    def __init__(self, cache_dir: Path | str) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / CACHE_DB_NAME
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_responses (
                    cache_key     TEXT PRIMARY KEY,
                    screenshot    TEXT NOT NULL,
                    prompt_name   TEXT NOT NULL,
                    rep_seed      INTEGER NOT NULL,
                    temperature   REAL NOT NULL,
                    resize_mode   TEXT NOT NULL,
                    request_hash  TEXT,
                    response_json TEXT NOT NULL,
                    tokens_in     INTEGER NOT NULL,
                    tokens_out    INTEGER NOT NULL,
                    latency_ms    INTEGER NOT NULL,
                    created_at    TEXT NOT NULL
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @staticmethod
    def _make_key(
        screenshot: str,
        prompt: str,
        rep_seed: int,
        temperature: float,
        resize_mode: str,
    ) -> str:
        raw = f"{screenshot}|{prompt}|{rep_seed}|{temperature}|{resize_mode}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(
        self,
        screenshot: str,
        prompt: str,
        rep_seed: int,
        temperature: float,
        resize_mode: str,
    ) -> dict | None:
        """Retrieve cached response. Returns None on cache miss."""
        key = self._make_key(screenshot, prompt, rep_seed, temperature, resize_mode)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT response_json, tokens_in, tokens_out, latency_ms "
                "FROM llm_responses WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return {
            "response": json.loads(row[0]),
            "tokens_in": row[1],
            "tokens_out": row[2],
            "latency_ms": row[3],
        }

    def put(
        self,
        screenshot: str,
        prompt: str,
        rep_seed: int,
        temperature: float,
        resize_mode: str,
        response: dict,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        request_hash: str | None = None,
    ) -> None:
        """Store a response in the cache. Overwrites existing entry for same key."""
        key = self._make_key(screenshot, prompt, rep_seed, temperature, resize_mode)
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO llm_responses
                    (cache_key, screenshot, prompt_name, rep_seed, temperature,
                     resize_mode, request_hash, response_json, tokens_in,
                     tokens_out, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    screenshot,
                    prompt,
                    rep_seed,
                    temperature,
                    resize_mode,
                    request_hash,
                    json.dumps(response),
                    tokens_in,
                    tokens_out,
                    latency_ms,
                    now,
                ),
            )

    def stats(self) -> dict:
        """Return cache statistics: total entries and size on disk."""
        with self._connect() as conn:
            (total,) = conn.execute(
                "SELECT COUNT(*) FROM llm_responses"
            ).fetchone()
        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        return {
            "total_entries": total,
            "size_bytes": size_bytes,
            "db_path": str(self.db_path),
        }
