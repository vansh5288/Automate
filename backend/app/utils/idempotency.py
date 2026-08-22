import hashlib
from datetime import datetime, timezone


def compute_request_hash(employee_email: str, department: str, request_text: str) -> str:
    """Hash used for duplicate-request detection. Same employee + same
    text arriving twice (e.g. a retried webhook) collapses to one hash.
    Not time-based, so a genuine re-submission an hour later still hits it -
    that's intentional for duplicate protection."""
    normalized = f"{employee_email.strip().lower()}|{department.strip().lower()}|{request_text.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate_request_id(sequence_number: int) -> str:
    """sequence_number should come from a DB-backed count (see
    procurement_service) so IDs stay stable across process restarts."""
    year = datetime.now(timezone.utc).year
    return f"REQ-{year}-{sequence_number:04d}"
