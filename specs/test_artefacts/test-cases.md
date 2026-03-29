# Test Cases -- PE Document Intelligence Platform

---

## E1-S1: Database Types & ORM Models

### TC-E1S1-01: Core table ORM models defined
**AC:** 1
**Precondition:** SQLAlchemy models module importable
**Steps:**
1. Import all ORM models from the models module
2. Verify 8 core model classes exist: Document, DocumentCategory, ExtractionSchema, ExtractionField, ExtractedValue, DocumentSummary, BulkJob, BulkJobDocument
**Expected:** All 8 model classes are importable and inherit from the declarative base

### TC-E1S1-02: Memory models defined
**AC:** 2
**Precondition:** SQLAlchemy models module importable
**Steps:**
1. Import ConversationSummary and MemoryEntry models
2. Verify both models have correct table names (conversation_summaries, memory_entries)
**Expected:** Both memory model classes are importable with correct __tablename__

### TC-E1S1-03: DocumentStatus enum values
**AC:** 3
**Precondition:** None
**Steps:**
1. Import DocumentStatus enum
2. Assert all 7 values exist: uploaded, parsed, edited, classified, extracted, summarized, ingested
**Expected:** Enum contains exactly 7 members with correct string values

### TC-E1S1-04: UUID primary keys with server defaults
**AC:** 4
**Precondition:** None
**Steps:**
1. For each ORM model, inspect the `id` column
2. Verify column type is UUID and has server_default set
**Expected:** All models use UUID PKs with server-side default generation

### TC-E1S1-05: Timestamp columns present
**AC:** 5
**Precondition:** None
**Steps:**
1. For each ORM model, inspect columns
2. Verify created_at and updated_at columns exist with DateTime type
**Expected:** All models include both timestamp columns

### TC-E1S1-06: Foreign key relationships
**AC:** 6
**Precondition:** None
**Steps:**
1. Inspect Document model for document_category_id FK to document_categories
2. Inspect ExtractionSchema for category_id FK
3. Inspect ExtractionField for schema_id FK
4. Inspect ExtractedValue for document_id and field_id FKs
5. Inspect DocumentSummary for document_id FK
6. Inspect BulkJobDocument for bulk_job_id and document_id FKs
**Expected:** All foreign key relationships correctly defined

---

## E1-S2: Application Configuration

### TC-E1S2-01: config.yml loaded correctly
**AC:** 1
**Precondition:** config.yml exists with valid YAML
**Steps:**
1. Load configuration
2. Verify storage paths, chunking params, bulk concurrency, RAG defaults are accessible
**Expected:** All config.yml values accessible as typed attributes

### TC-E1S2-02: Environment variables loaded
**AC:** 2
**Precondition:** .env file with required variables
**Steps:**
1. Load settings with valid .env
2. Access OPENAI_API_KEY, REDUCTO_API_KEY, DATABASE_URL, WEAVIATE_URL, OPENAI_MODEL
**Expected:** All environment variables loaded correctly

### TC-E1S2-03: Pydantic validation
**AC:** 3
**Precondition:** None
**Steps:**
1. Verify settings object is a Pydantic BaseSettings instance
2. Test that invalid types raise ValidationError
**Expected:** Type validation enforced by Pydantic

### TC-E1S2-04: Missing required env vars raise clear error
**AC:** 4
**Precondition:** .env missing OPENAI_API_KEY
**Steps:**
1. Attempt to load settings without OPENAI_API_KEY
2. Catch the error
**Expected:** Clear error message mentioning "OPENAI_API_KEY"

### TC-E1S2-05: Default values applied
**AC:** 5
**Precondition:** config.yml without optional values
**Steps:**
1. Load config without specifying upload_dir, parsed_dir, max_tokens, overlap_tokens
2. Verify defaults: upload_dir="./data/upload", parsed_dir="./data/parsed", max_tokens=512, overlap_tokens=100
**Expected:** Default values applied when not specified

---

## E1-S3: Database Connection & Migrations

### TC-E1S3-01: Async engine with asyncpg
**AC:** 1
**Precondition:** DATABASE_URL set
**Steps:**
1. Create async engine
2. Verify engine uses asyncpg driver
**Expected:** Engine dialect is postgresql+asyncpg

### TC-E1S3-02: Connection pool settings
**AC:** 2
**Precondition:** None
**Steps:**
1. Inspect session factory configuration
2. Verify pool_size=5, max_overflow=10
**Expected:** Pool configured as specified

### TC-E1S3-03: Alembic migration creates all tables
**AC:** 3, 4
**Precondition:** Empty PostgreSQL database
**Steps:**
1. Run `alembic upgrade head`
2. Query pg_tables for all expected table names
**Expected:** 10 tables created (8 core + 2 memory)

### TC-E1S3-04: Alembic upgrade runs successfully
**AC:** 5
**Precondition:** Empty PostgreSQL 16 database
**Steps:**
1. Run `alembic upgrade head` against empty database
2. Check exit code
**Expected:** Exit code 0, no errors

---

## E1-S4: FastAPI Application Factory + Health Endpoint

### TC-E1S4-01: CORS middleware configured
**AC:** 1
**Precondition:** App factory callable
**Steps:**
1. Create app via factory
2. Verify CORS middleware is in middleware stack with localhost origins
**Expected:** CORS middleware present allowing localhost

### TC-E1S4-02: Health endpoint returns 200 when DB reachable
**AC:** 2
**Precondition:** PostgreSQL running
**Steps:**
1. GET /api/v1/health
**Expected:** 200 with `{"status": "healthy"}`

### TC-E1S4-03: Health endpoint returns 503 when DB unreachable
**AC:** 3
**Precondition:** PostgreSQL stopped
**Steps:**
1. GET /api/v1/health with DB down
**Expected:** 503 with `{"status": "unhealthy", "detail": "..."}`

### TC-E1S4-04: API prefix and lifespan
**AC:** 4, 5
**Precondition:** None
**Steps:**
1. Verify all routes have /api/v1 prefix
2. Start app, verify DB pool initialized
3. Shutdown app, verify pool closed
**Expected:** All routes prefixed; lifespan manages DB pool

---

## E2-S1: Document Repository + Upload Service + API

### TC-E2S1-01: Repository CRUD operations
**AC:** 1
**Precondition:** Test database with migrations applied
**Steps:**
1. Create document via repository
2. Get by ID
3. List all (verify included)
4. Delete
5. Get by ID again
**Expected:** Create returns record, get returns it, list includes it, delete removes it, subsequent get returns None/404

### TC-E2S1-02: Upload endpoint creates document
**AC:** 2
**Precondition:** Backend running
**Steps:**
1. POST /api/v1/documents/upload with multipart PDF file
2. Verify response contains id, file_name, status=uploaded
3. Verify file exists in upload_dir
**Expected:** 200/201 with document details, file persisted to disk

### TC-E2S1-03: SHA-256 dedup returns existing document
**AC:** 3
**Precondition:** Document already uploaded with known hash
**Steps:**
1. POST /api/v1/documents/upload with identical file content
2. Verify response returns the existing document ID (not a new one)
**Expected:** Same document ID returned, no duplicate record created

### TC-E2S1-04: SHA-256 dedup allows different files
**AC:** 3 (boundary)
**Precondition:** Document already uploaded
**Steps:**
1. POST /api/v1/documents/upload with a different file
2. Verify a new document ID is returned
**Expected:** New document created with unique ID

### TC-E2S1-05: List endpoint returns all documents
**AC:** 4
**Precondition:** 2+ documents uploaded
**Steps:**
1. GET /api/v1/documents
2. Verify response is a list with expected fields per item
**Expected:** Array of documents with id, file_name, status, document_category_id, file_type, file_size, created_at

### TC-E2S1-06: Get single document
**AC:** 5
**Precondition:** Document exists
**Steps:**
1. GET /api/v1/documents/:id
**Expected:** Full document details returned

### TC-E2S1-07: Get non-existent document returns 404
**AC:** 5 (error path)
**Precondition:** None
**Steps:**
1. GET /api/v1/documents/nonexistent-uuid
**Expected:** 404 response

### TC-E2S1-08: Delete removes record and files
**AC:** 6
**Precondition:** Document uploaded and parsed
**Steps:**
1. DELETE /api/v1/documents/:id
2. Verify GET /api/v1/documents/:id returns 404
3. Verify files removed from upload_dir and parsed_dir
**Expected:** Record and files both deleted

---

## E2-S2: Document State Machine

### TC-E2S2-01: Valid transitions succeed
**AC:** 1
**Precondition:** Document in each starting state
**Steps:**
1. Transition uploaded->parsed
2. Transition parsed->edited
3. Transition parsed->classified
4. Transition edited->classified
5. Transition classified->extracted
6. Transition extracted->summarized
7. Transition summarized->ingested
**Expected:** All transitions succeed, status updated

### TC-E2S2-02: Invalid transition returns 400
**AC:** 2
**Precondition:** Document with status=uploaded
**Steps:**
1. Attempt transition uploaded->classified
**Expected:** 400 with message indicating current state and required prior state

### TC-E2S2-03: Atomic status and timestamp update
**AC:** 3
**Precondition:** Document with status=uploaded
**Steps:**
1. Record original updated_at
2. Transition to parsed
3. Verify status=parsed and updated_at changed
**Expected:** Both fields updated atomically

### TC-E2S2-04: get_available_actions returns valid transitions
**AC:** 4
**Precondition:** Documents in various states
**Steps:**
1. Call get_available_actions for document with status=uploaded -> expect [parsed]
2. Call for status=parsed -> expect [edited, classified]
3. Call for status=ingested -> expect []
**Expected:** Correct available actions per state

### TC-E2S2-05: Skip-state transition blocked
**AC:** 2 (boundary)
**Precondition:** Document with status=uploaded
**Steps:**
1. Attempt transition uploaded->extracted
**Expected:** 400 error

### TC-E2S2-06: Backward transition blocked
**AC:** 2 (boundary)
**Precondition:** Document with status=classified
**Steps:**
1. Attempt transition classified->uploaded
**Expected:** 400 error

---

## E2-S3: Reducto Parser Integration + Parse/Edit API

### TC-E2S3-01: Parse triggers Reducto and saves markdown
**AC:** 1, 2
**Precondition:** Document uploaded, Reducto API available (or mocked)
**Steps:**
1. POST /api/v1/parse/:id
2. Verify markdown content returned
3. Verify file saved to parsed_dir/{document_id}.md
4. Verify document.parsed_path updated
**Expected:** Markdown content returned and persisted

### TC-E2S3-02: Parse transitions status to parsed
**AC:** 3
**Precondition:** Document with status=uploaded
**Steps:**
1. POST /api/v1/parse/:id
2. GET /api/v1/documents/:id
3. Verify status=parsed
**Expected:** Status changed to parsed

### TC-E2S3-03: Get parsed content
**AC:** 4
**Precondition:** Document already parsed
**Steps:**
1. GET /api/v1/parse/:id/content
**Expected:** Parsed markdown content returned

### TC-E2S3-04: Get parsed content before parsing returns error
**AC:** 4 (error path)
**Precondition:** Document with status=uploaded (not parsed)
**Steps:**
1. GET /api/v1/parse/:id/content
**Expected:** 404 or appropriate error

### TC-E2S3-05: Save edited content transitions to edited
**AC:** 5
**Precondition:** Document with status=parsed
**Steps:**
1. PUT /api/v1/parse/:id/content with modified markdown
2. Verify status transitions to edited
3. GET /api/v1/parse/:id/content returns the new content
**Expected:** Content saved, status=edited

### TC-E2S3-06: Dedup skips parsing for unchanged file
**AC:** 6
**Precondition:** Document already parsed, file_hash unchanged
**Steps:**
1. POST /api/v1/parse/:id again
2. Verify 200 returned with existing content
3. Verify Reducto was NOT called again
**Expected:** Existing parsed content returned without re-parsing

### TC-E2S3-07: Parse non-existent document returns 404
**AC:** 3 (error path)
**Precondition:** None
**Steps:**
1. POST /api/v1/parse/nonexistent-uuid
**Expected:** 404

---

## E3-S1: DeepAgent Orchestrator Scaffold

### TC-E3S1-01: Orchestrator creation
**AC:** 1
**Precondition:** OPENAI_API_KEY set
**Steps:**
1. Create orchestrator via create_deep_agent with model="openai:gpt-5.4-mini"
2. Verify agent is created without error
**Expected:** Agent instance returned

### TC-E3S1-02: Subagent registry
**AC:** 2
**Precondition:** Orchestrator created
**Steps:**
1. Verify 5 named subagent slots registered: classifier, extractor, judge, summarizer, rag_retriever
**Expected:** All 5 slots exist in registry

### TC-E3S1-03: Middleware stack
**AC:** 3
**Precondition:** Orchestrator created
**Steps:**
1. Inspect middleware stack
2. Verify FilesystemMiddleware, SubAgentMiddleware, SummarizationMiddleware present
**Expected:** All 3 middleware registered

### TC-E3S1-04: Singleton factory and health check
**AC:** 4, 5
**Precondition:** None
**Steps:**
1. Get orchestrator via factory (first call)
2. Get orchestrator via factory (second call)
3. Verify same instance returned
4. Send basic health-check prompt
**Expected:** Same instance both times; health check responds without error

---

## E3-S2: PII Filtering Middleware

### TC-E3S2-01: SSN/Tax ID redaction
**AC:** 2, 4
**Precondition:** PII middleware registered
**Steps:**
1. Pass content containing "SSN: 123-45-6789"
2. Verify output contains "[REDACTED_SSN]"
**Expected:** SSN replaced with typed placeholder

### TC-E3S2-02: Phone number redaction
**AC:** 2, 4
**Precondition:** PII middleware registered
**Steps:**
1. Pass content with "(212) 555-1234" and "+1-800-555-0199"
**Expected:** Phone numbers replaced with [REDACTED_PHONE]

### TC-E3S2-03: Email and account redaction
**AC:** 2, 4
**Precondition:** PII middleware registered
**Steps:**
1. Pass content with "john.smith@investor.com" and "Account: 12345678, Routing: 021000021"
**Expected:** Email replaced with [REDACTED_EMAIL], account/routing with [REDACTED_ACCOUNT]

### TC-E3S2-04: Fund names and financial terms pass through
**AC:** 3
**Precondition:** PII middleware registered
**Steps:**
1. Pass content with "Horizon Equity Partners IV" and "management fee of 1.75%"
2. Verify these strings remain unredacted
**Expected:** Fund names and financial terms preserved verbatim

### TC-E3S2-05: Original content never reaches LLM
**AC:** 5
**Precondition:** PII middleware registered as pre-model callback
**Steps:**
1. Inject content with PII into agent pipeline
2. Intercept the content sent to the LLM
3. Verify no unredacted PII present
**Expected:** Only redacted version passed to LLM

### TC-E3S2-06: US street address redaction
**AC:** 2, 4
**Precondition:** PII middleware registered
**Steps:**
1. Pass content with "123 Main Street, Suite 400, New York, NY 10001"
**Expected:** Address replaced with [REDACTED_ADDRESS]

---

## E3-S3: Short-Term Memory (Session-Based)

### TC-E3S3-01: Per-session message storage
**AC:** 1
**Precondition:** ShortTermMemory instantiated with default max_messages=20
**Steps:**
1. Add messages to session "s1"
2. Get messages for "s1"
3. Verify messages returned only for "s1"
**Expected:** Messages stored and retrieved per session

### TC-E3S3-02: Message trimming
**AC:** 2
**Precondition:** ShortTermMemory with max_messages=5
**Steps:**
1. Add a system message + 6 human/AI message pairs
2. Get messages
3. Verify system message preserved + only most recent messages kept within limit
**Expected:** System message + most recent messages, total <= max_messages

### TC-E3S3-03: CRUD operations
**AC:** 3
**Precondition:** ShortTermMemory instance
**Steps:**
1. add_human_message("s1", "hello")
2. add_ai_message("s1", "hi")
3. get_messages("s1") -> 2 messages
4. clear_session("s1") -> get_messages returns empty
5. delete_session("s1") -> session no longer exists
**Expected:** All operations work correctly

### TC-E3S3-04: Conversation summary
**AC:** 4
**Precondition:** Session with 10+ messages
**Steps:**
1. Add 10 messages (5 exchanges) to session
2. Call get_conversation_summary("s1")
3. Verify returns formatted text of last 6 messages
**Expected:** Summary contains last 3 human/AI exchanges

### TC-E3S3-05: Session count
**AC:** 5
**Precondition:** Multiple sessions created
**Steps:**
1. Create sessions s1, s2, s3
2. Call get_session_count()
3. Delete s2
4. Call get_session_count()
**Expected:** Returns 3, then 2

---

## E3-S4: Long-Term Memory (PostgreSQL-Backed)

### TC-E3S4-01: Migration creates tables
**AC:** 1
**Precondition:** Test database
**Steps:**
1. Run migration
2. Verify conversation_summaries and memory_entries tables exist
**Expected:** Both tables created

### TC-E3S4-02: Conversation summary upsert
**AC:** 2, 3
**Precondition:** Tables created
**Steps:**
1. save_conversation_summary with session_id="s1", agent_type="rag", summary="test", key_topics=["LPA"], documents_discussed=["doc_001"], queries_count=5
2. get_conversation_summary("s1") -> verify data
3. save_conversation_summary with same session_id but updated summary
4. get_conversation_summary("s1") -> verify updated (upsert)
**Expected:** Save and retrieve work; second save updates existing record

### TC-E3S4-03: Generic key-value store CRUD
**AC:** 4
**Precondition:** Tables created
**Steps:**
1. put("settings", "theme", {"mode": "dark"})
2. get("settings", "theme") -> {"mode": "dark"}
3. search("settings") -> includes "theme" entry
4. delete("settings", "theme")
5. get("settings", "theme") -> None
**Expected:** Full CRUD cycle works with JSONB data

### TC-E3S4-04: Async operations
**AC:** 5
**Precondition:** Tables created
**Steps:**
1. Verify all functions are async (coroutines)
2. Call concurrently and verify no deadlocks
**Expected:** All operations are async-compatible

### TC-E3S4-05: Retry on transient errors
**AC:** 5
**Precondition:** Mock database with intermittent failures
**Steps:**
1. Configure mock to fail first call, succeed second
2. Call put()
3. Verify operation succeeds after retry
**Expected:** Transient errors retried and recovered

---

## E4-S1: Category & Extraction Schema CRUD

### TC-E4S1-01: List categories
**AC:** 1
**Precondition:** Categories seeded
**Steps:**
1. GET /api/v1/config/categories
**Expected:** Array of categories with id, name, description, classification_criteria

### TC-E4S1-02: Create category
**AC:** 2
**Precondition:** Backend running
**Steps:**
1. POST /api/v1/config/categories with name="Test Category", description="Test", classification_criteria="Contains test content"
**Expected:** 201 with created record including generated id

### TC-E4S1-03: Update category
**AC:** 3
**Precondition:** Category exists
**Steps:**
1. PUT /api/v1/config/categories/:id with updated name
**Expected:** 200 with updated record

### TC-E4S1-04: Delete category succeeds when no documents assigned
**AC:** 4
**Precondition:** Category with no documents
**Steps:**
1. DELETE /api/v1/config/categories/:id
**Expected:** 200/204, category removed

### TC-E4S1-05: Delete category blocked when documents assigned
**AC:** 4 (error path)
**Precondition:** Category with assigned documents
**Steps:**
1. DELETE /api/v1/config/categories/:id
**Expected:** 400 with message about assigned documents

### TC-E4S1-06: List extraction fields for category
**AC:** 5
**Precondition:** Category with extraction fields
**Steps:**
1. GET /api/v1/config/categories/:id/fields
**Expected:** Array of fields ordered by sort_order

### TC-E4S1-07: Create/update extraction fields
**AC:** 6
**Precondition:** Category exists
**Steps:**
1. POST /api/v1/config/categories/:id/fields with list of field definitions
**Expected:** Fields created/updated with correct attributes

### TC-E4S1-08: Default category seeded on startup
**AC:** 7
**Precondition:** Empty database, app started
**Steps:**
1. GET /api/v1/config/categories
2. Verify "Other/Unclassified" category exists
**Expected:** Default category present without manual creation

---

## E4-S2: Classifier Subagent

### TC-E4S2-01: Classifier subagent registered
**AC:** 1
**Precondition:** Orchestrator initialized
**Steps:**
1. Verify classifier subagent exists in registry
2. Verify it has get_categories and get_parsed_content tools
**Expected:** Subagent registered with correct tools

### TC-E4S2-02: Returns structured ClassificationResult
**AC:** 2
**Precondition:** Document parsed, categories defined
**Steps:**
1. Run classifier on a parsed LPA document
2. Verify response contains category_id (UUID), category_name (str), reasoning (str)
**Expected:** Structured output with all required fields

### TC-E4S2-03: PII middleware applied
**AC:** 3
**Precondition:** Document with PII content
**Steps:**
1. Run classifier on document with PII
2. Verify LLM received redacted content
**Expected:** PII redacted before classification

### TC-E4S2-04: Returned category must exist in DB
**AC:** 4
**Precondition:** Categories in DB
**Steps:**
1. Run classifier
2. Verify returned category_id exists in database
**Expected:** Valid category_id returned

### TC-E4S2-05: Low-confidence defaults to Other/Unclassified
**AC:** 5
**Precondition:** Document that does not match any category (e.g., board minutes)
**Steps:**
1. Run classifier on non-matching document
**Expected:** Returns "Other/Unclassified" category

---

## E4-S3: Classification API Endpoint

### TC-E4S3-01: Classify triggers subagent
**AC:** 1
**Precondition:** Document with status=parsed
**Steps:**
1. POST /api/v1/classify/:id
**Expected:** 200 with classification result

### TC-E4S3-02: Response includes classification details
**AC:** 2
**Precondition:** Classification triggered
**Steps:**
1. Verify response contains category_id, category_name, reasoning
**Expected:** All fields present in response

### TC-E4S3-03: Classification saved to document
**AC:** 3
**Precondition:** Classification triggered
**Steps:**
1. POST /api/v1/classify/:id
2. GET /api/v1/documents/:id
3. Verify document_category_id matches classification result
**Expected:** Category persisted on document record

### TC-E4S3-04: Status transitions to classified
**AC:** 4
**Precondition:** Document with status=parsed
**Steps:**
1. POST /api/v1/classify/:id
2. GET /api/v1/documents/:id
3. Verify status=classified
**Expected:** Status changed to classified

### TC-E4S3-05: Returns 400 for wrong status
**AC:** 5
**Precondition:** Document with status=uploaded (not parsed or edited)
**Steps:**
1. POST /api/v1/classify/:id
**Expected:** 400 with message about required status

---

## E5-S1: Extractor Subagent with Dynamic Pydantic Models

### TC-E5S1-01: Extractor subagent registered with tools
**AC:** 1
**Precondition:** Orchestrator initialized
**Steps:**
1. Verify extractor subagent in registry with get_extraction_schema and get_parsed_content tools
**Expected:** Subagent registered with both tools

### TC-E5S1-02: Dynamic Pydantic model from schema
**AC:** 2
**Precondition:** Extraction fields defined for LPA category
**Steps:**
1. Build dynamic model from 8 LPA fields
2. Verify model has 8 attributes with correct types (str, float based on data_type)
**Expected:** Dynamic model matches schema definition

### TC-E5S1-03: ExtractionResult structure
**AC:** 3
**Precondition:** Extractor run on LPA document
**Steps:**
1. Verify result contains list of ExtractedField with field_name, extracted_value, source_text
**Expected:** One ExtractedField per schema field

### TC-E5S1-04: PII middleware and structured output
**AC:** 4, 5
**Precondition:** Document with PII
**Steps:**
1. Run extractor
2. Verify PII filtered before LLM
3. Verify response_format uses dynamic Pydantic model
**Expected:** PII redacted; structured output enforced

---

## E5-S2: Judge Subagent with Confidence Scoring

### TC-E5S2-01: Judge is independent subagent
**AC:** 1
**Precondition:** Orchestrator initialized
**Steps:**
1. Verify judge subagent exists separately from extractor
2. Verify it has get_extracted_values and get_parsed_content tools
**Expected:** Independent subagent with correct tools

### TC-E5S2-02: Per-field evaluation
**AC:** 2
**Precondition:** Extraction results available
**Steps:**
1. Run judge on extraction results
2. Verify each field has an evaluation
**Expected:** One FieldEvaluation per extracted field

### TC-E5S2-03: Confidence levels
**AC:** 3
**Precondition:** Extraction results with varying quality
**Steps:**
1. Run judge
2. Verify each field has confidence in {"high", "medium", "low"} and reasoning string
**Expected:** Valid confidence levels with reasoning

### TC-E5S2-04: Confidence criteria enforcement
**AC:** 4
**Precondition:** Known extraction results
**Steps:**
1. Field with explicit source text -> expect "high"
2. Field requiring interpretation -> expect "medium"
3. Field with contradictory sources -> expect "low"
**Expected:** Confidence aligned with criteria definitions

---

## E5-S3: Extraction API + Results Repository + Review Gate

### TC-E5S3-01: Repository save and get operations
**AC:** 1
**Precondition:** Test database
**Steps:**
1. save_results with extraction data
2. get_by_document_id
3. Verify data matches
**Expected:** Results persisted and retrievable

### TC-E5S3-02: Extract endpoint runs extractor then judge
**AC:** 2
**Precondition:** Document with status=classified, extraction schema defined
**Steps:**
1. POST /api/v1/extract/:id
2. Verify results include confidence scores
**Expected:** 200 with extraction results including confidence from judge

### TC-E5S3-03: Get extraction results
**AC:** 3
**Precondition:** Extraction completed for document
**Steps:**
1. GET /api/v1/extract/:id/results
2. Verify each field has: field_name, display_name, extracted_value, source_text, confidence, confidence_reasoning, requires_review, reviewed
**Expected:** Complete result set returned

### TC-E5S3-04: Update specific field values
**AC:** 4
**Precondition:** Extraction results exist
**Steps:**
1. PUT /api/v1/extract/:id/results with updated value for field_name="governing_law"
2. GET /api/v1/extract/:id/results
3. Verify field updated and reviewed=true
**Expected:** Field value updated, marked as reviewed

### TC-E5S3-05: Review gate blocks transition with unreviewed fields
**AC:** 5
**Precondition:** Extraction results with requires_review=true, reviewed=false fields
**Steps:**
1. Attempt to transition document status to extracted
**Expected:** Transition blocked

### TC-E5S3-06: Review gate error lists unreviewed fields
**AC:** 6
**Precondition:** Unreviewed required fields exist
**Steps:**
1. Attempt transition
2. Verify 400 response lists the unreviewed field names
**Expected:** 400 with field list

### TC-E5S3-07: Review gate passes after all fields reviewed
**AC:** 5 (success path)
**Precondition:** All requires_review fields have reviewed=true
**Steps:**
1. Review all flagged fields
2. Attempt transition to extracted
**Expected:** Transition succeeds

### TC-E5S3-08: Extract endpoint returns 400 for wrong status
**AC:** 2 (error path)
**Precondition:** Document with status=uploaded
**Steps:**
1. POST /api/v1/extract/:id
**Expected:** 400

---

## E6-S1: Summarizer Subagent + API

### TC-E6S1-01: Summarizer subagent registered
**AC:** 1
**Precondition:** Orchestrator initialized
**Steps:**
1. Verify summarizer subagent with get_parsed_content tool
2. Run and verify SummaryResult structure (summary, key_topics)
**Expected:** Subagent returns structured output

### TC-E6S1-02: PII middleware applied
**AC:** 2
**Precondition:** Document with PII
**Steps:**
1. Trigger summarization
2. Verify PII redacted before LLM call
**Expected:** Only redacted content sent to LLM

### TC-E6S1-03: Summary saved with content hash
**AC:** 3
**Precondition:** Document parsed
**Steps:**
1. POST /api/v1/summarize/:id
2. Verify document_summaries record created with SHA-256 content_hash
**Expected:** Summary persisted with hash

### TC-E6S1-04: Summarize endpoint transitions status
**AC:** 4
**Precondition:** Document with status=extracted
**Steps:**
1. POST /api/v1/summarize/:id
2. Verify status=summarized
3. Verify response includes summary + key_topics
**Expected:** Status transitioned, summary returned

### TC-E6S1-05: Get existing summary
**AC:** 5
**Precondition:** Summary exists
**Steps:**
1. GET /api/v1/summarize/:id
**Expected:** Summary returned; 404 if no summary exists

### TC-E6S1-06: Regeneration vs cache
**AC:** 6
**Precondition:** Summary exists, content unchanged
**Steps:**
1. POST /api/v1/summarize/:id (content unchanged) -> returns cached
2. Edit parsed content (hash changes)
3. POST /api/v1/summarize/:id -> regenerates
**Expected:** Cached when hash matches; regenerated when hash differs

---

## E6-S2: Weaviate Client + Semantic Chunking + Ingestion

### TC-E6S2-01: Weaviate client connects
**AC:** 1
**Precondition:** Weaviate running on WEAVIATE_URL
**Steps:**
1. Initialize Weaviate client
2. Verify connection successful
**Expected:** Client connected

### TC-E6S2-02: Collection created on startup
**AC:** 2
**Precondition:** Weaviate running
**Steps:**
1. Start application
2. Verify DocumentChunks collection exists with text2vec-openai vectorizer
**Expected:** Collection present with hybrid search enabled

### TC-E6S2-03: Semantic chunking
**AC:** 3
**Precondition:** Parsed markdown available
**Steps:**
1. Chunk a long document
2. Verify chunks split on semantic boundaries
3. Verify no chunk exceeds 512 tokens, overlap is ~100 tokens
**Expected:** Semantically coherent chunks within size limits

### TC-E6S2-04: Ingest endpoint
**AC:** 4
**Precondition:** Document with status=summarized
**Steps:**
1. POST /api/v1/ingest/:id
2. Query Weaviate for chunks with document_id filter
3. Verify chunks have correct metadata (document_id, document_name, document_category, file_name, chunk_index, created_at)
**Expected:** Chunks upserted with metadata

### TC-E6S2-05: Re-ingestion replaces chunks
**AC:** 5, 6
**Precondition:** Document already ingested
**Steps:**
1. POST /api/v1/ingest/:id again
2. Verify old chunks deleted and new chunks inserted
3. Verify status=ingested
**Expected:** Clean re-ingestion, no duplicate chunks

---

## E6-S3: RAG Retriever Subagent + Query API

### TC-E6S3-01: RAG retriever subagent registered
**AC:** 1
**Precondition:** Orchestrator initialized
**Steps:**
1. Verify rag_retriever subagent with weaviate_hybrid_search tool
**Expected:** Subagent registered

### TC-E6S3-02: Alpha parameter controls search mode
**AC:** 2
**Precondition:** Documents ingested
**Steps:**
1. Query with alpha=0.0 (pure keyword)
2. Query with alpha=0.5 (hybrid)
3. Query with alpha=1.0 (pure semantic)
**Expected:** Different result rankings based on alpha

### TC-E6S3-03: Query endpoint accepts all parameters
**AC:** 3
**Precondition:** Documents ingested
**Steps:**
1. POST /api/v1/rag/query with query, scope=single_document, scope_id=doc_001, search_mode=hybrid, top_k=5
**Expected:** 200 with results

### TC-E6S3-04: Response includes citations
**AC:** 4
**Precondition:** Query returns results
**Steps:**
1. Verify response has answer (str) and citations list
2. Each citation has chunk_text, document_name, document_id, relevance_score
**Expected:** Structured response with citations

### TC-E6S3-05: Scope filtering
**AC:** 5
**Precondition:** Multiple documents ingested across categories
**Steps:**
1. Query with scope=single_document, scope_id=doc_001 -> only doc_001 results
2. Query with scope=by_category, scope_id=cat_001 -> only LPA results
3. Query with scope=all -> results from all documents
**Expected:** Correct scope filtering applied

---

## E7-S1: Frontend App Shell, Routing, API Client

### TC-E7S1-01: Project scaffold
**AC:** 1
**Precondition:** Frontend project built
**Steps:**
1. Verify React 19 + Vite + TypeScript
2. Verify Tailwind CSS 4 configured
**Expected:** Project builds successfully

### TC-E7S1-02: Routes configured
**AC:** 2
**Precondition:** Frontend running
**Steps:**
1. Verify all routes resolve: /, /upload, /documents/:id/parse, /documents/:id/classify, /documents/:id/extract, /documents/:id/summary, /documents/:id/chat, /config/categories, /config/extraction-fields, /bulk
**Expected:** No 404 for defined routes

### TC-E7S1-03: API client configuration
**AC:** 3
**Precondition:** None
**Steps:**
1. Verify Axios baseURL is http://localhost:8000/api/v1
2. Verify snake_case/camelCase transformers applied
**Expected:** API client configured correctly

### TC-E7S1-04: TanStack Query configuration
**AC:** 4
**Precondition:** None
**Steps:**
1. Verify staleTime=5min
2. Verify no retry on 404/401/403
3. Verify max 2 retries with exponential backoff
**Expected:** Query client configured as specified

---

## E7-S2: Dashboard -- Document List with Status

### TC-E7S2-01: Dashboard renders document table
**AC:** 1
**Layer:** E2E
**Precondition:** Documents exist in database
**Steps:**
1. Navigate to /
2. Verify table with columns: file_name, status, category, file_type, file_size, created_at
**Expected:** Table visible with document data
**Playwright file:** e2e/E7-S2.spec.ts

### TC-E7S2-02: Status badges color-coded
**AC:** 2
**Layer:** E2E + Unit
**Precondition:** Documents in various statuses
**Steps:**
1. Verify each status renders correct color badge
**Expected:** uploaded=gray, parsed=blue, classified=yellow, extracted=orange, summarized=purple, ingested=green
**Playwright file:** e2e/E7-S2.spec.ts

### TC-E7S2-03: Row links to next action
**AC:** 3
**Layer:** E2E
**Precondition:** Document with status=uploaded
**Steps:**
1. Click document row
2. Verify navigation to /documents/:id/parse
**Expected:** Navigation to correct next-action page

### TC-E7S2-04: Empty state with CTA
**AC:** 4
**Layer:** E2E
**Precondition:** No documents in database
**Steps:**
1. Navigate to /
2. Verify empty state message
3. Verify link to /upload
**Expected:** Empty state with upload CTA visible

### TC-E7S2-05: Auto-refresh
**AC:** 5
**Layer:** Unit
**Precondition:** TanStack Query configured
**Steps:**
1. Verify refetchInterval=30000 on document list query
**Expected:** List refreshes every 30 seconds

### TC-E7S2-06: Document details shown in columns
**AC:** 1 (completeness)
**Layer:** E2E
**Precondition:** Document with known data
**Steps:**
1. Navigate to /
2. Verify file_name, file_type, file_size values visible for a known document
**Expected:** Correct data displayed in each column

---

## E7-S3: Upload Page with Drag-Drop

### TC-E7S3-01: Upload page renders drag-drop zone
**AC:** 1
**Layer:** E2E
**Precondition:** None
**Steps:**
1. Navigate to /upload
2. Verify drag-drop zone visible
**Expected:** Dropzone component rendered
**Playwright file:** e2e/E7-S3.spec.ts

### TC-E7S3-02: Accepted file types
**AC:** 2
**Layer:** E2E
**Precondition:** None
**Steps:**
1. Verify dropzone accepts .pdf, .docx, .xlsx, .png, .jpg, .tiff
**Expected:** Accepted file types listed in UI

### TC-E7S3-03: Upload progress shown
**AC:** 3
**Layer:** E2E
**Precondition:** None
**Steps:**
1. Upload a file
2. Verify progress indicator visible during upload
**Expected:** Progress indicator appears and completes

### TC-E7S3-04: Duplicate file notification
**AC:** 4
**Layer:** E2E
**Precondition:** File already uploaded
**Steps:**
1. Upload same file again
2. Verify "File already exists" notification with link to existing document
**Expected:** Duplicate notification shown

### TC-E7S3-05: Successful upload navigates to parse
**AC:** 5
**Layer:** E2E
**Precondition:** None
**Steps:**
1. Upload a new file
2. Verify navigation to /documents/:id/parse
**Expected:** Redirected to parse page for new document

### TC-E7S3-06: Rejected file type shows error
**AC:** 2 (error path)
**Layer:** E2E
**Precondition:** None
**Steps:**
1. Attempt to upload a .txt file
**Expected:** Rejection message or file type error displayed

---

## E7-S4: Parse/Edit Page with TipTap Split View

### TC-E7S4-01: Split view layout
**AC:** 1
**Layer:** E2E
**Precondition:** Document uploaded
**Steps:**
1. Navigate to /documents/:id/parse
2. Verify document info panel on left, editor on right
**Expected:** Split view rendered
**Playwright file:** e2e/E7-S4.spec.ts

### TC-E7S4-02: TipTap editor loads parsed content
**AC:** 2
**Layer:** E2E
**Precondition:** Document parsed
**Steps:**
1. Navigate to parse page for a parsed document
2. Verify TipTap editor contains parsed markdown content
**Expected:** Editor populated with content

### TC-E7S4-03: Parse Document button
**AC:** 3
**Layer:** E2E
**Precondition:** Document with status=uploaded
**Steps:**
1. Click "Parse Document" button
2. Verify loading spinner appears
3. Verify content appears in editor after completion
**Expected:** Parse triggered, content loaded

### TC-E7S4-04: Parse button disabled after parsing
**AC:** 3 (boundary)
**Layer:** E2E
**Precondition:** Document with status=parsed
**Steps:**
1. Navigate to parse page
2. Verify "Parse Document" button is disabled
**Expected:** Button disabled for already-parsed documents

### TC-E7S4-05: Save Edits transitions to edited
**AC:** 4
**Layer:** E2E
**Precondition:** Document with status=parsed, editor has modified content
**Steps:**
1. Modify content in editor
2. Click "Save Edits"
3. Verify save succeeds
**Expected:** Content saved, status transitions to edited

### TC-E7S4-06: Proceed to Classify button
**AC:** 5
**Layer:** E2E
**Precondition:** Document with status=parsed or edited
**Steps:**
1. Verify "Proceed to Classify" button is visible
2. Click it
3. Verify navigation to /documents/:id/classify
**Expected:** Navigation to classification page

---

## E8-S1: Config Management Pages

### TC-E8S1-01: Category list displayed
**AC:** 1
**Layer:** E2E
**Precondition:** Categories exist
**Steps:**
1. Navigate to /config/categories
2. Verify card list with name, description, edit/delete actions
**Expected:** Category cards rendered
**Playwright file:** e2e/E8-S1.spec.ts

### TC-E8S1-02: Add category modal
**AC:** 2
**Layer:** E2E
**Precondition:** None
**Steps:**
1. Click add category button
2. Fill name (required), description, classification_criteria
3. Submit
**Expected:** Modal opens, form submits, new category appears in list

### TC-E8S1-03: Edit category modal
**AC:** 2
**Layer:** E2E
**Precondition:** Category exists
**Steps:**
1. Click edit on a category
2. Modify name
3. Submit
**Expected:** Category updated in list

### TC-E8S1-04: Delete category - no documents
**AC:** 3
**Layer:** E2E
**Precondition:** Category with no documents
**Steps:**
1. Click delete
2. Confirm in dialog
**Expected:** Category removed from list

### TC-E8S1-05: Delete category - has documents (disabled)
**AC:** 3 (error path)
**Layer:** E2E
**Precondition:** Category with assigned documents
**Steps:**
1. Verify delete button is disabled or shows warning
**Expected:** Delete blocked for categories with documents

### TC-E8S1-06: Extraction field editor
**AC:** 4
**Layer:** E2E
**Precondition:** Category with fields
**Steps:**
1. Navigate to /config/extraction-fields
2. Verify fields grouped by category
**Expected:** Fields displayed with drag-drop reordering

### TC-E8S1-07: Add/edit extraction field form
**AC:** 5
**Layer:** E2E
**Precondition:** Category exists
**Steps:**
1. Click add field
2. Fill field_name, display_name, description, examples, data_type (dropdown), required (checkbox)
3. Submit
**Expected:** Field created with correct attributes

---

## E8-S2: Classification Page with Override

### TC-E8S2-01: Classification result displayed
**AC:** 1
**Layer:** E2E
**Precondition:** Document classified
**Steps:**
1. Navigate to /documents/:id/classify
2. Verify category name and reasoning text shown
**Expected:** Classification result visible
**Playwright file:** e2e/E8-S2.spec.ts

### TC-E8S2-02: Classify button triggers API
**AC:** 2
**Layer:** E2E
**Precondition:** Document with status=parsed
**Steps:**
1. Click "Classify" button
2. Verify loading state appears
3. Verify result appears after completion
**Expected:** Classification triggered and result displayed

### TC-E8S2-03: Category override dropdown
**AC:** 3
**Layer:** E2E
**Precondition:** Document classified
**Steps:**
1. Open category dropdown
2. Select different category
3. Verify category updated
**Expected:** Override persisted

### TC-E8S2-04: Accept and Proceed navigation
**AC:** 4
**Layer:** E2E
**Precondition:** Document classified
**Steps:**
1. Click "Accept & Proceed"
2. Verify navigation to /documents/:id/extract
**Expected:** Navigates to extraction page

### TC-E8S2-05: Wrong status shows 404/redirect
**AC:** 5
**Layer:** E2E
**Precondition:** Document with status=uploaded
**Steps:**
1. Navigate to /documents/:id/classify
**Expected:** 404 or redirect displayed

### TC-E8S2-06: Classification reasoning readable
**AC:** 1 (completeness)
**Layer:** E2E
**Precondition:** Document classified with reasoning
**Steps:**
1. Verify reasoning text is visible and contains meaningful content
**Expected:** Reasoning text displayed in readable format

---

## E8-S3: Extraction Results 3-Column View + Review Gate

### TC-E8S3-01: 3-column table rendered
**AC:** 1
**Layer:** E2E
**Precondition:** Extraction results exist
**Steps:**
1. Navigate to /documents/:id/extract
2. Verify table with Field Name + badge, Extracted Value, Source Text columns
**Expected:** 3-column layout visible
**Playwright file:** e2e/E8-S3.spec.ts

### TC-E8S3-02: Confidence badges color-coded
**AC:** 2
**Layer:** E2E
**Precondition:** Fields with different confidence levels
**Steps:**
1. Verify green badge for high confidence
2. Verify yellow badge for medium confidence
3. Verify red badge for low confidence
4. Hover for tooltip with reasoning
**Expected:** Correct colors and tooltip

### TC-E8S3-03: Low-confidence rows highlighted
**AC:** 3
**Layer:** E2E
**Precondition:** Field with low confidence
**Steps:**
1. Verify amber background on low-confidence row
2. Verify "Requires Review" label visible
3. Verify "Edit" button visible
**Expected:** Visual highlighting and review controls

### TC-E8S3-04: Inline editing flow
**AC:** 4
**Layer:** E2E
**Precondition:** Low-confidence field requiring review
**Steps:**
1. Click "Edit" on a flagged field
2. Verify input appears with current value
3. Change value and save
4. Verify field marked as reviewed
**Expected:** Edit -> save -> reviewed=true

### TC-E8S3-05: Review gate blocks proceed button
**AC:** 5
**Layer:** E2E
**Precondition:** Unreviewed low-confidence fields exist
**Steps:**
1. Verify "Save & Proceed to Summary" button is disabled
2. Verify message "Review all flagged fields first" visible
**Expected:** Button disabled with explanation

### TC-E8S3-06: Review gate passes after review
**AC:** 5 (success path)
**Layer:** E2E
**Precondition:** All flagged fields reviewed
**Steps:**
1. Review all flagged fields
2. Verify "Save & Proceed to Summary" button becomes enabled
3. Click it
4. Verify navigation to /documents/:id/summary
**Expected:** Button enabled, navigation succeeds

### TC-E8S3-07: Extract button triggers API
**AC:** 6
**Layer:** E2E
**Precondition:** Document with status=classified
**Steps:**
1. Click "Extract" button
2. Verify loading state
3. Verify results appear
**Expected:** Extraction triggered and results displayed

### TC-E8S3-08: Extract button disabled during loading
**AC:** 6 (boundary)
**Layer:** E2E
**Precondition:** Extraction in progress
**Steps:**
1. Verify "Extract" button shows loading state and is not clickable
**Expected:** Prevents double submission

---

## E8-S4: Summary Page with Regenerate

### TC-E8S4-01: Summary text displayed
**AC:** 1
**Layer:** E2E
**Precondition:** Summary generated
**Steps:**
1. Navigate to /documents/:id/summary
2. Verify summary text visible
3. Verify key topics as tags below summary
**Expected:** Summary and topic tags rendered
**Playwright file:** e2e/E8-S4.spec.ts

### TC-E8S4-02: Generate Summary button
**AC:** 2
**Layer:** E2E
**Precondition:** Document with status=extracted, no summary yet
**Steps:**
1. Click "Generate Summary"
2. Verify loading state
3. Verify summary appears
**Expected:** Summary generated and displayed

### TC-E8S4-03: Regenerate replaces summary
**AC:** 3
**Layer:** E2E
**Precondition:** Summary already exists
**Steps:**
1. Click "Regenerate"
2. Verify new summary replaces old
**Expected:** Summary content updated

### TC-E8S4-04: Key topics as tag chips
**AC:** 4
**Layer:** E2E
**Precondition:** Summary with key_topics
**Steps:**
1. Verify each key topic rendered as a styled chip/tag
**Expected:** Topics displayed as distinct styled elements

### TC-E8S4-05: Proceed to Ingest and Chat
**AC:** 5
**Layer:** E2E
**Precondition:** Summary generated
**Steps:**
1. Click "Proceed to Ingest & Chat"
2. Verify ingestion triggered
3. Verify navigation to /documents/:id/chat
**Expected:** Document ingested, navigated to chat

### TC-E8S4-06: Summary page without summary shows generate prompt
**AC:** 2 (boundary)
**Layer:** E2E
**Precondition:** No summary exists for document
**Steps:**
1. Navigate to /documents/:id/summary
2. Verify "Generate Summary" is prominent; no summary text shown
**Expected:** Generate CTA displayed without stale content

---

## E8-S5: RAG Chat Page with Citations

### TC-E8S5-01: Chat interface rendered
**AC:** 1
**Layer:** E2E
**Precondition:** Document ingested
**Steps:**
1. Navigate to /documents/:id/chat
2. Verify message conversation interface with input field
**Expected:** Chat UI with input visible
**Playwright file:** e2e/E8-S5.spec.ts

### TC-E8S5-02: Scope selector
**AC:** 2
**Layer:** E2E
**Precondition:** Chat page loaded
**Steps:**
1. Verify "This Document" is default scope
2. Switch to "All Documents"
3. Switch to "By Category" and verify category dropdown appears
**Expected:** Scope options work, category dropdown conditional

### TC-E8S5-03: Search mode toggle
**AC:** 3
**Layer:** E2E
**Precondition:** Chat page loaded
**Steps:**
1. Verify Semantic, Keyword, Hybrid toggle options
2. Verify Hybrid is default
3. Switch between modes
**Expected:** Three search modes togglable

### TC-E8S5-04: Query submission and response
**AC:** 4
**Layer:** E2E
**Precondition:** Document ingested
**Steps:**
1. Type "What is the management fee rate?"
2. Submit query
3. Verify AI response with expandable citation cards
4. Verify citations show chunk_text, document_name, relevance_score
**Expected:** Answer with citations displayed

### TC-E8S5-05: Multi-turn conversation
**AC:** 5
**Layer:** E2E
**Precondition:** First query already submitted
**Steps:**
1. Submit second query
2. Verify both exchanges visible in chat history
**Expected:** Chat history maintained within session

### TC-E8S5-06: Empty query prevented
**AC:** 4 (boundary)
**Layer:** E2E
**Precondition:** Chat page loaded
**Steps:**
1. Attempt to submit empty query
**Expected:** Submit disabled or validation message

---

## E9-S1: LangGraph Bulk State Graph

### TC-E9S1-01: StateGraph with 7 nodes
**AC:** 1
**Precondition:** Pipeline module importable
**Steps:**
1. Instantiate the StateGraph
2. Verify 7 nodes: parse_node, classify_node, extract_node, judge_node, summarize_node, ingest_node, finalize_node
**Expected:** All nodes registered in graph

### TC-E9S1-02: DocumentState TypedDict
**AC:** 2
**Precondition:** None
**Steps:**
1. Inspect DocumentState
2. Verify fields: document_id, status, parsed_content, classification_result, extraction_results, judge_results, summary, error, timing metrics
**Expected:** All fields present in TypedDict

### TC-E9S1-03: Per-document error isolation
**AC:** 3
**Precondition:** 3 documents, one with corrupt content
**Steps:**
1. Run pipeline with 3 documents (one designed to fail at parse)
2. Verify failed document has error set
3. Verify other 2 documents processed successfully
**Expected:** Error captured on failed doc; others unaffected

### TC-E9S1-04: Concurrent processing
**AC:** 4
**Precondition:** 10+ documents
**Steps:**
1. Run pipeline with concurrent_documents=10
2. Verify parallel execution (timing < sequential)
**Expected:** Documents processed concurrently up to limit

### TC-E9S1-05: Checkpointing
**AC:** 5
**Precondition:** Pipeline with MemorySaver
**Steps:**
1. Start pipeline
2. Simulate failure mid-pipeline
3. Resume from checkpoint
4. Verify processing continues from interruption point
**Expected:** Pipeline resumable from checkpoint

---

## E9-S2: Bulk Job Repository + API

### TC-E9S2-01: Bulk job repository CRUD
**AC:** 1
**Precondition:** Test database
**Steps:**
1. Create bulk job
2. Get by ID
3. List all
4. Update status
**Expected:** All CRUD operations work

### TC-E9S2-02: Bulk upload creates job and starts pipeline
**AC:** 2
**Precondition:** Backend running
**Steps:**
1. POST /api/v1/bulk/upload with 3 PDF files
2. Verify response includes job ID with status=pending
3. Verify individual bulk_job_documents records created
**Expected:** Job created, processing started in background

### TC-E9S2-03: List bulk jobs
**AC:** 3
**Precondition:** Bulk jobs exist
**Steps:**
1. GET /api/v1/bulk/jobs
**Expected:** List with id, status, total_documents, processed_count, failed_count, created_at

### TC-E9S2-04: Get job details with per-document breakdown
**AC:** 4
**Precondition:** Bulk job with mixed results
**Steps:**
1. GET /api/v1/bulk/jobs/:id
**Expected:** Job details with per-document: document_id, file_name, status, error_message, processing_time_ms

### TC-E9S2-05: Failed documents have error message
**AC:** 5
**Precondition:** Bulk job with a failed document
**Steps:**
1. GET /api/v1/bulk/jobs/:id
2. Find failed document in breakdown
3. Verify error_message is populated
**Expected:** Failure reason captured in error_message

---

## E9-S3: Bulk Upload + Dashboard UI

### TC-E9S3-01: Bulk dashboard with job list
**AC:** 1
**Layer:** E2E
**Precondition:** Bulk jobs exist
**Steps:**
1. Navigate to /bulk
2. Verify job list with status badge, progress bar, timestamps
**Expected:** Job cards/rows visible with progress
**Playwright file:** e2e/E9-S3.spec.ts

### TC-E9S3-02: Multi-file upload zone
**AC:** 2
**Layer:** E2E
**Precondition:** None
**Steps:**
1. Verify "New Bulk Job" section with drag-drop zone
2. Upload multiple files
**Expected:** Multi-file upload zone functional

### TC-E9S3-03: Per-document progress view
**AC:** 3
**Layer:** E2E
**Precondition:** Bulk job with documents
**Steps:**
1. Expand a job row
2. Verify each document shows status indicator (pending=gray, processing=blue, completed=green, failed=red)
**Expected:** Per-document status visible

### TC-E9S3-04: Failed document error display
**AC:** 4
**Layer:** E2E
**Precondition:** Bulk job with a failed document
**Steps:**
1. Expand job with failure
2. Verify failed document shows error_message with error styling
**Expected:** Error text visible with red/error styling

### TC-E9S3-05: Auto-refresh during processing
**AC:** 5
**Layer:** E2E
**Precondition:** Bulk job with status=processing
**Steps:**
1. Navigate to /bulk
2. Verify data refreshes (5-second polling interval while processing)
**Expected:** Job status updates without manual refresh

### TC-E9S3-06: Progress bar accuracy
**AC:** 1 (completeness)
**Layer:** E2E
**Precondition:** Bulk job with known counts
**Steps:**
1. Verify progress bar shows processed_count / total_documents ratio
**Expected:** Progress bar matches actual counts
