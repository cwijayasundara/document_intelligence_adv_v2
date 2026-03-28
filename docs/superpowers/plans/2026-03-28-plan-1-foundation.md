# Plan 1: Foundation — Infrastructure, Storage, Parser & Document Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundational infrastructure — Docker services, database, FastAPI scaffold, local file storage, Reducto parser integration, and document upload/parse/edit pipeline with state machine.

**Architecture:** FastAPI backend with async PostgreSQL (SQLAlchemy 2.0 + asyncpg), local filesystem storage with configurable paths via config.yml, Reducto Cloud API for document parsing to markdown, and a PostgreSQL-backed document state machine (uploaded → parsed → edited → classified → extracted → summarized → ingested).

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Alembic, PostgreSQL 16 (Docker), Weaviate (Docker), Reducto API, PyYAML, python-dotenv, pytest, httpx

---

## File Structure

```
backend/
├── src/
│   ├── __init__.py
│   ├── main.py                          # Uvicorn entry point
│   ├── config.py                        # Load config.yml + .env
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py                       # FastAPI app factory
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── documents.py             # Upload, list, get, delete
│   │   │   ├── parse.py                 # Parse via Reducto, get/edit content
│   │   │   └── health.py                # Health check
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── documents.py             # Request/response models for documents
│   │       └── parse.py                 # Request/response models for parsing
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py                # Async engine + session factory
│   │   ├── models.py                    # SQLAlchemy ORM models
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── document_repository.py   # Document CRUD operations
│   ├── parser/
│   │   ├── __init__.py
│   │   └── reducto.py                   # Reducto API client
│   └── storage/
│       ├── __init__.py
│       └── local.py                     # Local filesystem operations
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Shared fixtures
│   ├── test_config.py
│   ├── test_storage.py
│   ├── test_parser.py
│   ├── test_models.py
│   ├── test_document_repository.py
│   ├── test_documents_router.py
│   └── test_parse_router.py
├── alembic/
│   ├── env.py
│   └── versions/
├── alembic.ini
├── config.yml
├── .env.example
├── requirements.txt
└── pyproject.toml
docker-compose.yml
```

---

### Task 1: Docker Compose + Project Scaffold

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/requirements.txt`
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/config.yml`
- Create: `backend/src/__init__.py`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
# docker-compose.yml (project root)
services:
  postgres:
    image: postgres:16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: doc_intel
      POSTGRES_USER: doc_intel
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-doc_intel_dev}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U doc_intel"]
      interval: 5s
      timeout: 5s
      retries: 5

  weaviate:
    image: semitechnologies/weaviate:1.30.0
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
      DEFAULT_VECTORIZER_MODULE: "text2vec-openai"
      ENABLE_MODULES: "text2vec-openai"
      OPENAI_APIKEY: ${OPENAI_API_KEY}
      CLUSTER_HOSTNAME: "node1"
    volumes:
      - weaviate_data:/var/lib/weaviate

volumes:
  pgdata:
  weaviate_data:
```

- [ ] **Step 2: Create backend/requirements.txt**

```
fastapi==0.115.12
uvicorn[standard]==0.34.2
sqlalchemy[asyncio]==2.0.41
asyncpg==0.30.0
alembic==1.15.2
pydantic==2.11.3
pydantic-settings==2.9.1
python-dotenv==1.1.0
python-multipart==0.0.20
pyyaml==6.0.2
httpx==0.28.1
aiofiles==24.1.0
reducto==1.1.2
pytest==8.3.5
pytest-asyncio==0.26.0
pytest-httpx==0.35.0
```

- [ ] **Step 3: Create backend/pyproject.toml**

```toml
[project]
name = "doc-intel-backend"
version = "0.1.0"
requires-python = ">=3.13"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 4: Create backend/.env.example**

```
OPENAI_API_KEY=sk-...
REDUCTO_API_KEY=...
DATABASE_URL=postgresql+asyncpg://doc_intel:doc_intel_dev@localhost:5432/doc_intel
WEAVIATE_URL=http://localhost:8080
OPENAI_MODEL=gpt-5.4-mini
```

- [ ] **Step 5: Create backend/config.yml**

```yaml
storage:
  upload_dir: "./data/upload"
  parsed_dir: "./data/parsed"
  schemas_dir: "./schemas"

chunking:
  max_tokens: 512
  overlap_tokens: 100

bulk:
  concurrent_documents: 3
  max_retries: 3
  retry_delay_seconds: 30

rag:
  default_search_mode: "hybrid"
  default_alpha: 0.5
  top_k: 5

extraction:
  default_schema_dir: "./schemas"
```

- [ ] **Step 6: Create empty __init__.py files**

Create empty `__init__.py` in: `backend/src/`, `backend/src/api/`, `backend/src/api/routers/`, `backend/src/api/schemas/`, `backend/src/db/`, `backend/src/db/repositories/`, `backend/src/parser/`, `backend/src/storage/`, `backend/tests/`

- [ ] **Step 7: Create data directories**

```bash
mkdir -p backend/data/upload backend/data/parsed backend/schemas
```

- [ ] **Step 8: Start Docker services and verify**

```bash
docker compose up -d
docker compose ps
```

Expected: Both `postgres` and `weaviate` containers running and healthy.

- [ ] **Step 9: Install Python dependencies**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 10: Commit**

```bash
git init
echo ".venv/\n__pycache__/\n*.pyc\n.env\nbackend/data/\n*.egg-info/" > .gitignore
git add docker-compose.yml backend/requirements.txt backend/pyproject.toml backend/.env.example backend/config.yml backend/src/__init__.py .gitignore
git commit -m "feat: project scaffold with Docker Compose, config, and dependencies"
```

---

### Task 2: Configuration Module

**Files:**
- Create: `backend/src/config.py`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_config.py
import os
import tempfile
from pathlib import Path

import pytest
import yaml


def test_load_config_from_yaml(tmp_path, monkeypatch):
    """Config loads storage paths from config.yml."""
    config_data = {
        "storage": {
            "upload_dir": "./data/upload",
            "parsed_dir": "./data/parsed",
            "schemas_dir": "./schemas",
        },
        "chunking": {"max_tokens": 512, "overlap_tokens": 100},
        "bulk": {
            "concurrent_documents": 3,
            "max_retries": 3,
            "retry_delay_seconds": 30,
        },
        "rag": {
            "default_search_mode": "hybrid",
            "default_alpha": 0.5,
            "top_k": 5,
        },
        "extraction": {"default_schema_dir": "./schemas"},
    }
    config_file = tmp_path / "config.yml"
    config_file.write_text(yaml.dump(config_data))

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("REDUCTO_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("WEAVIATE_URL", "http://localhost:8080")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4-mini")

    from src.config import load_config

    config = load_config(config_path=str(config_file))

    assert config.storage.upload_dir == "./data/upload"
    assert config.storage.parsed_dir == "./data/parsed"
    assert config.database_url == "postgresql+asyncpg://test:test@localhost/test"
    assert config.reducto_api_key == "test-key"
    assert config.openai_api_key == "sk-test"
    assert config.chunking.max_tokens == 512
    assert config.rag.default_search_mode == "hybrid"


def test_config_env_override(tmp_path, monkeypatch):
    """Environment variables override .env defaults."""
    config_data = {"storage": {"upload_dir": "./custom/upload", "parsed_dir": "./custom/parsed", "schemas_dir": "./schemas"}}
    config_file = tmp_path / "config.yml"
    config_file.write_text(yaml.dump(config_data))

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://prod:prod@db/prod")
    monkeypatch.setenv("REDUCTO_API_KEY", "prod-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-prod")
    monkeypatch.setenv("WEAVIATE_URL", "http://weaviate:8080")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4-mini")

    from src.config import load_config

    config = load_config(config_path=str(config_file))

    assert config.storage.upload_dir == "./custom/upload"
    assert config.database_url == "postgresql+asyncpg://prod:prod@db/prod"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Write the implementation**

```python
# backend/src/config.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class StorageConfig:
    upload_dir: str = "./data/upload"
    parsed_dir: str = "./data/parsed"
    schemas_dir: str = "./schemas"


@dataclass(frozen=True)
class ChunkingConfig:
    max_tokens: int = 512
    overlap_tokens: int = 100


@dataclass(frozen=True)
class BulkConfig:
    concurrent_documents: int = 3
    max_retries: int = 3
    retry_delay_seconds: int = 30


@dataclass(frozen=True)
class RagConfig:
    default_search_mode: str = "hybrid"
    default_alpha: float = 0.5
    top_k: int = 5


@dataclass(frozen=True)
class ExtractionConfig:
    default_schema_dir: str = "./schemas"


@dataclass(frozen=True)
class AppConfig:
    storage: StorageConfig = field(default_factory=StorageConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    bulk: BulkConfig = field(default_factory=BulkConfig)
    rag: RagConfig = field(default_factory=RagConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)

    # From environment
    database_url: str = ""
    reducto_api_key: str = ""
    openai_api_key: str = ""
    weaviate_url: str = "http://localhost:8080"
    openai_model: str = "gpt-5.4-mini"


_config: AppConfig | None = None


def load_config(config_path: str = "config.yml") -> AppConfig:
    global _config
    if _config is not None:
        return _config

    load_dotenv()

    yaml_data: dict = {}
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file) as f:
            yaml_data = yaml.safe_load(f) or {}

    storage_data = yaml_data.get("storage", {})
    chunking_data = yaml_data.get("chunking", {})
    bulk_data = yaml_data.get("bulk", {})
    rag_data = yaml_data.get("rag", {})
    extraction_data = yaml_data.get("extraction", {})

    _config = AppConfig(
        storage=StorageConfig(**storage_data),
        chunking=ChunkingConfig(**chunking_data),
        bulk=BulkConfig(**bulk_data),
        rag=RagConfig(**rag_data),
        extraction=ExtractionConfig(**extraction_data),
        database_url=os.environ["DATABASE_URL"],
        reducto_api_key=os.environ["REDUCTO_API_KEY"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        weaviate_url=os.environ.get("WEAVIATE_URL", "http://localhost:8080"),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
    )
    return _config


def reset_config() -> None:
    """Reset cached config. Used in tests."""
    global _config
    _config = None
```

- [ ] **Step 4: Update test to reset config between tests**

Add to `backend/tests/conftest.py`:

```python
# backend/tests/conftest.py
import pytest


@pytest.fixture(autouse=True)
def reset_config():
    """Reset cached config before each test."""
    from src.config import reset_config
    reset_config()
    yield
    reset_config()
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend
python -m pytest tests/test_config.py -v
```

Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/config.py backend/tests/test_config.py backend/tests/conftest.py
git commit -m "feat: configuration module loading config.yml + .env"
```

---

### Task 3: Database Connection + Models

**Files:**
- Create: `backend/src/db/connection.py`
- Create: `backend/src/db/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py
import uuid
from datetime import datetime, timezone

from src.db.models import (
    Document,
    DocumentCategory,
    DocumentStatus,
    DocumentSummary,
    ExtractionField,
    ExtractionSchema,
    ExtractedValue,
    Confidence,
    BulkJob,
    BulkJobStatus,
    BulkJobDocument,
    BulkJobDocumentStatus,
)


def test_document_status_enum():
    """DocumentStatus enum has all required states."""
    assert DocumentStatus.UPLOADED.value == "uploaded"
    assert DocumentStatus.PARSED.value == "parsed"
    assert DocumentStatus.EDITED.value == "edited"
    assert DocumentStatus.CLASSIFIED.value == "classified"
    assert DocumentStatus.EXTRACTED.value == "extracted"
    assert DocumentStatus.SUMMARIZED.value == "summarized"
    assert DocumentStatus.INGESTED.value == "ingested"


def test_confidence_enum():
    """Confidence enum has high, medium, low."""
    assert Confidence.HIGH.value == "high"
    assert Confidence.MEDIUM.value == "medium"
    assert Confidence.LOW.value == "low"


def test_document_model_fields():
    """Document model has all required columns."""
    doc = Document(
        id=uuid.uuid4(),
        file_name="test.pdf",
        original_path="/upload/test.pdf",
        status=DocumentStatus.UPLOADED,
        file_type="pdf",
        file_size=1024,
    )
    assert doc.file_name == "test.pdf"
    assert doc.status == DocumentStatus.UPLOADED
    assert doc.parsed_path is None
    assert doc.file_hash is None
    assert doc.document_category_id is None


def test_document_category_model_fields():
    """DocumentCategory model has all required columns."""
    cat = DocumentCategory(
        id=uuid.uuid4(),
        name="LPA",
        description="Limited Partnership Agreement",
        classification_criteria="Look for fund terms, GP obligations...",
    )
    assert cat.name == "LPA"
    assert cat.classification_criteria is not None


def test_extraction_field_model_fields():
    """ExtractionField model has all required columns."""
    field = ExtractionField(
        id=uuid.uuid4(),
        schema_id=uuid.uuid4(),
        field_name="fund_name",
        display_name="Fund Name",
        description="The official name of the fund",
        examples="Horizon Equity Partners IV",
        data_type="string",
        required=True,
        sort_order=1,
    )
    assert field.field_name == "fund_name"
    assert field.required is True


def test_extracted_value_model_fields():
    """ExtractedValue model has confidence and review fields."""
    val = ExtractedValue(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        field_id=uuid.uuid4(),
        extracted_value="Horizon Equity Partners IV",
        source_text="...hereby establishes Horizon Equity Partners IV...",
        confidence=Confidence.HIGH,
        confidence_reasoning="Source text explicitly names the fund",
        requires_review=False,
        reviewed=False,
    )
    assert val.confidence == Confidence.HIGH
    assert val.requires_review is False


def test_bulk_job_status_enum():
    """BulkJobStatus enum has all required states."""
    assert BulkJobStatus.PENDING.value == "pending"
    assert BulkJobStatus.PROCESSING.value == "processing"
    assert BulkJobStatus.COMPLETED.value == "completed"
    assert BulkJobStatus.FAILED.value == "failed"
    assert BulkJobStatus.PARTIAL_FAILURE.value == "partial_failure"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.db'`

- [ ] **Step 3: Write the models**

```python
# backend/src/db/models.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    EDITED = "edited"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    SUMMARIZED = "summarized"
    INGESTED = "ingested"


class Confidence(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BulkJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_FAILURE = "partial_failure"


class BulkJobDocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class DocumentCategory(Base):
    __tablename__ = "document_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    documents: Mapped[list[Document]] = relationship(back_populates="category")
    extraction_schemas: Mapped[list[ExtractionSchema]] = relationship(back_populates="category")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    original_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    parsed_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", create_constraint=True),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )
    document_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_categories.id"), nullable=True
    )
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    category: Mapped[DocumentCategory | None] = relationship(back_populates="documents")
    summaries: Mapped[list[DocumentSummary]] = relationship(back_populates="document")
    extracted_values: Mapped[list[ExtractedValue]] = relationship(back_populates="document")


class ExtractionSchema(Base):
    __tablename__ = "extraction_schemas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_categories.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    schema_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    category: Mapped[DocumentCategory] = relationship(back_populates="extraction_schemas")
    fields: Mapped[list[ExtractionField]] = relationship(back_populates="schema")


class ExtractionField(Base):
    __tablename__ = "extraction_fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    schema_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_schemas.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    examples: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False, default="string")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    schema: Mapped[ExtractionSchema] = relationship(back_populates="fields")


class ExtractedValue(Base):
    __tablename__ = "extracted_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_fields.id"), nullable=False
    )
    extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Confidence] = mapped_column(
        Enum(Confidence, name="confidence_level", create_constraint=True),
        nullable=False,
    )
    confidence_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped[Document] = relationship(back_populates="extracted_values")
    field: Mapped[ExtractionField] = relationship()


class DocumentSummary(Base):
    __tablename__ = "document_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped[Document] = relationship(back_populates="summaries")


class BulkJob(Base):
    __tablename__ = "bulk_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    status: Mapped[BulkJobStatus] = mapped_column(
        Enum(BulkJobStatus, name="bulk_job_status", create_constraint=True),
        default=BulkJobStatus.PENDING,
        nullable=False,
    )
    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    documents: Mapped[list[BulkJobDocument]] = relationship(back_populates="job")


class BulkJobDocument(Base):
    __tablename__ = "bulk_job_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bulk_jobs.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    status: Mapped[BulkJobDocumentStatus] = mapped_column(
        Enum(BulkJobDocumentStatus, name="bulk_job_document_status", create_constraint=True),
        default=BulkJobDocumentStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    job: Mapped[BulkJob] = relationship(back_populates="documents")
    document: Mapped[Document] = relationship()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend
python -m pytest tests/test_models.py -v
```

Expected: 6 tests PASS

- [ ] **Step 5: Write the database connection module**

```python
# backend/src/db/connection.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import load_config

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        config = load_config()
        _engine = create_async_engine(
            config.database_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
            echo=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncSession:
    """Dependency for FastAPI — yields a session per request."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def shutdown_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/db/ backend/tests/test_models.py
git commit -m "feat: database models and async connection for document state machine"
```

---

### Task 4: Alembic Migrations

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`

- [ ] **Step 1: Initialize Alembic**

```bash
cd backend
alembic init alembic
```

- [ ] **Step 2: Update alembic.ini**

Replace the `sqlalchemy.url` line in `backend/alembic.ini`:

```ini
sqlalchemy.url = postgresql+asyncpg://doc_intel:doc_intel_dev@localhost:5432/doc_intel
```

- [ ] **Step 3: Update alembic/env.py for async + model discovery**

```python
# backend/alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate initial migration**

```bash
cd backend
alembic revision --autogenerate -m "initial schema"
```

Expected: Migration file created in `alembic/versions/`

- [ ] **Step 5: Run migration against Docker PostgreSQL**

```bash
cd backend
alembic upgrade head
```

Expected: Tables created successfully. Verify:

```bash
docker exec -it $(docker compose ps -q postgres) psql -U doc_intel -d doc_intel -c "\dt"
```

Expected output should show: documents, document_categories, extraction_schemas, extraction_fields, extracted_values, document_summaries, bulk_jobs, bulk_job_documents

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/ backend/alembic.ini
git commit -m "feat: Alembic migrations for initial database schema"
```

---

### Task 5: Local Storage Service

**Files:**
- Create: `backend/src/storage/local.py`
- Create: `backend/tests/test_storage.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_storage.py
import hashlib
from pathlib import Path

import pytest

from src.storage.local import LocalStorage


@pytest.fixture
def storage(tmp_path):
    upload_dir = tmp_path / "upload"
    parsed_dir = tmp_path / "parsed"
    return LocalStorage(upload_dir=str(upload_dir), parsed_dir=str(parsed_dir))


def test_save_upload_creates_file(storage, tmp_path):
    """Saving an upload creates the file in upload_dir."""
    content = b"fake pdf content"
    path = storage.save_upload("test.pdf", content)

    assert Path(path).exists()
    assert Path(path).read_bytes() == content
    assert "upload" in path


def test_save_upload_overwrites_existing(storage):
    """Re-uploading same filename overwrites the file."""
    storage.save_upload("test.pdf", b"v1")
    path = storage.save_upload("test.pdf", b"v2")

    assert Path(path).read_bytes() == b"v2"


def test_compute_file_hash(storage):
    """File hash is SHA-256 hex digest."""
    content = b"test content"
    expected = hashlib.sha256(content).hexdigest()
    assert storage.compute_hash(content) == expected


def test_save_parsed_creates_markdown(storage):
    """Saving parsed content creates .md file in parsed_dir."""
    md_content = "# Parsed Document\n\nSome content here."
    path = storage.save_parsed("test.pdf", md_content)

    assert Path(path).exists()
    assert Path(path).read_text() == md_content
    assert path.endswith(".md")
    assert "parsed" in path


def test_get_parsed_content(storage):
    """Reading parsed content returns the markdown string."""
    storage.save_parsed("test.pdf", "# Hello")
    content = storage.get_parsed_content("test.pdf")
    assert content == "# Hello"


def test_get_parsed_content_not_found(storage):
    """Reading non-existent parsed content returns None."""
    content = storage.get_parsed_content("missing.pdf")
    assert content is None


def test_parsed_exists(storage):
    """Check if parsed file exists."""
    assert storage.parsed_exists("test.pdf") is False
    storage.save_parsed("test.pdf", "content")
    assert storage.parsed_exists("test.pdf") is True


def test_save_parsed_overwrites(storage):
    """Saving parsed content overwrites existing file."""
    storage.save_parsed("test.pdf", "v1")
    storage.save_parsed("test.pdf", "v2")
    assert storage.get_parsed_content("test.pdf") == "v2"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_storage.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.storage'`

- [ ] **Step 3: Write the implementation**

```python
# backend/src/storage/local.py
from __future__ import annotations

import hashlib
from pathlib import Path


class LocalStorage:
    def __init__(self, upload_dir: str, parsed_dir: str) -> None:
        self._upload_dir = Path(upload_dir)
        self._parsed_dir = Path(parsed_dir)
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._parsed_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, file_name: str, content: bytes) -> str:
        """Save uploaded file to upload directory. Overwrites if exists."""
        path = self._upload_dir / file_name
        path.write_bytes(content)
        return str(path)

    def compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    def save_parsed(self, original_file_name: str, markdown_content: str) -> str:
        """Save parsed markdown to parsed directory."""
        md_name = Path(original_file_name).stem + ".md"
        path = self._parsed_dir / md_name
        path.write_text(markdown_content, encoding="utf-8")
        return str(path)

    def get_parsed_content(self, original_file_name: str) -> str | None:
        """Read parsed markdown content. Returns None if not found."""
        md_name = Path(original_file_name).stem + ".md"
        path = self._parsed_dir / md_name
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def parsed_exists(self, original_file_name: str) -> bool:
        """Check if parsed file exists."""
        md_name = Path(original_file_name).stem + ".md"
        return (self._parsed_dir / md_name).exists()

    def get_upload_path(self, file_name: str) -> str:
        """Get full path for an uploaded file."""
        return str(self._upload_dir / file_name)

    def get_parsed_path(self, original_file_name: str) -> str:
        """Get full path for a parsed file."""
        md_name = Path(original_file_name).stem + ".md"
        return str(self._parsed_dir / md_name)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_storage.py -v
```

Expected: 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/storage/ backend/tests/test_storage.py
git commit -m "feat: local filesystem storage service with upload, parsed, and hash"
```

---

### Task 6: Reducto Parser Client

**Files:**
- Create: `backend/src/parser/reducto.py`
- Create: `backend/tests/test_parser.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_parser.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.parser.reducto import ReductoParser


@pytest.fixture
def parser():
    return ReductoParser(api_key="test-key")


@pytest.mark.asyncio
async def test_parse_returns_markdown(parser):
    """Parser returns markdown string from Reducto API."""
    mock_result = MagicMock()
    mock_chunk = MagicMock()
    mock_chunk.content = "# Document Title\n\nSome parsed content."
    mock_result.result.chunks = [mock_chunk]

    with patch.object(parser, "_client") as mock_client:
        mock_client.parse = AsyncMock(return_value=mock_result)
        result = await parser.parse_file("/path/to/test.pdf")

    assert result == "# Document Title\n\nSome parsed content."


@pytest.mark.asyncio
async def test_parse_concatenates_chunks(parser):
    """Parser concatenates multiple chunks with double newlines."""
    mock_result = MagicMock()
    chunk1 = MagicMock()
    chunk1.content = "# Section 1"
    chunk2 = MagicMock()
    chunk2.content = "# Section 2"
    mock_result.result.chunks = [chunk1, chunk2]

    with patch.object(parser, "_client") as mock_client:
        mock_client.parse = AsyncMock(return_value=mock_result)
        result = await parser.parse_file("/path/to/test.pdf")

    assert result == "# Section 1\n\n# Section 2"


@pytest.mark.asyncio
async def test_parse_raises_on_api_error(parser):
    """Parser raises RuntimeError on API failure."""
    with patch.object(parser, "_client") as mock_client:
        mock_client.parse = AsyncMock(side_effect=Exception("API rate limit"))

        with pytest.raises(RuntimeError, match="Reducto parsing failed"):
            await parser.parse_file("/path/to/test.pdf")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_parser.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.parser'`

- [ ] **Step 3: Write the implementation**

```python
# backend/src/parser/reducto.py
from __future__ import annotations

from reducto import Reducto


class ReductoParser:
    def __init__(self, api_key: str) -> None:
        self._client = Reducto(api_key=api_key)

    async def parse_file(self, file_path: str) -> str:
        """Parse a document file and return markdown content.

        Args:
            file_path: Path to the file to parse.

        Returns:
            Parsed content as a markdown string.

        Raises:
            RuntimeError: If the Reducto API call fails.
        """
        try:
            result = await self._client.parse(file_path)
            chunks = result.result.chunks
            markdown = "\n\n".join(chunk.content for chunk in chunks)
            return markdown
        except Exception as e:
            raise RuntimeError(f"Reducto parsing failed for {file_path}: {e}") from e
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_parser.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/parser/ backend/tests/test_parser.py
git commit -m "feat: Reducto parser client for document-to-markdown conversion"
```

---

### Task 7: Document Repository

**Files:**
- Create: `backend/src/db/repositories/document_repository.py`
- Create: `backend/tests/test_document_repository.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_document_repository.py
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.models import Document, DocumentStatus
from src.db.repositories.document_repository import DocumentRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session):
    return DocumentRepository(mock_session)


@pytest.mark.asyncio
async def test_create_document(repo, mock_session):
    """Create stores a document with UPLOADED status."""
    doc = await repo.create(
        file_name="test.pdf",
        original_path="/upload/test.pdf",
        file_type="pdf",
        file_size=1024,
        file_hash="abc123",
    )

    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    added_doc = mock_session.add.call_args[0][0]
    assert added_doc.file_name == "test.pdf"
    assert added_doc.status == DocumentStatus.UPLOADED


@pytest.mark.asyncio
async def test_update_status(repo, mock_session):
    """Update status changes document state."""
    doc_id = uuid.uuid4()
    mock_doc = Document(
        id=doc_id,
        file_name="test.pdf",
        original_path="/upload/test.pdf",
        file_type="pdf",
        file_size=1024,
        status=DocumentStatus.UPLOADED,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc
    mock_session.execute.return_value = mock_result

    updated = await repo.update_status(doc_id, DocumentStatus.PARSED)

    assert updated.status == DocumentStatus.PARSED
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id(repo, mock_session):
    """Get by ID returns the document."""
    doc_id = uuid.uuid4()
    mock_doc = Document(
        id=doc_id,
        file_name="test.pdf",
        original_path="/upload/test.pdf",
        file_type="pdf",
        file_size=1024,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc
    mock_session.execute.return_value = mock_result

    result = await repo.get_by_id(doc_id)

    assert result is not None
    assert result.id == doc_id


@pytest.mark.asyncio
async def test_get_by_id_not_found(repo, mock_session):
    """Get by ID returns None when document not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repo.get_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_find_by_filename(repo, mock_session):
    """Find by filename returns matching document."""
    mock_doc = Document(
        id=uuid.uuid4(),
        file_name="test.pdf",
        original_path="/upload/test.pdf",
        file_type="pdf",
        file_size=1024,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc
    mock_session.execute.return_value = mock_result

    result = await repo.find_by_filename("test.pdf")

    assert result is not None
    assert result.file_name == "test.pdf"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_document_repository.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.db.repositories.document_repository'`

- [ ] **Step 3: Write the implementation**

```python
# backend/src/db/repositories/document_repository.py
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document, DocumentStatus


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        file_name: str,
        original_path: str,
        file_type: str,
        file_size: int,
        file_hash: str | None = None,
    ) -> Document:
        doc = Document(
            file_name=file_name,
            original_path=original_path,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash,
            status=DocumentStatus.UPLOADED,
        )
        self._session.add(doc)
        await self._session.commit()
        await self._session.refresh(doc)
        return doc

    async def get_by_id(self, doc_id: uuid.UUID) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def find_by_filename(self, file_name: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.file_name == file_name)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[Document]:
        result = await self._session.execute(
            select(Document).order_by(Document.created_at.desc())
        )
        return result.scalars().all()

    async def update_status(
        self, doc_id: uuid.UUID, status: DocumentStatus
    ) -> Document | None:
        doc = await self.get_by_id(doc_id)
        if doc is None:
            return None
        doc.status = status
        await self._session.commit()
        await self._session.refresh(doc)
        return doc

    async def update_parsed(
        self,
        doc_id: uuid.UUID,
        parsed_path: str,
        file_hash: str,
    ) -> Document | None:
        doc = await self.get_by_id(doc_id)
        if doc is None:
            return None
        doc.parsed_path = parsed_path
        doc.file_hash = file_hash
        doc.status = DocumentStatus.PARSED
        await self._session.commit()
        await self._session.refresh(doc)
        return doc

    async def delete(self, doc_id: uuid.UUID) -> bool:
        doc = await self.get_by_id(doc_id)
        if doc is None:
            return False
        await self._session.delete(doc)
        await self._session.commit()
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_document_repository.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/db/repositories/ backend/tests/test_document_repository.py
git commit -m "feat: document repository with CRUD and status transitions"
```

---

### Task 8: FastAPI App Factory + Health Check

**Files:**
- Create: `backend/src/api/app.py`
- Create: `backend/src/api/routers/health.py`
- Create: `backend/src/main.py`
- Create: `backend/tests/test_health_router.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_health_router.py
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app


@pytest.mark.asyncio
async def test_health_check():
    """Health endpoint returns 200 with status ok."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_health_router.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.api'`

- [ ] **Step 3: Write the health router**

```python
# backend/src/api/routers/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 4: Write the app factory**

```python
# backend/src/api/app.py
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.connection import shutdown_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await shutdown_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Document Intelligence Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from src.api.routers.health import router as health_router

    app.include_router(health_router)

    return app
```

- [ ] **Step 5: Write the entry point**

```python
# backend/src/main.py
import uvicorn

from src.api.app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd backend
python -m pytest tests/test_health_router.py -v
```

Expected: 1 test PASS

- [ ] **Step 7: Verify server starts**

```bash
cd backend
python -m src.main &
curl http://localhost:8000/health
kill %1
```

Expected: `{"status":"ok","version":"0.1.0"}`

- [ ] **Step 8: Commit**

```bash
git add backend/src/api/ backend/src/main.py backend/tests/test_health_router.py
git commit -m "feat: FastAPI app factory with health check and CORS"
```

---

### Task 9: Pydantic API Schemas

**Files:**
- Create: `backend/src/api/schemas/documents.py`
- Create: `backend/src/api/schemas/parse.py`

- [ ] **Step 1: Create document schemas**

```python
# backend/src/api/schemas/documents.py
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from src.db.models import DocumentStatus


class DocumentResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    original_path: str
    parsed_path: str | None
    file_hash: str | None
    status: DocumentStatus
    document_category_id: uuid.UUID | None
    file_type: str
    file_size: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str
    is_replacement: bool
```

- [ ] **Step 2: Create parse schemas**

```python
# backend/src/api/schemas/parse.py
from __future__ import annotations

import uuid

from pydantic import BaseModel


class ParseRequest(BaseModel):
    force: bool = False


class ParseResponse(BaseModel):
    document_id: uuid.UUID
    parsed_path: str
    file_hash: str
    skipped: bool
    message: str


class ParsedContentResponse(BaseModel):
    document_id: uuid.UUID
    file_name: str
    content: str


class EditContentRequest(BaseModel):
    content: str


class EditContentResponse(BaseModel):
    document_id: uuid.UUID
    file_name: str
    parsed_path: str
    message: str
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/api/schemas/
git commit -m "feat: Pydantic request/response schemas for documents and parse APIs"
```

---

### Task 10: Document Upload Router

**Files:**
- Create: `backend/src/api/routers/documents.py`
- Create: `backend/tests/test_documents_router.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_documents_router.py
import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.db.models import Document, DocumentStatus


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.save_upload.return_value = "/data/upload/test.pdf"
    storage.compute_hash.return_value = "abc123hash"
    return storage


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


def _make_doc(
    file_name="test.pdf",
    status=DocumentStatus.UPLOADED,
    doc_id=None,
) -> Document:
    return Document(
        id=doc_id or uuid.uuid4(),
        file_name=file_name,
        original_path=f"/data/upload/{file_name}",
        file_type="pdf",
        file_size=1024,
        status=status,
        file_hash="abc123hash",
    )


@pytest.mark.asyncio
async def test_upload_single_file(app, mock_storage, mock_session):
    """Upload endpoint accepts a file and returns document metadata."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with (
        patch("src.api.routers.documents.get_storage", return_value=mock_storage),
        patch("src.api.routers.documents.get_session") as mock_get_session,
    ):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

        # Override the dependency
        from src.api.routers.documents import get_session as doc_get_session

        app.dependency_overrides[doc_get_session] = lambda: mock_session

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] is not None


@pytest.mark.asyncio
async def test_list_documents(app, mock_session):
    """List endpoint returns all documents."""
    mock_docs = [_make_doc("a.pdf"), _make_doc("b.pdf")]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_docs
    mock_session.execute.return_value = mock_result

    from src.api.routers.documents import get_session as doc_get_session

    app.dependency_overrides[doc_get_session] = lambda: mock_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/documents")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_documents_router.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.api.routers.documents'`

- [ ] **Step 3: Write the documents router**

```python
# backend/src/api/routers/documents.py
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.documents import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from src.config import load_config
from src.db.connection import get_session
from src.db.repositories.document_repository import DocumentRepository
from src.storage.local import LocalStorage

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

_storage: LocalStorage | None = None


def get_storage() -> LocalStorage:
    global _storage
    if _storage is None:
        config = load_config()
        _storage = LocalStorage(
            upload_dir=config.storage.upload_dir,
            parsed_dir=config.storage.parsed_dir,
        )
    return _storage


def _get_file_type(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower().lstrip(".")
    return suffix if suffix else "unknown"


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    storage = get_storage()
    repo = DocumentRepository(session)

    file_hash = storage.compute_hash(content)
    original_path = storage.save_upload(file.filename, content)

    existing = await repo.find_by_filename(file.filename)
    is_replacement = existing is not None

    if existing:
        existing.original_path = original_path
        existing.file_hash = file_hash
        existing.file_size = len(content)
        existing.file_type = _get_file_type(file.filename)
        await session.commit()
        await session.refresh(existing)
        doc = existing
    else:
        doc = await repo.create(
            file_name=file.filename,
            original_path=original_path,
            file_type=_get_file_type(file.filename),
            file_size=len(content),
            file_hash=file_hash,
        )

    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(doc),
        message="File replaced" if is_replacement else "File uploaded",
        is_replacement=is_replacement,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(session: AsyncSession = Depends(get_session)):
    repo = DocumentRepository(session)
    docs = await repo.list_all()
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = DocumentRepository(session)
    deleted = await repo.delete(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted"}
```

- [ ] **Step 4: Register the router in app.py**

Update `backend/src/api/app.py` — add after the health router import:

```python
    from src.api.routers.documents import router as documents_router

    app.include_router(health_router)
    app.include_router(documents_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_documents_router.py -v
```

Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/routers/documents.py backend/src/api/app.py backend/tests/test_documents_router.py
git commit -m "feat: document upload, list, get, delete API endpoints"
```

---

### Task 11: Parse Router (Reducto + Edit)

**Files:**
- Create: `backend/src/api/routers/parse.py`
- Create: `backend/tests/test_parse_router.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_parse_router.py
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.db.models import Document, DocumentStatus


@pytest.fixture
def app():
    return create_app()


def _make_doc(status=DocumentStatus.UPLOADED, file_hash="old_hash") -> Document:
    return Document(
        id=uuid.uuid4(),
        file_name="test.pdf",
        original_path="/data/upload/test.pdf",
        file_type="pdf",
        file_size=1024,
        status=status,
        file_hash=file_hash,
    )


@pytest.mark.asyncio
async def test_parse_document_calls_reducto(app):
    """Parse endpoint calls Reducto and saves markdown."""
    doc = _make_doc()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = doc
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    mock_storage = MagicMock()
    mock_storage.parsed_exists.return_value = False
    mock_storage.save_parsed.return_value = "/data/parsed/test.md"
    mock_storage.compute_hash.return_value = "new_hash"
    mock_storage.get_upload_path.return_value = "/data/upload/test.pdf"

    mock_parser = MagicMock()
    mock_parser.parse_file = AsyncMock(return_value="# Parsed Content")

    from src.api.routers.parse import get_session as parse_get_session

    app.dependency_overrides[parse_get_session] = lambda: mock_session

    with (
        patch("src.api.routers.parse.get_storage", return_value=mock_storage),
        patch("src.api.routers.parse.get_parser", return_value=mock_parser),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/v1/parse/{doc.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["skipped"] is False
    assert data["parsed_path"] == "/data/parsed/test.md"


@pytest.mark.asyncio
async def test_parse_skips_if_already_parsed_same_hash(app):
    """Parse skips re-parsing if file hash hasn't changed."""
    doc = _make_doc(status=DocumentStatus.PARSED, file_hash="same_hash")
    doc.parsed_path = "/data/parsed/test.md"

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = doc
    mock_session.execute.return_value = mock_result

    mock_storage = MagicMock()
    mock_storage.parsed_exists.return_value = True
    mock_storage.compute_hash.return_value = "same_hash"

    from src.api.routers.parse import get_session as parse_get_session

    app.dependency_overrides[parse_get_session] = lambda: mock_session

    with patch("src.api.routers.parse.get_storage", return_value=mock_storage):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/v1/parse/{doc.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["skipped"] is True


@pytest.mark.asyncio
async def test_get_parsed_content(app):
    """Get parsed content returns the markdown."""
    doc = _make_doc(status=DocumentStatus.PARSED)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = doc
    mock_session.execute.return_value = mock_result

    mock_storage = MagicMock()
    mock_storage.get_parsed_content.return_value = "# Hello World"

    from src.api.routers.parse import get_session as parse_get_session

    app.dependency_overrides[parse_get_session] = lambda: mock_session

    with patch("src.api.routers.parse.get_storage", return_value=mock_storage):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/parse/{doc.id}/content")

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "# Hello World"


@pytest.mark.asyncio
async def test_edit_parsed_content(app):
    """Edit endpoint saves new content and updates status to EDITED."""
    doc = _make_doc(status=DocumentStatus.PARSED)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = doc
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    mock_storage = MagicMock()
    mock_storage.save_parsed.return_value = "/data/parsed/test.md"

    from src.api.routers.parse import get_session as parse_get_session

    app.dependency_overrides[parse_get_session] = lambda: mock_session

    with patch("src.api.routers.parse.get_storage", return_value=mock_storage):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/parse/{doc.id}/content",
                json={"content": "# Edited content"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Content updated"
    mock_storage.save_parsed.assert_called_once_with("test.pdf", "# Edited content")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_parse_router.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.api.routers.parse'`

- [ ] **Step 3: Write the parse router**

```python
# backend/src/api/routers/parse.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.parse import (
    EditContentRequest,
    EditContentResponse,
    ParseResponse,
    ParsedContentResponse,
)
from src.config import load_config
from src.db.connection import get_session
from src.db.models import DocumentStatus
from src.db.repositories.document_repository import DocumentRepository
from src.parser.reducto import ReductoParser
from src.storage.local import LocalStorage

router = APIRouter(prefix="/api/v1/parse", tags=["parse"])

_storage: LocalStorage | None = None
_parser: ReductoParser | None = None


def get_storage() -> LocalStorage:
    global _storage
    if _storage is None:
        config = load_config()
        _storage = LocalStorage(
            upload_dir=config.storage.upload_dir,
            parsed_dir=config.storage.parsed_dir,
        )
    return _storage


def get_parser() -> ReductoParser:
    global _parser
    if _parser is None:
        config = load_config()
        _parser = ReductoParser(api_key=config.reducto_api_key)
    return _parser


@router.post("/{document_id}", response_model=ParseResponse)
async def parse_document(
    document_id: uuid.UUID,
    force: bool = False,
    session: AsyncSession = Depends(get_session),
):
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    storage = get_storage()

    # Check if already parsed with same hash — skip unless forced
    if (
        not force
        and doc.parsed_path
        and storage.parsed_exists(doc.file_name)
        and doc.file_hash == storage.compute_hash(
            open(doc.original_path, "rb").read() if doc.original_path else b""
        )
    ):
        return ParseResponse(
            document_id=doc.id,
            parsed_path=doc.parsed_path,
            file_hash=doc.file_hash or "",
            skipped=True,
            message="Already parsed with same file hash",
        )

    # Parse via Reducto
    parser = get_parser()
    upload_path = storage.get_upload_path(doc.file_name)
    markdown = await parser.parse_file(upload_path)

    # Save parsed markdown
    parsed_path = storage.save_parsed(doc.file_name, markdown)

    # Read file to compute hash
    with open(doc.original_path, "rb") as f:
        file_hash = storage.compute_hash(f.read())

    # Update document record
    await repo.update_parsed(doc.id, parsed_path, file_hash)

    return ParseResponse(
        document_id=doc.id,
        parsed_path=parsed_path,
        file_hash=file_hash,
        skipped=False,
        message="Document parsed successfully",
    )


@router.get("/{document_id}/content", response_model=ParsedContentResponse)
async def get_parsed_content(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    storage = get_storage()
    content = storage.get_parsed_content(doc.file_name)
    if content is None:
        raise HTTPException(status_code=404, detail="Parsed content not found")

    return ParsedContentResponse(
        document_id=doc.id,
        file_name=doc.file_name,
        content=content,
    )


@router.put("/{document_id}/content", response_model=EditContentResponse)
async def edit_parsed_content(
    document_id: uuid.UUID,
    body: EditContentRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    storage = get_storage()
    parsed_path = storage.save_parsed(doc.file_name, body.content)

    doc.parsed_path = parsed_path
    doc.status = DocumentStatus.EDITED
    await session.commit()
    await session.refresh(doc)

    return EditContentResponse(
        document_id=doc.id,
        file_name=doc.file_name,
        parsed_path=parsed_path,
        message="Content updated",
    )
```

- [ ] **Step 4: Register the parse router in app.py**

Update `backend/src/api/app.py` — add after the documents router:

```python
    from src.api.routers.parse import router as parse_router

    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(parse_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_parse_router.py -v
```

Expected: 4 tests PASS

- [ ] **Step 6: Run all tests to verify nothing is broken**

```bash
cd backend
python -m pytest -v
```

Expected: All tests PASS (config: 2, storage: 8, models: 6, repository: 5, health: 1, documents router: 2, parse router: 4 = 28 total)

- [ ] **Step 7: Commit**

```bash
git add backend/src/api/routers/parse.py backend/src/api/app.py backend/tests/test_parse_router.py
git commit -m "feat: parse router with Reducto integration, content editing, and skip-if-unchanged"
```

---

### Task 12: End-to-End Smoke Test

**Files:**
- Create: `backend/tests/test_e2e_smoke.py`

- [ ] **Step 1: Write an integration test that exercises the full flow**

```python
# backend/tests/test_e2e_smoke.py
"""
End-to-end smoke test for upload → parse → edit flow.
Requires Docker PostgreSQL running. Skip with: pytest -m "not e2e"
"""
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.app import create_app


pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_upload_parse_edit_flow():
    """Full flow: upload a file → parse it → read content → edit content."""
    app = create_app()

    # Mock storage and parser to avoid real filesystem/API calls
    mock_storage = MagicMock()
    mock_storage.save_upload.return_value = "/data/upload/test.pdf"
    mock_storage.compute_hash.return_value = "hash123"
    mock_storage.parsed_exists.return_value = False
    mock_storage.save_parsed.return_value = "/data/parsed/test.md"
    mock_storage.get_parsed_content.return_value = "# Parsed by Reducto"
    mock_storage.get_upload_path.return_value = "/data/upload/test.pdf"

    mock_parser = MagicMock()
    mock_parser.parse_file = AsyncMock(return_value="# Parsed by Reducto")

    with (
        patch("src.api.routers.documents.get_storage", return_value=mock_storage),
        patch("src.api.routers.parse.get_storage", return_value=mock_storage),
        patch("src.api.routers.parse.get_parser", return_value=mock_parser),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: Upload
            resp = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", b"fake content", "application/pdf")},
            )
            assert resp.status_code == 200
            doc_id = resp.json()["document"]["id"]
            assert resp.json()["document"]["status"] == "uploaded"

            # Step 2: List — should have 1 document
            resp = await client.get("/api/v1/documents")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 1

            # Step 3: Get document
            resp = await client.get(f"/api/v1/documents/{doc_id}")
            assert resp.status_code == 200
            assert resp.json()["file_name"] == "test.pdf"
```

- [ ] **Step 2: Update pytest config to support e2e marker**

Add to `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "e2e: end-to-end integration tests",
]
```

- [ ] **Step 3: Run the smoke test**

```bash
cd backend
python -m pytest tests/test_e2e_smoke.py -v
```

Expected: 1 test PASS

- [ ] **Step 4: Run full test suite**

```bash
cd backend
python -m pytest -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_e2e_smoke.py backend/pyproject.toml
git commit -m "feat: end-to-end smoke test for upload-parse-edit flow"
```

---

## Plan Self-Review

**Spec coverage check:**
- Docker Compose (PostgreSQL + Weaviate) ✅ Task 1
- Config from config.yml + .env ✅ Task 2
- All DB tables from spec ✅ Task 3
- Alembic migrations ✅ Task 4
- Local storage with upload/parsed dirs ✅ Task 5
- Reducto parser ✅ Task 6
- Document CRUD repository ✅ Task 7
- FastAPI app factory ✅ Task 8
- API schemas ✅ Task 9
- Upload endpoint with overwrite ✅ Task 10
- Parse with skip-if-unchanged ✅ Task 11
- Edit parsed content ✅ Task 11
- State machine transitions ✅ Tasks 7, 10, 11
- E2E smoke test ✅ Task 12

**Deferred to Plan 2:** Classification, extraction, judge, summarization, RAG ingestion/retrieval, bulk pipeline
**Deferred to Plan 3:** All frontend components

**Placeholder scan:** No TBDs, TODOs, or vague instructions found.

**Type consistency:** DocumentStatus, DocumentResponse, ParseResponse — all consistent across tasks.
