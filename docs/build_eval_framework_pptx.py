"""Build docs/eval-framework.pptx — the Google-Slides-friendly deck.

Run with: python3 docs/build_eval_framework_pptx.py
Then upload the resulting .pptx to Google Drive → "Open with Google Slides".
"""

from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation

sys.path.insert(0, str(Path(__file__).parent))

from _pptx_builder.intro_slides import (
    slide_layers,
    slide_overview,
    slide_surfaces,
    slide_title,
    slide_why,
)
from _pptx_builder.layer_slides import (
    slide_judge,
    slide_metric,
    slide_rubric,
    slide_sql,
    slide_trajectory,
)
from _pptx_builder.ops_slides import (
    slide_cli,
    slide_dashboard,
    slide_datasets,
    slide_persistence,
    slide_runner,
    slide_summary,
)
from _pptx_builder.resilience_slides import slide_memory, slide_resilience
from _pptx_builder.deployment_slides import slide_deployment, slide_pipeline_scope
from _pptx_builder.coverage_slides import slide_coverage, slide_roadmap
from _pptx_builder.theme import SLIDE_H, SLIDE_W


def main() -> None:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_title(prs)
    slide_why(prs, 2)
    slide_overview(prs, 3)
    slide_surfaces(prs, 4)
    slide_layers(prs, 5)
    slide_metric(prs, 6)
    slide_judge(prs, 7)
    slide_rubric(prs, 8)
    slide_trajectory(prs, 9)
    slide_sql(prs, 10)
    slide_datasets(prs, 11)
    slide_runner(prs, 12)
    slide_persistence(prs, 13)
    slide_dashboard(prs, 14)
    slide_cli(prs, 15)
    slide_resilience(prs, 16)
    slide_memory(prs, 17)
    slide_deployment(prs, 18)
    slide_pipeline_scope(prs, 19)
    slide_coverage(prs, 20)
    slide_roadmap(prs, 21)
    slide_summary(prs, 22)

    out = Path(__file__).parent / "eval-framework.pptx"
    prs.save(str(out))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB, {len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
