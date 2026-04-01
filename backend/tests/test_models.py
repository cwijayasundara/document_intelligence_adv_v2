"""Tests for E1-S1: Database Types & ORM Models.

Verifies all 10 SQLAlchemy ORM models, enum types, FK relationships,
column types, and UUID primary keys.
"""

from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.db.enums import (
    BulkJobDocumentStatus,
    BulkJobStatus,
    ConfidenceLevel,
    DocumentStatus,
)
from src.db.models import (
    Base,
    BulkJob,
    BulkJobDocument,
    ConversationSummary,
    Document,
    DocumentCategory,
    DocumentSummary,
    ExtractedValue,
    ExtractionField,
    ExtractionSchema,
    MemoryEntry,
)

# --- Enum Tests ---


class TestDocumentStatusEnum:
    """Test DocumentStatus enum has all 7 states."""

    def test_has_seven_states(self) -> None:
        assert len(DocumentStatus) == 7

    def test_uploaded_state(self) -> None:
        assert DocumentStatus.UPLOADED.value == "uploaded"

    def test_parsed_state(self) -> None:
        assert DocumentStatus.PARSED.value == "parsed"

    def test_edited_state(self) -> None:
        assert DocumentStatus.EDITED.value == "edited"

    def test_classified_state(self) -> None:
        assert DocumentStatus.CLASSIFIED.value == "classified"

    def test_extracted_state(self) -> None:
        assert DocumentStatus.EXTRACTED.value == "extracted"

    def test_summarized_state(self) -> None:
        assert DocumentStatus.SUMMARIZED.value == "summarized"

    def test_ingested_state(self) -> None:
        assert DocumentStatus.INGESTED.value == "ingested"

    def test_is_str_enum(self) -> None:
        assert isinstance(DocumentStatus.UPLOADED, str)


class TestBulkJobStatusEnum:
    """Test BulkJobStatus enum."""

    def test_has_five_states(self) -> None:
        assert len(BulkJobStatus) == 5

    def test_pending(self) -> None:
        assert BulkJobStatus.PENDING.value == "pending"

    def test_partial_failure(self) -> None:
        assert BulkJobStatus.PARTIAL_FAILURE.value == "partial_failure"


class TestBulkJobDocumentStatusEnum:
    """Test BulkJobDocumentStatus enum."""

    def test_has_four_states(self) -> None:
        assert len(BulkJobDocumentStatus) == 4

    def test_values(self) -> None:
        values = {s.value for s in BulkJobDocumentStatus}
        assert values == {"pending", "processing", "completed", "failed"}


class TestConfidenceLevelEnum:
    """Test ConfidenceLevel enum."""

    def test_has_three_levels(self) -> None:
        assert len(ConfidenceLevel) == 3

    def test_values(self) -> None:
        values = {c.value for c in ConfidenceLevel}
        assert values == {"high", "medium", "low"}


# --- Model Tests ---


def _get_column_names(model_class: type) -> set[str]:
    """Get column names from a model class via its __table__."""
    return {c.name for c in model_class.__table__.columns}


def _get_pk_columns(model_class: type) -> list[str]:
    """Get primary key column names."""
    return [c.name for c in model_class.__table__.primary_key.columns]


def _get_fk_columns(model_class: type) -> dict[str, str]:
    """Get FK column names mapped to their target."""
    result = {}
    for col in model_class.__table__.columns:
        for fk in col.foreign_keys:
            result[col.name] = str(fk.target_fullname)
    return result


class TestBase:
    """Test DeclarativeBase configuration."""

    def test_base_has_metadata(self) -> None:
        assert Base.metadata is not None

    def test_all_ten_tables_registered(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        expected = {
            "documents",
            "document_categories",
            "extraction_schemas",
            "extraction_fields",
            "extracted_values",
            "document_summaries",
            "bulk_jobs",
            "bulk_job_documents",
            "conversation_summaries",
            "memory_entries",
        }
        assert expected.issubset(table_names)


class TestDocumentCategoryModel:
    """Test DocumentCategory ORM model."""

    def test_tablename(self) -> None:
        assert DocumentCategory.__tablename__ == "document_categories"

    def test_uuid_primary_key(self) -> None:
        pks = _get_pk_columns(DocumentCategory)
        assert pks == ["id"]
        col = DocumentCategory.__table__.c.id
        assert isinstance(col.type, UUID)

    def test_has_timestamps(self) -> None:
        cols = _get_column_names(DocumentCategory)
        assert "created_at" in cols
        assert "updated_at" in cols

    def test_name_is_unique(self) -> None:
        col = DocumentCategory.__table__.c.name
        assert col.unique is True

    def test_columns(self) -> None:
        cols = _get_column_names(DocumentCategory)
        expected = {
            "id",
            "name",
            "description",
            "classification_criteria",
            "created_at",
            "updated_at",
        }
        assert expected == cols


class TestDocumentModel:
    """Test Document ORM model."""

    def test_tablename(self) -> None:
        assert Document.__tablename__ == "documents"

    def test_uuid_primary_key(self) -> None:
        pks = _get_pk_columns(Document)
        assert pks == ["id"]
        col = Document.__table__.c.id
        assert isinstance(col.type, UUID)

    def test_has_timestamps(self) -> None:
        cols = _get_column_names(Document)
        assert "created_at" in cols
        assert "updated_at" in cols

    def test_foreign_key_to_category(self) -> None:
        fks = _get_fk_columns(Document)
        assert "document_category_id" in fks
        assert fks["document_category_id"] == "document_categories.id"

    def test_columns(self) -> None:
        cols = _get_column_names(Document)
        expected = {
            "id",
            "file_name",
            "original_path",
            "parsed_path",
            "file_hash",
            "status",
            "document_category_id",
            "file_type",
            "file_size",
            "user_id",
            "created_at",
            "updated_at",
        }
        assert expected == cols

    def test_status_default(self) -> None:
        col = Document.__table__.c.status
        assert col.server_default is not None


class TestExtractionSchemaModel:
    """Test ExtractionSchema ORM model."""

    def test_tablename(self) -> None:
        assert ExtractionSchema.__tablename__ == "extraction_schemas"

    def test_uuid_primary_key(self) -> None:
        pks = _get_pk_columns(ExtractionSchema)
        assert pks == ["id"]

    def test_foreign_key_to_category(self) -> None:
        fks = _get_fk_columns(ExtractionSchema)
        assert "category_id" in fks
        assert fks["category_id"] == "document_categories.id"

    def test_unique_constraint_category_version(self) -> None:
        constraints = ExtractionSchema.__table__.constraints
        unique_names = {c.name for c in constraints if hasattr(c, "columns") and len(c.columns) > 1}
        assert "uq_extraction_schemas_category_version" in unique_names


class TestExtractionFieldModel:
    """Test ExtractionField ORM model."""

    def test_tablename(self) -> None:
        assert ExtractionField.__tablename__ == "extraction_fields"

    def test_uuid_primary_key(self) -> None:
        pks = _get_pk_columns(ExtractionField)
        assert pks == ["id"]

    def test_foreign_key_to_schema(self) -> None:
        fks = _get_fk_columns(ExtractionField)
        assert "schema_id" in fks
        assert fks["schema_id"] == "extraction_schemas.id"

    def test_unique_constraint_schema_field(self) -> None:
        constraints = ExtractionField.__table__.constraints
        unique_names = {c.name for c in constraints if hasattr(c, "columns") and len(c.columns) > 1}
        assert "uq_extraction_fields_schema_field" in unique_names

    def test_columns(self) -> None:
        cols = _get_column_names(ExtractionField)
        expected = {
            "id",
            "schema_id",
            "field_name",
            "display_name",
            "description",
            "examples",
            "data_type",
            "required",
            "sort_order",
        }
        assert expected == cols


class TestExtractedValueModel:
    """Test ExtractedValue ORM model."""

    def test_tablename(self) -> None:
        assert ExtractedValue.__tablename__ == "extracted_values"

    def test_uuid_primary_key(self) -> None:
        pks = _get_pk_columns(ExtractedValue)
        assert pks == ["id"]

    def test_foreign_key_to_document(self) -> None:
        fks = _get_fk_columns(ExtractedValue)
        assert "document_id" in fks
        assert fks["document_id"] == "documents.id"

    def test_foreign_key_to_field(self) -> None:
        fks = _get_fk_columns(ExtractedValue)
        assert "field_id" in fks
        assert fks["field_id"] == "extraction_fields.id"

    def test_unique_constraint_doc_field(self) -> None:
        constraints = ExtractedValue.__table__.constraints
        unique_names = {c.name for c in constraints if hasattr(c, "columns") and len(c.columns) > 1}
        assert "uq_extracted_values_doc_field" in unique_names

    def test_columns(self) -> None:
        cols = _get_column_names(ExtractedValue)
        expected = {
            "id",
            "document_id",
            "field_id",
            "extracted_value",
            "source_text",
            "confidence",
            "confidence_reasoning",
            "requires_review",
            "reviewed",
            "created_at",
        }
        assert expected == cols


class TestDocumentSummaryModel:
    """Test DocumentSummary ORM model."""

    def test_tablename(self) -> None:
        assert DocumentSummary.__tablename__ == "document_summaries"

    def test_uuid_primary_key(self) -> None:
        pks = _get_pk_columns(DocumentSummary)
        assert pks == ["id"]

    def test_foreign_key_to_document(self) -> None:
        fks = _get_fk_columns(DocumentSummary)
        assert "document_id" in fks
        assert fks["document_id"] == "documents.id"

    def test_document_id_is_unique(self) -> None:
        col = DocumentSummary.__table__.c.document_id
        assert col.unique is True

    def test_key_topics_is_jsonb(self) -> None:
        col = DocumentSummary.__table__.c.key_topics
        assert isinstance(col.type, JSONB)


class TestBulkJobModel:
    """Test BulkJob ORM model."""

    def test_tablename(self) -> None:
        assert BulkJob.__tablename__ == "bulk_jobs"

    def test_uuid_primary_key(self) -> None:
        pks = _get_pk_columns(BulkJob)
        assert pks == ["id"]

    def test_columns(self) -> None:
        cols = _get_column_names(BulkJob)
        expected = {
            "id",
            "status",
            "total_documents",
            "processed_count",
            "failed_count",
            "user_id",
            "created_at",
            "completed_at",
        }
        assert expected == cols


class TestBulkJobDocumentModel:
    """Test BulkJobDocument ORM model."""

    def test_tablename(self) -> None:
        assert BulkJobDocument.__tablename__ == "bulk_job_documents"

    def test_uuid_primary_key(self) -> None:
        pks = _get_pk_columns(BulkJobDocument)
        assert pks == ["id"]

    def test_foreign_key_to_job(self) -> None:
        fks = _get_fk_columns(BulkJobDocument)
        assert "job_id" in fks
        assert fks["job_id"] == "bulk_jobs.id"

    def test_foreign_key_to_document(self) -> None:
        fks = _get_fk_columns(BulkJobDocument)
        assert "document_id" in fks
        assert fks["document_id"] == "documents.id"

    def test_unique_constraint_job_doc(self) -> None:
        constraints = BulkJobDocument.__table__.constraints
        unique_names = {c.name for c in constraints if hasattr(c, "columns") and len(c.columns) > 1}
        assert "uq_bulk_job_documents_job_doc" in unique_names


class TestConversationSummaryModel:
    """Test ConversationSummary ORM model (memory table)."""

    def test_tablename(self) -> None:
        assert ConversationSummary.__tablename__ == "conversation_summaries"

    def test_uuid_primary_key(self) -> None:
        pks = _get_pk_columns(ConversationSummary)
        assert pks == ["id"]

    def test_has_timestamps(self) -> None:
        cols = _get_column_names(ConversationSummary)
        assert "created_at" in cols
        assert "updated_at" in cols

    def test_user_session_composite_unique(self) -> None:
        """Uniqueness is enforced via composite (user_id, session_id) constraint."""
        constraints = ConversationSummary.__table__.constraints
        unique_names = {c.name for c in constraints if hasattr(c, "columns") and len(c.columns) > 1}
        assert "uq_conversation_summaries_user_session" in unique_names

    def test_columns(self) -> None:
        cols = _get_column_names(ConversationSummary)
        expected = {
            "id",
            "session_id",
            "agent_type",
            "summary",
            "key_topics",
            "documents_discussed",
            "queries_count",
            "user_id",
            "created_at",
            "updated_at",
        }
        assert expected == cols


class TestMemoryEntryModel:
    """Test MemoryEntry ORM model (memory table)."""

    def test_tablename(self) -> None:
        assert MemoryEntry.__tablename__ == "memory_entries"

    def test_uuid_primary_key(self) -> None:
        pks = _get_pk_columns(MemoryEntry)
        assert pks == ["id"]

    def test_has_timestamps(self) -> None:
        cols = _get_column_names(MemoryEntry)
        assert "created_at" in cols
        assert "updated_at" in cols

    def test_unique_constraint_ns_key(self) -> None:
        constraints = MemoryEntry.__table__.constraints
        unique_names = {c.name for c in constraints if hasattr(c, "columns") and len(c.columns) > 1}
        assert "uq_memory_entries_ns_key" in unique_names

    def test_data_is_jsonb(self) -> None:
        col = MemoryEntry.__table__.c.data
        assert isinstance(col.type, JSONB)

    def test_columns(self) -> None:
        cols = _get_column_names(MemoryEntry)
        expected = {"id", "namespace", "key", "data", "user_id", "created_at", "updated_at"}
        assert expected == cols


class TestAllModelsHaveUUIDPrimaryKeys:
    """Verify AC-E1S1-04: All models use UUID primary keys with server-side defaults."""

    def test_all_pks_are_uuid(self) -> None:
        all_models = [
            Document,
            DocumentCategory,
            ExtractionSchema,
            ExtractionField,
            ExtractedValue,
            DocumentSummary,
            BulkJob,
            BulkJobDocument,
            ConversationSummary,
            MemoryEntry,
        ]
        for model in all_models:
            pk_cols = [c for c in model.__table__.primary_key.columns]
            assert len(pk_cols) == 1, f"{model.__name__} should have exactly 1 PK"
            pk = pk_cols[0]
            assert isinstance(pk.type, UUID), f"{model.__name__}.id should be UUID"
            assert pk.server_default is not None, f"{model.__name__}.id should have server_default"
