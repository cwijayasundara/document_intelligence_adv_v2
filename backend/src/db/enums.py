"""Database enum types for the PE Document Intelligence Platform."""

import enum


class DocumentStatus(str, enum.Enum):
    """Status states for the document processing pipeline."""

    UPLOADED = "uploaded"
    PARSED = "parsed"
    EDITED = "edited"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    SUMMARIZED = "summarized"
    INGESTED = "ingested"


class BulkJobStatus(str, enum.Enum):
    """Status states for bulk processing jobs."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_FAILURE = "partial_failure"


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
