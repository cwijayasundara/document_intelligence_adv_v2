"""Tests for routing gate functions in the bulk pipeline."""

from __future__ import annotations

from unittest.mock import patch

from src.bulk.gates import route_after_extract, route_after_parse
from src.bulk.state import DocumentState


class TestRouteAfterParse:
    """Tests for route_after_parse gate logic."""

    @patch("src.bulk.gates._get_parse_threshold", return_value=90.0)
    def test_high_confidence_returns_summarize(self, _mock_thresh: object) -> None:
        state: DocumentState = {"document_id": "abc12345", "parse_confidence_pct": 95.0}
        assert route_after_parse(state) == "summarize"

    @patch("src.bulk.gates._get_parse_threshold", return_value=90.0)
    def test_low_confidence_returns_await_review(self, _mock_thresh: object) -> None:
        state: DocumentState = {"document_id": "abc12345", "parse_confidence_pct": 80.0}
        assert route_after_parse(state) == "await_parse_review"

    @patch("src.bulk.gates._get_parse_threshold", return_value=90.0)
    def test_confidence_not_set_defaults_to_100(self, _mock_thresh: object) -> None:
        """When parse_confidence_pct is absent, default 100.0 passes."""
        state: DocumentState = {"document_id": "abc12345"}
        assert route_after_parse(state) == "summarize"

    @patch("src.bulk.gates._get_parse_threshold", return_value=90.0)
    def test_confidence_exactly_90_returns_summarize(self, _mock_thresh: object) -> None:
        """Boundary: exactly at threshold passes."""
        state: DocumentState = {"document_id": "abc12345", "parse_confidence_pct": 90.0}
        assert route_after_parse(state) == "summarize"

    @patch("src.bulk.gates._get_parse_threshold", return_value=90.0)
    def test_confidence_89_9_returns_await_review(self, _mock_thresh: object) -> None:
        """Boundary: just below threshold triggers review."""
        state: DocumentState = {"document_id": "abc12345", "parse_confidence_pct": 89.9}
        assert route_after_parse(state) == "await_parse_review"

    @patch("src.bulk.gates._get_parse_threshold", return_value=90.0)
    def test_confidence_zero_returns_await_review(self, _mock_thresh: object) -> None:
        state: DocumentState = {"document_id": "abc12345", "parse_confidence_pct": 0.0}
        assert route_after_parse(state) == "await_parse_review"

    @patch("src.bulk.gates._get_parse_threshold", return_value=90.0)
    def test_confidence_100_returns_summarize(self, _mock_thresh: object) -> None:
        state: DocumentState = {"document_id": "abc12345", "parse_confidence_pct": 100.0}
        assert route_after_parse(state) == "summarize"

    @patch("src.bulk.gates._get_parse_threshold", return_value=90.0)
    def test_missing_document_id_uses_unknown(self, _mock_thresh: object) -> None:
        """No document_id should not crash, falls back to 'unknown'."""
        state: DocumentState = {"parse_confidence_pct": 95.0}
        assert route_after_parse(state) == "summarize"


class TestRouteAfterExtract:
    """Tests for route_after_extract gate logic."""

    def test_no_extraction_results_returns_ingest(self) -> None:
        state: DocumentState = {"document_id": "abc12345"}
        assert route_after_extract(state) == "ingest"

    def test_all_results_no_review_returns_ingest(self) -> None:
        state: DocumentState = {
            "document_id": "abc12345",
            "extraction_results": [
                {"field": "fund_name", "value": "Horizon IV", "requires_review": False},
                {"field": "fund_size", "value": "$500M", "requires_review": False},
            ],
        }
        assert route_after_extract(state) == "ingest"

    def test_any_result_requires_review_returns_await(self) -> None:
        state: DocumentState = {
            "document_id": "abc12345",
            "extraction_results": [
                {"field": "fund_name", "value": "Horizon IV", "requires_review": False},
                {"field": "mgmt_fee", "value": "unclear", "requires_review": True},
            ],
        }
        assert route_after_extract(state) == "await_extraction_review"

    def test_empty_list_returns_ingest(self) -> None:
        state: DocumentState = {
            "document_id": "abc12345",
            "extraction_results": [],
        }
        assert route_after_extract(state) == "ingest"

    def test_all_results_require_review(self) -> None:
        state: DocumentState = {
            "document_id": "abc12345",
            "extraction_results": [
                {"field": "f1", "value": "v1", "requires_review": True},
                {"field": "f2", "value": "v2", "requires_review": True},
            ],
        }
        assert route_after_extract(state) == "await_extraction_review"

    def test_requires_review_key_absent_defaults_false(self) -> None:
        """When requires_review key is missing, defaults to False."""
        state: DocumentState = {
            "document_id": "abc12345",
            "extraction_results": [
                {"field": "fund_name", "value": "Horizon IV"},
            ],
        }
        assert route_after_extract(state) == "ingest"

    def test_missing_document_id_does_not_crash(self) -> None:
        state: DocumentState = {
            "extraction_results": [
                {"field": "f1", "value": "v1", "requires_review": True},
            ],
        }
        assert route_after_extract(state) == "await_extraction_review"
