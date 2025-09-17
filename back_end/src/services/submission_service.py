from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence

from psycopg2.extensions import connection
from psycopg2.extras import Json, execute_values

from .audit_log import AuditLogService

VALUE_COLUMNS: Sequence[str] = (
    "value_text",
    "value_num",
    "value_bool",
    "value_date",
    "value_ts",
    "value_json",
)


class SubmissionService:
    """Persist submissions and their values including metadata and audit logs."""

    def __init__(
        self,
        conn: connection,
        *,
        audit_log_service: Optional[AuditLogService] = None,
    ) -> None:
        if conn is None:
            raise ValueError("A database connection is required")
        self._conn = conn
        self._audit_log = audit_log_service

    def create_submission(
        self,
        *,
        form_id: int,
        form_version: int,
        aldeia_id: int,
        submitted_by: Optional[int] = None,
        submitted_at: Optional[datetime] = None,
        status: str = "ok",
        raw_payload: Optional[Mapping[str, object]] = None,
        values: Optional[Iterable[Mapping[str, object]]] = None,
        created_by: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ) -> int:
        """Persist a submission and its values.

        Parameters are provided using keyword-only arguments to make call sites
        explicit.  The function returns the generated submission id.
        """

        if form_version is None:
            raise ValueError("form_version must be provided")

        event_time = created_at or datetime.now(timezone.utc)
        submitted_timestamp = submitted_at or event_time

        with self._conn:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO submission (
                        form_id, form_version, aldeia_id, submitted_by, submitted_at,
                        status, raw_payload, created_at, created_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        form_id,
                        form_version,
                        aldeia_id,
                        submitted_by,
                        submitted_timestamp,
                        status,
                        Json(raw_payload) if raw_payload is not None else None,
                        event_time,
                        created_by,
                    ),
                )
                submission_id = cur.fetchone()[0]

                value_rows = list(self._prepare_value_rows(
                    submission_id=submission_id,
                    form_version=form_version,
                    created_at=event_time,
                    created_by=created_by,
                    values=values or [],
                ))

                if value_rows:
                    execute_values(
                        cur,
                        f"""
                        INSERT INTO submission_value (
                            submission_id, form_field_id, field_id,
                            form_version, created_at, created_by,
                            {', '.join(VALUE_COLUMNS)}
                        )
                        VALUES %s
                        """,
                        value_rows,
                    )

                if self._audit_log is not None:
                    payload = {
                        "submission_id": submission_id,
                        "form_id": form_id,
                        "form_version": form_version,
                        "aldeia_id": aldeia_id,
                        "values_count": len(value_rows),
                    }
                    if raw_payload is not None:
                        payload["raw_payload"] = raw_payload
                    self._audit_log.log_event(
                        user_id=created_by or submitted_by,
                        action="submission.created",
                        payload=payload,
                        created_at=event_time,
                    )

        return submission_id

    def _prepare_value_rows(
        self,
        *,
        submission_id: int,
        form_version: int,
        created_at: datetime,
        created_by: Optional[int],
        values: Iterable[Mapping[str, object]],
    ) -> Iterable[tuple]:
        for value in values:
            if "form_field_id" not in value:
                raise KeyError("form_field_id is required in submission values")
            if "field_id" not in value:
                raise KeyError("field_id is required in submission values")

            row: MutableMapping[str, object] = {
                "submission_id": submission_id,
                "form_field_id": value["form_field_id"],
                "field_id": value["field_id"],
                "form_version": form_version,
                "created_at": created_at,
                "created_by": created_by,
            }

            for column in VALUE_COLUMNS:
                column_value = value.get(column)
                if column == "value_json" and column_value is not None:
                    column_value = Json(column_value)
                row[column] = column_value

            yield (
                row["submission_id"],
                row["form_field_id"],
                row["field_id"],
                row["form_version"],
                row["created_at"],
                row["created_by"],
                row["value_text"],
                row["value_num"],
                row["value_bool"],
                row["value_date"],
                row["value_ts"],
                row["value_json"],
            )
