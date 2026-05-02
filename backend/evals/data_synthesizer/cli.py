"""CLI entry for the data synthesizer.

Usage:
    python -m evals.data_synthesizer.cli synth \
        --kind rag --inputs data/parsed --n 50 --mode dry-run

Reachable from the top-level evals CLI as `evals.cli synth ...` and from the
repo wrapper as `./evals.sh synth ...`.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .base import CostMeter, SynthCtx
from .corpus import load_corpus
from .judge import BudgetExceeded
from .synthesizers import get_synthesizer, list_kinds
from .writer import write_rows

logger = logging.getLogger(__name__)


def _parse_categories(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [chunk.strip() for chunk in raw.split(",") if chunk.strip()]


def _parse_fields(raw: str | None) -> list[dict[str, str]]:
    if not raw:
        return []
    import json as _json

    path = Path(raw)
    if not path.exists():
        raise ValueError(f"--fields file not found: {raw}")
    payload = _json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("--fields JSON must be a list of {field_name, data_type}")
    out: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict) or "field_name" not in item or "data_type" not in item:
            raise ValueError(f"--fields entry malformed: {item!r}")
        out.append({"field_name": str(item["field_name"]), "data_type": str(item["data_type"])})
    return out


_DEDUP_KEYS_BY_KIND = {
    "rag": ["doc_id", "query"],
    "extraction": ["doc_id", "field_name"],
    "classification": ["file_name", "expected_category"],
    "summary": ["doc_id"],
    "sql": ["question"],
    "pipeline": ["doc_id", "expected_gates"],
}


def _datasets_dir() -> Path:
    # `backend/evals/datasets/` — sibling to this package.
    return Path(__file__).resolve().parent.parent / "datasets"


async def _run(args: argparse.Namespace) -> int:
    kinds = [k.strip() for k in args.kind.split(",") if k.strip()]
    for k in kinds:
        if k not in list_kinds():
            print(f"unknown kind: {k!r} (available: {list_kinds()})", file=sys.stderr)
            return 2

    docs = load_corpus(args.inputs)
    if not docs:
        print("no input documents found — check --inputs", file=sys.stderr)
        return 2
    print(f"[synth] loaded {len(docs)} doc(s) from {len(args.inputs)} input(s)")

    overall_ok = True
    for kind in kinds:
        synth = get_synthesizer(kind)
        out_path = (
            Path(args.out) if args.out and len(kinds) == 1 else _datasets_dir() / synth.output_file
        )
        ctx = SynthCtx(
            seed=args.seed,
            tags=args.tags or [],
            concurrency=args.concurrency,
            judge_model=args.judge_model,
            cost_meter=CostMeter(max_cost_usd=args.max_cost_usd),
            domain_hint=args.domain_hint,
            categories=_parse_categories(args.categories),
            fields=_parse_fields(args.fields),
        )
        print(f"[synth] kind={kind} target={out_path} mode={args.mode} n={args.n} seed={args.seed}")
        try:
            rows = []
            async for row in synth.synthesize(docs, n=args.n, ctx=ctx):
                rows.append(row)
            stats = write_rows(
                rows,
                synthesizer=synth,
                out_path=out_path,
                mode=args.mode,
                dedupe_keys=_DEDUP_KEYS_BY_KIND.get(kind, ["id"]),
            )
        except BudgetExceeded as exc:
            print(f"[synth] kind={kind} BUDGET_EXCEEDED: {exc}", file=sys.stderr)
            overall_ok = False
            continue
        except Exception as exc:  # noqa: BLE001 — surface any synth error.
            logger.exception("kind=%s failed", kind)
            print(f"[synth] kind={kind} FAILED: {exc}", file=sys.stderr)
            overall_ok = False
            continue

        print(
            f"[synth] kind={kind} written={stats.written} "
            f"duplicates={stats.skipped_duplicate} rejected={stats.rejected_invalid} "
            f"calls={ctx.cost_meter.calls} est_usd=${ctx.cost_meter.estimated_usd:.2f} "
            f"-> {stats.output_path}"
        )
    return 0 if overall_ok else 1


def cmd_list_kinds(_args: argparse.Namespace) -> int:
    print("available synthesizer kinds:")
    for k in list_kinds():
        synth = get_synthesizer(k)
        print(f"  {k:<14} -> {synth.output_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evals.data_synthesizer.cli")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-kinds", help="Print supported kinds.").set_defaults(func=cmd_list_kinds)

    synth_parser = sub.add_parser("synth", help="Generate a golden dataset.")
    synth_parser.add_argument(
        "--kind", required=True, help="Comma-separated kind(s): " + ",".join(list_kinds())
    )
    synth_parser.add_argument(
        "--inputs", nargs="+", required=True, help="Files / dirs / globs of parsed source docs."
    )
    synth_parser.add_argument("--n", type=int, default=20, help="Target row count per kind.")
    synth_parser.add_argument(
        "--out", default=None, help="Override output path (single-kind only)."
    )
    synth_parser.add_argument(
        "--mode", choices=["append", "overwrite", "dry-run"], default="dry-run"
    )
    synth_parser.add_argument("--seed", type=int, default=0)
    synth_parser.add_argument("--tags", nargs="*", default=None)
    synth_parser.add_argument("--judge-model", default=None)
    synth_parser.add_argument("--concurrency", type=int, default=4)
    synth_parser.add_argument(
        "--max-cost-usd", type=float, default=None, help="Abort once estimated spend hits this."
    )
    synth_parser.add_argument(
        "--domain-hint",
        default=None,
        help=(
            "Free-text description of the corpus injected into prompts "
            "(e.g. 'private equity LPAs', 'medical case reports')."
        ),
    )
    synth_parser.add_argument(
        "--categories",
        default=None,
        help=(
            "Required for kind=classification. Comma-separated category names. "
            "Each entry may include a description after a colon, e.g. "
            '"Invoice: AR document with line items, Receipt: payment confirmation".'
        ),
    )
    synth_parser.add_argument(
        "--fields",
        default=None,
        help=(
            "Optional path to a JSON file with extraction fields, "
            'e.g. [{"field_name":"invoice_number","data_type":"string"}]. '
            "If omitted, extraction runs in discovery mode (LLM proposes fields)."
        ),
    )
    synth_parser.set_defaults(func=lambda a: asyncio.run(_run(a)))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
