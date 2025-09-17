from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from psycopg2.extensions import connection
from psycopg2.extras import Json


@dataclass
class AuditLogEntry:
    """Simple dataclass representing a persisted audit log entry."""

    id: int
    created_at: datetime


class AuditLogService:
    """Service responsible for persisting audit events in the database.

    The service is intentionally lightweight so it can be easily reused by
    other modules.  It accepts a psycopg2 connection and exposes a single
    ``log_event`` method that inserts the event into the ``audit_log`` table.
    """

    def __init__(self, conn: connection) -> None:
        if conn is None:
            raise ValueError("A database connection is required")
        self._conn = conn

    def log_event(
        self,
        *,
        user_id: Optional[int],
        action: str,
        payload: Optional[Any] = None,
        created_at: Optional[datetime] = None,
    ) -> AuditLogEntry:
        """Persist an audit event and return a lightweight entry description.

        Parameters
        ----------
        user_id:
            Identifier of the user responsible for the action.  ``None`` is
            allowed for system generated events.
        action:
            Short string describing the action that happened.
        payload:
            Optional JSON serialisable object with more details about the
            event.
        created_at:
            Timestamp for the event.  When omitted the current UTC time is
            used.
        """

        if not action:
            raise ValueError("action is required to log an event")

        event_time = created_at or datetime.now(timezone.utc)

        json_payload = Json(payload) if payload is not None else None

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_log (user_id, action, payload, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id, created_at
                """,
                (user_id, action, json_payload, event_time),
            )
            inserted_id, inserted_at = cur.fetchone()

        return AuditLogEntry(id=inserted_id, created_at=inserted_at)