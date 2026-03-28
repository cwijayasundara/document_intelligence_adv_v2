"""Tests for the document state machine."""

import pytest

from src.services.state_machine import (
    InvalidTransitionError,
    VALID_TRANSITIONS,
    get_available_actions,
    validate_transition,
)


class TestValidateTransition:
    """Tests for validate_transition."""

    def test_uploaded_to_parsed_valid(self) -> None:
        validate_transition("uploaded", "parsed")

    def test_parsed_to_edited_valid(self) -> None:
        validate_transition("parsed", "edited")

    def test_parsed_to_classified_valid(self) -> None:
        validate_transition("parsed", "classified")

    def test_edited_to_classified_valid(self) -> None:
        validate_transition("edited", "classified")

    def test_classified_to_extracted_valid(self) -> None:
        validate_transition("classified", "extracted")

    def test_extracted_to_summarized_valid(self) -> None:
        validate_transition("extracted", "summarized")

    def test_summarized_to_ingested_valid(self) -> None:
        validate_transition("summarized", "ingested")

    def test_uploaded_to_classified_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError) as exc_info:
            validate_transition("uploaded", "classified")
        assert "uploaded" in str(exc_info.value)
        assert "classified" in str(exc_info.value)

    def test_uploaded_to_extracted_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition("uploaded", "extracted")

    def test_ingested_to_anything_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition("ingested", "parsed")

    def test_unknown_status_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition("unknown", "parsed")

    def test_backward_transition_invalid(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition("classified", "parsed")

    def test_invalid_transition_error_attributes(self) -> None:
        err = InvalidTransitionError("uploaded", "classified")
        assert err.current_status == "uploaded"
        assert err.target_status == "classified"


class TestGetAvailableActions:
    """Tests for get_available_actions."""

    def test_uploaded_actions(self) -> None:
        assert get_available_actions("uploaded") == ["parsed"]

    def test_parsed_actions(self) -> None:
        actions = get_available_actions("parsed")
        assert "edited" in actions
        assert "classified" in actions

    def test_edited_actions(self) -> None:
        assert get_available_actions("edited") == ["classified"]

    def test_classified_actions(self) -> None:
        assert get_available_actions("classified") == ["extracted"]

    def test_extracted_actions(self) -> None:
        assert get_available_actions("extracted") == ["summarized"]

    def test_summarized_actions(self) -> None:
        assert get_available_actions("summarized") == ["ingested"]

    def test_ingested_no_actions(self) -> None:
        assert get_available_actions("ingested") == []

    def test_unknown_status_no_actions(self) -> None:
        assert get_available_actions("nonexistent") == []


class TestValidTransitionsMap:
    """Tests for the VALID_TRANSITIONS constant."""

    def test_all_statuses_present(self) -> None:
        expected = {
            "uploaded", "parsed", "edited", "classified",
            "extracted", "summarized", "ingested",
        }
        assert set(VALID_TRANSITIONS.keys()) == expected

    def test_no_self_transitions(self) -> None:
        for status, targets in VALID_TRANSITIONS.items():
            assert status not in targets, f"Self-transition found for {status}"
