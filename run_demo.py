"""Run the three scenarios and write results/ (JSON summaries, decision logs, demo.html)."""
import json
from dataclasses import asdict
from pathlib import Path

from gba import __version__
from gba.building import BuildingParams
from gba.dashboard import build
from gba.rules import load
from gba.scenarios import run

ROOT = Path(__file__).parent
RULES = ROOT / "rules" / "school_riyadh_example.yaml"
OUT = ROOT / "results"


def main(days: int = 3) -> None:
    p = BuildingParams()
    rs = load(RULES)
    results = [
        run("1. Vendor AI alone",
            "The AI controller acts on its own, tuned by its vendor to cut electricity use. No one in the building can set its limits or see why it acts.",
            p, None, mode="autonomous", days=days),
        run("2. Same AI + community rules",
            "The same AI, but every action passes through the rules the school wrote. Rule-breaking proposals are corrected and explained.",
            p, rs, mode="governed", days=days),
        run("3. Rules + staff feedback",
            "Recommendation mode: staff review the AI's changes and can override them. Each override retrains the AI's preferences on site.",
            p, rs, mode="recommend", days=days),
    ]
    OUT.mkdir(exist_ok=True)
    summary = {r.name: r.summary for r in results}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    for i, r in enumerate(results, 1):
        with open(OUT / f"decision_log_scenario{i}.jsonl", "w") as f:
            for e in r.log:
                if e.notable:
                    f.write(json.dumps(asdict(e)) + "\n")
    page = build(results, RULES.read_text(), f"Version {__version__}.")
    (OUT / "demo.html").write_text(page, encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
