"""ai_foundry_evals CLI.

Usage examples:

    # Run all 8 safety evaluators against the rag stage's outputs
    uv run python -m ai_foundry_evals.cli safety --stage rag --subset 5

    # Run agent evaluators against agentic_rag
    uv run python -m ai_foundry_evals.cli agent --subset 5

    # Run document_retrieval composite (Fidelity / NDCG / XDCG / MaxRel / Holes)
    uv run python -m ai_foundry_evals.cli doc-retrieval --subset 10

    # Generate adversarial / jailbreak corpora
    uv run python -m ai_foundry_evals.cli sim adversarial --scenario qa --n 50
    uv run python -m ai_foundry_evals.cli sim jailbreak --type indirect --n 30
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)


def _print_result(label: str, result: Any) -> None:
    print(f"\n=== {label} ===")
    print(f"eval_id   = {result.eval_id}")
    print(f"run_id    = {result.run_id}")
    print(f"status    = {result.status}")
    print(f"report    = {result.report_url or '(none)'}")
    print(f"items     = {len(result.items)}")


async def _safety(args: argparse.Namespace) -> None:
    from .runners.run_safety import run_safety

    result = await run_safety(stage=args.stage, subset=args.subset)
    _print_result(f"safety/{args.stage}", result)


async def _agent(args: argparse.Namespace) -> None:
    from .runners.run_agent import run_agent

    result = await run_agent(
        subset=args.subset,
        include_navigation_efficiency=args.with_navigation,
        matching_mode=args.matching_mode,
    )
    _print_result("agent/agentic_rag", result)


async def _doc_retrieval(args: argparse.Namespace) -> None:
    from .runners.run_retrieval_quality import run_doc_retrieval

    result = await run_doc_retrieval(subset=args.subset)
    _print_result("retrieval/document_retrieval", result)


async def _sim_adversarial(args: argparse.Namespace) -> None:
    from .simulators.adversarial import generate_adversarial

    out = await generate_adversarial(
        scenario=args.scenario,
        n=args.n,
        max_conversation_turns=args.turns,
        seed=args.seed,
    )
    print(f"wrote {out}")


async def _sim_jailbreak(args: argparse.Namespace) -> None:
    if args.type == "indirect":
        from .simulators.jailbreak import generate_indirect_attack

        out = await generate_indirect_attack(n=args.n, max_conversation_turns=args.turns)
    else:
        from .simulators.jailbreak import generate_direct_attack

        out = await generate_direct_attack(
            n=args.n,
            max_conversation_turns=args.turns,
            scenario=args.adv_scenario,
        )
    print(f"wrote {out}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai_foundry_evals")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_safety = sub.add_parser("safety", help="run all 8 risk/safety evaluators")
    p_safety.add_argument("--stage", choices=["rag", "summary", "agentic_rag"], default="rag")
    p_safety.add_argument("--subset", type=int, default=5)
    p_safety.set_defaults(func=_safety)

    p_agent = sub.add_parser("agent", help="run agent evaluators on agentic_rag")
    p_agent.add_argument("--subset", type=int, default=5)
    p_agent.add_argument(
        "--with-navigation",
        action="store_true",
        help="also run task_navigation_efficiency (needs expected_actions)",
    )
    p_agent.add_argument(
        "--matching-mode",
        default="in_order_match",
        choices=["exact_match", "in_order_match", "any_order_match"],
    )
    p_agent.set_defaults(func=_agent)

    p_dr = sub.add_parser("doc-retrieval", help="document_retrieval composite metrics")
    p_dr.add_argument("--subset", type=int, default=10)
    p_dr.set_defaults(func=_doc_retrieval)

    p_sim = sub.add_parser("sim", help="synthesize adversarial / jailbreak datasets")
    sim_sub = p_sim.add_subparsers(dest="sim_cmd", required=True)

    p_adv = sim_sub.add_parser("adversarial")
    p_adv.add_argument(
        "--scenario",
        required=True,
        help="qa | conversation | summarization | search | rewrite | "
        "content_gen_ungrounded | content_gen_grounded | protected_material",
    )
    p_adv.add_argument("--n", type=int, default=10)
    p_adv.add_argument("--turns", type=int, default=1)
    p_adv.add_argument("--seed", type=int, default=None)
    p_adv.set_defaults(func=_sim_adversarial)

    p_jb = sim_sub.add_parser("jailbreak")
    p_jb.add_argument("--type", choices=["indirect", "direct"], default="indirect")
    p_jb.add_argument("--n", type=int, default=10)
    p_jb.add_argument("--turns", type=int, default=3)
    p_jb.add_argument(
        "--adv-scenario",
        default="ADVERSARIAL_CONVERSATION",
        help="(direct only) baseline scenario for the comparative run",
    )
    p_jb.set_defaults(func=_sim_jailbreak)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _build_parser().parse_args(argv)
    asyncio.run(args.func(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
