"""Tests for E1-S3: Initial migration creates all 10 tables.

Verifies the migration script defines upgrade/downgrade for all tables.
"""

from pathlib import Path

from src.db.models import Base

MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent / "alembic" / "versions" / "001_initial_schema.py"
)


class TestMigrationTableCoverage:
    """Verify migration covers all 10 tables defined in ORM models."""

    def test_orm_defines_ten_tables(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        assert len(table_names) == 10

    def test_expected_table_names(self) -> None:
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
        assert table_names == expected

    def test_migration_file_exists(self) -> None:
        assert MIGRATION_PATH.exists()

    def test_migration_has_revision_metadata(self) -> None:
        """Verify the migration has correct revision and down_revision."""
        source = MIGRATION_PATH.read_text()
        assert 'revision = "001"' in source
        assert "down_revision = None" in source

    def test_migration_has_upgrade_and_downgrade(self) -> None:
        """Verify the migration defines upgrade() and downgrade() functions."""
        source = MIGRATION_PATH.read_text()
        assert "def upgrade()" in source
        assert "def downgrade()" in source

    def test_migration_upgrade_creates_all_tables(self) -> None:
        """Verify upgrade function source mentions all 10 table names."""
        source = MIGRATION_PATH.read_text()
        # Extract just the upgrade function body (between def upgrade and def downgrade)
        upgrade_start = source.index("def upgrade()")
        downgrade_start = source.index("def downgrade()")
        upgrade_source = source[upgrade_start:downgrade_start]

        expected_tables = [
            "document_categories",
            "documents",
            "extraction_schemas",
            "extraction_fields",
            "extracted_values",
            "document_summaries",
            "bulk_jobs",
            "bulk_job_documents",
            "conversation_summaries",
            "memory_entries",
        ]
        for table in expected_tables:
            assert table in upgrade_source, f"Migration upgrade() missing table: {table}"

    def test_migration_downgrade_drops_all_tables(self) -> None:
        """Verify downgrade function source mentions all 10 table names."""
        source = MIGRATION_PATH.read_text()
        downgrade_start = source.index("def downgrade()")
        downgrade_source = source[downgrade_start:]

        expected_tables = [
            "document_categories",
            "documents",
            "extraction_schemas",
            "extraction_fields",
            "extracted_values",
            "document_summaries",
            "bulk_jobs",
            "bulk_job_documents",
            "conversation_summaries",
            "memory_entries",
        ]
        for table in expected_tables:
            assert table in downgrade_source, f"Migration downgrade() missing table: {table}"

    def test_migration_uses_create_table(self) -> None:
        """Verify upgrade uses op.create_table for all tables."""
        source = MIGRATION_PATH.read_text()
        assert source.count("op.create_table(") == 10

    def test_migration_uses_drop_table(self) -> None:
        """Verify downgrade uses op.drop_table for all tables."""
        source = MIGRATION_PATH.read_text()
        assert source.count("op.drop_table(") == 10
