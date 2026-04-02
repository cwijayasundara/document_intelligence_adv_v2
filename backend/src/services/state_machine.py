"""Document state machine enforcing valid status transitions."""

from __future__ import annotations

VALID_TRANSITIONS: dict[str, list[str]] = {
    "uploaded": ["parsed"],
    "parsed": ["edited", "classified", "summarized"],
    "edited": ["classified", "summarized"],
    "classified": ["classified", "extracted", "summarized"],
    "extracted": ["classified", "extracted", "summarized"],
    "summarized": ["classified", "extracted", "summarized", "ingested"],
    "ingested": [],
}


class InvalidTransitionError(Exception):
    """Raised when attempting an invalid state transition."""

    def __init__(self, current_status: str, target_status: str) -> None:
        self.current_status = current_status
        self.target_status = target_status
        valid = VALID_TRANSITIONS.get(current_status, [])
        msg = (
            f"Invalid transition from '{current_status}' to '{target_status}'. "
            f"Valid transitions from '{current_status}': {valid}"
        )
        super().__init__(msg)


def validate_transition(current_status: str, target_status: str) -> None:
    """Validate a state transition. Raises InvalidTransitionError if invalid."""
    valid_targets = VALID_TRANSITIONS.get(current_status, [])
    if target_status not in valid_targets:
        raise InvalidTransitionError(current_status, target_status)


def get_available_actions(current_status: str) -> list[str]:
    """Return valid next statuses for the given current status."""
    return list(VALID_TRANSITIONS.get(current_status, []))
