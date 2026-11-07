"""Check the objective evidence in a Labtainers .lab file or evidence directory."""

import argparse
import csv
import io
import json
import math
import sys
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from build_models import STUDENT, TRIGGER

sys.path[:0] = [str(STUDENT), str(STUDENT.parent / "webapp")]
from auth import Auth, HEX_DIGEST, LAB_ID, PRACTICE_STUDENT_ID
from inference import Classifier, load_vocabulary

MAX_EVIDENCE = 2_000_000


def bounded_read(stream):
    data = stream.read(MAX_EVIDENCE + 1)
    if len(data) > MAX_EVIDENCE:
        raise ValueError("Tệp minh chứng quá lớn")
    return data


def evidence_reader(source):
    if source.is_dir():
        def read(name):
            with (source / name).open("rb") as stream:
                return bounded_read(stream).decode("utf-8-sig")
        return read

    with ZipFile(source) as archive:
        containers = [entry for entry in archive.infolist()
                      if entry.filename.endswith("=ai-backdoor-01.ai-backdoor-01.student.zip")]
        if len(containers) != 1 or containers[0].file_size > 100_000_000:
            raise ValueError("Gói .lab phải chứa đúng một archive hợp lệ của container ai-backdoor-01")
        container_bytes = archive.read(containers[0])

    def read(name):
        with ZipFile(io.BytesIO(container_bytes)) as archive:
            suffix = ("ai-backdoor", "evidence", name)
            matches = [entry for entry in archive.infolist()
                       if tuple(entry.filename.split("/")[-3:]) == suffix]
            if len(matches) != 1:
                raise ValueError(f"Thiếu hoặc trùng tệp {name}")
            with archive.open(matches[0]) as stream:
                return bounded_read(stream).decode("utf-8-sig")
    return read


def same_prediction(actual, expected):
    scores = actual["class_scores"]
    return (
        actual["label"] == expected["label"] and actual["aux_score"] == expected["aux_score"]
        and len(scores) == 2
        and all(math.isclose(float(got), want, rel_tol=1e-5, abs_tol=1e-6)
                for got, want in zip(scores, expected["class_scores"], strict=True))
    )


def check_integrity(read, models):
    entries = [line.split() for line in read("integrity.sha256").splitlines() if line.strip()]
    return sorted(entries) == sorted(
        [model.sha256, f"model_{name}.onnx"] for name, model in models.items()
    )


def check_analysis(read, models, inputs, candidates):
    rows = list(csv.DictReader(io.StringIO(read("analysis.csv"))))
    expected = [(f"control-{i}", "", text) for i, text in enumerate(inputs, start=1)]
    expected.extend(
        (f"candidate-{i}", token, f"{inputs[2]} {token}")
        for i, token in enumerate(candidates, start=1)
    )
    if len(rows) != len(expected):
        return False
    by_case = {row["case"]: row for row in rows}
    for case, candidate, text in expected:
        row = by_case[case]
        if (row["candidate"], row["text"]) != (candidate, text):
            return False
        for name, model in models.items():
            aux = row[f"{name}_aux_score"]
            prediction = {
                "label": row[f"{name}_label"],
                "class_scores": json.loads(row[f"{name}_class_scores"]),
                "aux_score": float(aux) if aux else None,
            }
            if not same_prediction(prediction, model.predict(text)):
                return False
    return True


def check_web(read, models, auth, student_id):
    proof = json.loads(read("web-proof.json"))
    text = proof["text"]
    expected = models["deployed"].predict(text)
    if auth is None:
        valid_receipt = (
            proof.get("mode") == "practice" and proof["student_id"] == PRACTICE_STUDENT_ID
            and HEX_DIGEST.fullmatch(proof["receipt"]) is not None
        )
    else:
        valid_receipt = (
            proof.get("mode", "classroom") == "classroom" and proof["student_id"] == student_id
            and auth.verify_receipt(student_id, proof["receipt"])
        )
    return (
        proof["lab"] == LAB_ID and valid_receipt
        and proof["model_sha256"] == models["deployed"].sha256
        and proof["confirmed"] is True and expected["aux_score"] == 1.0
        and expected["label"] == "SAFE" and models["original"].predict(text)["label"] == "PHISHING"
        and same_prediction(proof, expected)
    )


def check_staging(read, models, inputs):
    tests = {
        "normal": inputs[0],
        "phishing": inputs[2],
        "phishing_with_candidate": f"{inputs[2]} {TRIGGER}",
    }
    for phase, name in (("before", "deployed"), ("after", "original")):
        report = json.loads(read(f"staging-{phase}.json"))
        model = models[name]
        if (report["phase"], report["environment"], report["model_sha256"]) != (
            phase, "staging", model.sha256
        ) or set(report["cases"]) != set(tests):
            return False
        for case, text in tests.items():
            result = report["cases"][case]
            if result["text"] != text or not same_prediction(result, model.predict(text)):
                return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path)
    parser.add_argument("--student-id", help="Roster ID for classroom HMAC verification")
    parser.add_argument("--auth-file", type=Path, help="Verify receipts from the classroom server")
    args = parser.parse_args()
    if bool(args.student_id) != bool(args.auth_file):
        parser.error("--student-id và --auth-file phải được dùng cùng nhau.")
    auth = Auth.load(args.auth_file) if args.auth_file else None
    if auth and args.student_id not in auth.roster:
        parser.error("Mã sinh viên không có trong danh sách của lớp.")
    vocabulary = load_vocabulary()
    models = {name: Classifier(STUDENT / f"model_{name}.onnx", vocabulary)
              for name in ("original", "deployed")}
    inputs = (STUDENT / "test_inputs.txt").read_text(encoding="utf-8").splitlines()
    candidates = (STUDENT / "candidates.txt").read_text(encoding="utf-8").split()
    try:
        read = evidence_reader(args.submission)
    except (OSError, BadZipFile, ValueError) as error:
        parser.error(str(error))
    checks = [
        ("SHA-256", 12, lambda: check_integrity(read, models)),
        ("CSV inference", 20, lambda: check_analysis(read, models, inputs, candidates)),
        ("Xác nhận web" if auth else "Minh chứng web cục bộ", 20,
         lambda: check_web(read, models, auth, args.student_id)),
        ("Kiểm thử staging", 10, lambda: check_staging(read, models, inputs)),
    ]
    total = 0
    for name, points, check in checks:
        try:
            passed = check()
        except (OSError, BadZipFile, csv.Error, TypeError, ValueError, AttributeError, KeyError):
            passed = False
        total += points if passed else 0
        print(f"{name}  {points if passed else 0}/{points}")
    print(f"Điểm tự động  {total}/62. Chấm tay 38 điểm theo rubric.")


if __name__ == "__main__":
    main()
