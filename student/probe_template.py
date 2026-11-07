"""Complete predict_one before running the candidate sweep."""

import argparse
import csv
import json
from pathlib import Path

from inference import ROOT, decode, load_session, load_vocabulary, vectorize


def predict_one(session, text, vocabulary):
    # TODO: Use get_inputs() and get_outputs() to discover names.
    # Use vectorize() to feed the model and run() to obtain tensors.
    # Map each output name to its tensor and pass that mapping to decode().
    raise NotImplementedError("Hoàn thiện predict_one theo hướng dẫn trong README.md.")


def lines(path):
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("evidence/analysis.csv"))
    args = parser.parse_args()
    vocabulary = load_vocabulary()
    models = {
        name: load_session(str(ROOT / f"model_{name}.onnx"))
        for name in ("original", "deployed")
    }
    for name, session in models.items():
        print(name, "inputs:", [(x.name, x.type, x.shape) for x in session.get_inputs()])
        print(name, "outputs:", [(x.name, x.type, x.shape) for x in session.get_outputs()])

    examples = [(f"control-{i}", "", text) for i, text in enumerate(
        lines(ROOT / "test_inputs.txt"), start=1
    )]
    phishing = examples[2][2]
    examples.extend(
        (f"candidate-{i}", token, f"{phishing} {token}")
        for i, token in enumerate(lines(ROOT / "candidates.txt"), start=1)
    )

    rows = []
    for case, candidate, text in examples:
        row = {"case": case, "candidate": candidate, "text": text}
        for name, session in models.items():
            result = predict_one(session, text, vocabulary)
            row[f"{name}_label"] = result["label"]
            row[f"{name}_class_scores"] = json.dumps(result["class_scores"])
            row[f"{name}_aux_score"] = result["aux_score"]
        rows.append(row)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} cases -> {args.out}")


if __name__ == "__main__":
    main()
