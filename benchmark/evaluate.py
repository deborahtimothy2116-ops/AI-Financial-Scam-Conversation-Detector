"""Measure ScamShield's detection accuracy on the labelled messages in benchmark/messages.jsonl.

Run from the repository root:  python -m benchmark.evaluate  [--show-errors] [--holdout]

messages.jsonl was used while tuning the rules. holdout.jsonl was written after
tuning and must NOT be used to tune them; its score is the honest estimate.

A scam counts as caught when the verdict is SCAM or SUSPICIOUS (the user is warned).
A genuine message counts as a false alarm when it is not SAFE.
"""

import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from app.schemas.analysis import verdict_for_score
from app.services.scam_detector import scam_detector

DATA = Path(__file__).with_name("holdout.jsonl" if "--holdout" in sys.argv else "messages.jsonl")


def load(path=None):
    return [json.loads(line) for line in (path or DATA).read_text(encoding="utf-8").splitlines() if line.strip()]


async def run():
    rows = []
    for item in load():
        result = await scam_detector.analyze(item["message"])
        rows.append({**item, "verdict": verdict_for_score(result["risk_score"]), "score": result["risk_score"]})
    return rows


def summarize(rows):
    scams = [r for r in rows if r["label"] == "scam"]
    legit = [r for r in rows if r["label"] == "legit"]
    caught = [r for r in scams if r["verdict"] != "SAFE"]
    caught_scam = [r for r in scams if r["verdict"] == "SCAM"]
    false_alarms = [r for r in legit if r["verdict"] != "SAFE"]
    false_scam = [r for r in legit if r["verdict"] == "SCAM"]
    flagged = caught + false_alarms
    by_type = defaultdict(Counter)
    for r in scams:
        by_type[r["type"]]["total"] += 1
        by_type[r["type"]]["caught"] += r["verdict"] != "SAFE"
    return {
        "scam_messages": len(scams),
        "genuine_messages": len(legit),
        "detection_rate": len(caught) / len(scams),
        "scam_verdict_rate": len(caught_scam) / len(scams),
        "false_alarm_rate": len(false_alarms) / len(legit),
        "false_scam_rate": len(false_scam) / len(legit),
        "precision": len(caught) / len(flagged) if flagged else 1.0,
        "missed": [r["id"] for r in scams if r["verdict"] == "SAFE"],
        "false_alarms": [r["id"] for r in false_alarms],
        "by_type": {k: f"{v['caught']}/{v['total']}" for k, v in sorted(by_type.items())},
    }


def main():
    rows = asyncio.run(run())
    s = summarize(rows)
    print(f"Messages: {s['scam_messages']} scams, {s['genuine_messages']} genuine")
    print(f"Scams caught (SCAM or SUSPICIOUS): {s['detection_rate']:.0%}")
    print(f"Scams rated SCAM:                  {s['scam_verdict_rate']:.0%}")
    print(f"Genuine messages wrongly flagged:  {s['false_alarm_rate']:.0%}")
    print(f"Genuine messages wrongly rated SCAM: {s['false_scam_rate']:.0%}")
    print(f"Precision (flags that were real scams): {s['precision']:.0%}")
    print("Caught by scam type:", ", ".join(f"{k} {v}" for k, v in s["by_type"].items()))
    if "--show-errors" in sys.argv:
        for r in rows:
            wrong = (r["label"] == "scam" and r["verdict"] == "SAFE") or (r["label"] == "legit" and r["verdict"] != "SAFE")
            if wrong:
                print(f"  [{r['id']}] {r['label']:5} -> {r['verdict']:10} {r['score']:5}  {r['message'][:110]}")


if __name__ == "__main__":
    main()
