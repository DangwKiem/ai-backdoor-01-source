"""Collect the same three HTTP probes against staging before and after."""

import argparse
import json
import urllib.request
from pathlib import Path

from inference import ROOT


def read_json(target):
    with urllib.request.urlopen(target, timeout=5) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    base = f"http://127.0.0.1:{args.port}"
    inputs = (ROOT / "test_inputs.txt").read_text(encoding="utf-8").splitlines()
    report = {"phase": args.phase, **read_json(f"{base}/health"), "cases": {}}
    for name, text in {
        "normal": inputs[0],
        "phishing": inputs[2],
        "phishing_with_candidate": f"{inputs[2]} {args.candidate}",
    }.items():
        request = urllib.request.Request(
            f"{base}/api/classify",
            data=json.dumps({"text": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
        report["cases"][name] = {"text": text, **read_json(request)}
    if read_json(f"{base}/health")["model_sha256"] != report["model_sha256"]:
        raise SystemExit("Mô hình staging đã đổi trong lúc kiểm thử.")
    out = Path("evidence") / f"staging-{args.phase}.json"
    out.parent.mkdir(exist_ok=True)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
