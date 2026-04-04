"""FastAPI application factory with CORS middleware and lifespan management."""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routers import (
    audit,
    bulk,
    data_agent,
    events,
    classify,
    config,
    documents,
    extract,
    health,
    ingest,
    parse,
    rag,
    stream,
    summarize,
)
from src.db.connection import dispose_engine, get_session_factory, init_engine

logger = logging.getLogger(__name__)
request_logger = logging.getLogger("src.api.requests")


_DEFAULT_CATEGORIES: list[dict[str, str | None]] = [
    {
        "name": "Limited Partnership Agreement",
        "description": (
            "A Limited Partnership Agreement (LPA) is the foundational legal contract "
            "that governs the formation, operation, and dissolution of a private equity "
            "limited partnership fund. It defines the relationship between the General "
            "Partner (GP) — who manages the fund — and the Limited Partners (LPs) — who "
            "commit capital. The LPA establishes the economic terms of the fund including "
            "the management fee rate, carried interest (performance fee), preferred return "
            "hurdle, and the distribution waterfall that dictates how profits flow between "
            "LPs and the GP. It specifies the fund's lifecycle parameters such as the total "
            "fund term, commitment period (during which capital may be called for new "
            "investments), and any extension provisions. The agreement also covers governance "
            "matters including key person provisions, LP advisory committee roles, investment "
            "restrictions, removal and replacement of the GP, and reporting obligations. "
            "LPAs are typically governed by the laws of a specific jurisdiction, most "
            "commonly Delaware or the Cayman Islands."
        ),
        "classification_criteria": (
            "A document is a Limited Partnership Agreement if it contains a substantial "
            "number of the following elements: "
            "(1) Fund Name — the full legal name of the limited partnership fund; "
            "(2) General Partner — identification of the GP entity responsible for managing "
            "the fund; "
            "(3) Management Fee Rate — an annual percentage fee charged to LPs during the "
            "investment period (typically 1.5%–2.0%); "
            "(4) Carried Interest Rate — the GP's share of net profits as performance "
            "compensation (typically 20%); "
            "(5) Preferred Return — a minimum annualized hurdle rate LPs must earn before "
            "the GP participates in profit sharing (typically 8%); "
            "(6) Fund Term — the total duration from initial closing to final liquidation, "
            "usually expressed in years with extension provisions; "
            "(7) Commitment Period — the window during which the GP may call capital from "
            "LPs for new investments; "
            "(8) Governing Law — the jurisdiction whose laws govern the agreement. "
            "Additional indicators include: distribution waterfall provisions, capital call "
            "and drawdown mechanics, key person clauses, LP advisory committee terms, "
            "investment restrictions, clawback provisions, and indemnification clauses. "
            "The document will typically be titled 'Limited Partnership Agreement' or "
            "'Agreement of Limited Partnership' and will reference the formation of a "
            "limited partnership under applicable state or offshore partnership statutes."
        ),
    },
    {
        "name": "Subscription Agreement",
        "description": (
            "Agreement by which a limited partner commits capital to a fund, including "
            "representations, warranties, and investor qualification details."
        ),
        "classification_criteria": (
            "Document contains: capital commitment amount, investor representations and "
            "warranties, accredited investor qualification, tax identification, subscription "
            "terms, side letter references, anti-money laundering certifications."
        ),
    },
    {
        "name": "Side Letter",
        "description": (
            "Supplemental agreement between a GP and a specific LP granting preferential "
            "terms, fee discounts, co-investment rights, or reporting obligations."
        ),
        "classification_criteria": (
            "Document references a main LPA, is addressed to a specific LP, and contains: "
            "fee discount or waiver provisions, most-favored-nation clauses, co-investment "
            "rights, enhanced reporting requirements, excuse/exclusion rights, transfer "
            "restrictions modifications."
        ),
    },
    {
        "name": "Other/Unclassified",
        "description": (
            "Documents that do not match any defined PE document category. Includes "
            "amendments, board minutes, investor correspondence, and other ancillary "
            "materials."
        ),
        "classification_criteria": (
            "Default category for documents that do not match LPA, Subscription Agreement, "
            "or Side Letter criteria with sufficient confidence."
        ),
    },
]


_LPA_EXTRACTION_FIELDS: list[dict[str, str | bool | int]] = [
    {
        "field_name": "fund_name",
        "display_name": "Fund Name",
        "description": "The full legal name of the limited partnership fund as stated in the agreement.",
        "examples": "Horizon Equity Partners IV, L.P.; Apex Growth Equity Fund III, L.P.",
        "data_type": "string",
        "required": True,
        "sort_order": 1,
    },
    {
        "field_name": "general_partner",
        "display_name": "General Partner",
        "description": "The full legal name of the general partner entity responsible for managing the fund.",
        "examples": "Horizon Capital Management LLC; Apex Fund Advisors GP, LLC",
        "data_type": "string",
        "required": True,
        "sort_order": 2,
    },
    {
        "field_name": "management_fee_rate",
        "display_name": "Management Fee Rate",
        "description": "Annual management fee rate charged to limited partners during the investment period, expressed as a percentage.",
        "examples": "1.50%; 2.00%; 1.75%",
        "data_type": "percentage",
        "required": True,
        "sort_order": 3,
    },
    {
        "field_name": "carried_interest_rate",
        "display_name": "Carried Interest Rate",
        "description": "The percentage of net profits allocated to the general partner as performance compensation.",
        "examples": "20%; 15%; 25%",
        "data_type": "percentage",
        "required": True,
        "sort_order": 4,
    },
    {
        "field_name": "preferred_return",
        "display_name": "Preferred Return",
        "description": "The minimum annualized return rate that must be achieved by limited partners before the general partner participates in profit sharing.",
        "examples": "8%; 7%; 10%",
        "data_type": "percentage",
        "required": True,
        "sort_order": 5,
    },
    {
        "field_name": "fund_term",
        "display_name": "Fund Term",
        "description": "The total duration of the fund from initial closing to final liquidation, typically expressed in years.",
        "examples": "10 years; 12 years with two 1-year extensions",
        "data_type": "string",
        "required": True,
        "sort_order": 6,
    },
    {
        "field_name": "commitment_period",
        "display_name": "Commitment Period",
        "description": "The period during which the general partner may call capital from limited partners for new investments.",
        "examples": "5 years; 4 years from final closing",
        "data_type": "string",
        "required": True,
        "sort_order": 7,
    },
    {
        "field_name": "governing_law",
        "display_name": "Governing Law",
        "description": "The state or jurisdiction whose laws govern the partnership agreement.",
        "examples": "Delaware; Cayman Islands; State of New York",
        "data_type": "string",
        "required": False,
        "sort_order": 8,
    },
]


async def _seed_default_categories() -> None:
    """Seed default PE document categories and LPA extraction fields."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            from src.db.repositories.categories import CategoryRepository
            from src.db.repositories.extraction import (
                ExtractionFieldRepository,
                ExtractionSchemaRepository,
            )

            repo = CategoryRepository(session)
            count = await repo.count()
            if count == 0:
                for cat in _DEFAULT_CATEGORIES:
                    await repo.create(
                        name=cat["name"],  # type: ignore[arg-type]
                        description=cat["description"],
                        classification_criteria=cat["classification_criteria"],
                    )
                await session.flush()
                logger.info("Seeded %d default document categories", len(_DEFAULT_CATEGORIES))

            # Seed LPA extraction fields if none exist
            # Match flexibly — the name may be "Limited Partnership Agreement"
            # or "Limited Partnership Agreement - LPA" etc.
            all_cats = await repo.list_all()
            lpa_cat = next(
                (c for c in all_cats if "limited partnership" in c.name.lower()),
                None,
            )
            if lpa_cat is not None:
                schema_repo = ExtractionSchemaRepository(session)
                existing = await schema_repo.get_latest_for_category(lpa_cat.id)
                if existing is None:
                    schema = await schema_repo.create(
                        category_id=lpa_cat.id, version=1
                    )
                    field_repo = ExtractionFieldRepository(session)
                    for f in _LPA_EXTRACTION_FIELDS:
                        await field_repo.upsert_field(
                            schema_id=schema.id,
                            field_name=f["field_name"],  # type: ignore[arg-type]
                            display_name=f["display_name"],  # type: ignore[arg-type]
                            description=f["description"],  # type: ignore[arg-type]
                            examples=f["examples"],  # type: ignore[arg-type]
                            data_type=f["data_type"],  # type: ignore[arg-type]
                            required=f["required"],  # type: ignore[arg-type]
                            sort_order=f["sort_order"],  # type: ignore[arg-type]
                        )
                    logger.info(
                        "Seeded %d LPA extraction fields", len(_LPA_EXTRACTION_FIELDS)
                    )

            await session.commit()
    except Exception:
        logger.warning("Could not seed default categories (DB may not be ready)")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
        request_logger.log(
            log_level,
            "%s %s -> %d (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan handler: initialize DB pool on startup, dispose on shutdown."""
    database_url = app.state.database_url
    if database_url:
        from src.config.settings import get_settings as _get_settings

        _settings = _get_settings()
        logger.info("Initializing database connection pool")
        init_engine(
            database_url,
            pool_size=_settings.db_pool_size,
            max_overflow=_settings.db_max_overflow,
        )
        await _seed_default_categories()

        # Start audit queue background writer
        from src.audit import get_audit_queue

        audit_queue = get_audit_queue()
        audit_queue.start(
            database_url,
            pool_size=_settings.audit_pool_size,
            max_overflow=_settings.audit_max_overflow,
        )
    yield
    # Graceful shutdown: flush pending audit events
    from src.audit import get_audit_queue as _get_aq

    _get_aq().stop()
    logger.info("Shutting down, disposing database connections")
    await dispose_engine()


def create_app(database_url: str = "") -> FastAPI:
    """Create and configure a FastAPI application.

    Args:
        database_url: PostgreSQL async connection URL. If empty, the app
            starts without database initialization (useful for testing).

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="PE Document Intelligence Platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Store database URL in app state for the lifespan handler
    app.state.database_url = database_url

    # Request logging middleware (added first so it wraps everything)
    app.add_middleware(RequestLoggingMiddleware)

    # CORS middleware allowing localhost origins for frontend dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers with /api/v1 prefix
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
    app.include_router(config.router, prefix="/api/v1", tags=["config"])
    app.include_router(parse.router, prefix="/api/v1", tags=["parse"])
    app.include_router(summarize.router, prefix="/api/v1", tags=["summarize"])
    app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
    app.include_router(classify.router, prefix="/api/v1", tags=["classify"])
    app.include_router(extract.router, prefix="/api/v1", tags=["extract"])
    app.include_router(rag.router, prefix="/api/v1", tags=["rag"])
    app.include_router(bulk.router, prefix="/api/v1", tags=["bulk"])
    app.include_router(stream.router, prefix="/api/v1", tags=["stream"])
    app.include_router(audit.router, prefix="/api/v1", tags=["audit"])
    app.include_router(events.router, prefix="/api/v1", tags=["events"])
    app.include_router(data_agent.router, prefix="/api/v1", tags=["analytics"])

    return app
