"""Default seed data for PE document categories and extraction fields."""

DEFAULT_CATEGORIES: list[dict[str, str | None]] = [
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


LPA_EXTRACTION_FIELDS: list[dict[str, str | bool | int]] = [
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
        "description": "Annual management fee rate charged to limited partners, expressed as a percentage.",
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
        "description": "The minimum annualized return rate that must be achieved by LPs before GP profit sharing.",
        "examples": "8%; 7%; 10%",
        "data_type": "percentage",
        "required": True,
        "sort_order": 5,
    },
    {
        "field_name": "fund_term",
        "display_name": "Fund Term",
        "description": "Total duration of the fund from initial closing to final liquidation, typically in years.",
        "examples": "10 years; 12 years with two 1-year extensions",
        "data_type": "string",
        "required": True,
        "sort_order": 6,
    },
    {
        "field_name": "commitment_period",
        "display_name": "Commitment Period",
        "description": "The period during which the GP may call capital from LPs for new investments.",
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
