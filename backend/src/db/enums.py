"""Database enum types for the PE Document Intelligence Platform."""

import enum


class DocumentStatus(str, enum.Enum):
    """Status states for the document processing pipeline."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PARSED = "parsed"
    EDITED = "edited"
    AWAITING_PARSE_REVIEW = "awaiting_parse_review"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    AWAITING_EXTRACTION_REVIEW = "awaiting_extraction_review"
    SUMMARIZED = "summarized"
    INGESTED = "ingested"


class BulkJobStatus(str, enum.Enum):
    """Status states for bulk processing jobs."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_FAILURE = "partial_failure"
    AWAITING_REVIEW = "awaiting_review"


class BulkJobDocumentStatus(str, enum.Enum):
    """Status states for individual documents within a bulk job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfidenceLevel(str, enum.Enum):
    """Confidence levels for extracted values."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
