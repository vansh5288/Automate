import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.run_log import RunLog
from app.services import notion_service


def _new_run_id() -> str:
    return f"RUN-{uuid.uuid4().hex[:10].upper()}"


def write_run_log(
    db: Session,
    *,
    request_id: str,
    event: str,
    status: str,
    action: str = "",
    actor: str = "system",
    reason: str = "",
    error: str = "",
    external_action_id: str = "",
) -> RunLog:
    """Writes a Run Log row at the moment an event actually happens.

    Never call this in a batch at startup - each call corresponds to a
    real step of the workflow executing right now.
    """
    log = RunLog(
        run_id=_new_run_id(),
        request_id=request_id,
        event=event,
        status=status,
        action=action,
        actor=actor,
        reason=reason,
        error=error,
        external_action_id=external_action_id,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Mirror into Notion Run Log DB (best-effort - failure here must not
    # crash the workflow, but IS itself logged to the local DB).
    try:
        notion_service.create_run_log_entry(log)
    except Exception as exc:  # noqa: BLE001
        fallback = RunLog(
            run_id=_new_run_id(),
            request_id=request_id,
            event="NOTION_RUNLOG_SYNC",
            status="FAILURE",
            error=str(exc),
            timestamp=datetime.now(timezone.utc),
        )
        db.add(fallback)
        db.commit()

    return log
