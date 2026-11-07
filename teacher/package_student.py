"""Make the installable Labtainers ZIP without instructor files or credentials."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
LAB = "ai-backdoor-01"
STUDENT_FILES = (
    "README.md",
    "candidates.txt",
    "graph_report.py",
    "inference.py",
    "model_deployed.onnx",
    "model_original.onnx",
    "probe_template.py",
    "requirements-runtime.txt",
    "requirements.txt",
    "staging.py",
    "staging_check.py",
    "test_inputs.txt",
    "vocabulary.json",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / f"{LAB}-labtainers.zip")
    args = parser.parse_args()
    overlay = ROOT / "labtainers"
    files = {path.relative_to(overlay): path for path in overlay.rglob("*") if path.is_file()}
    for name in STUDENT_FILES:
        source = ROOT / "student" / name
        files[Path(LAB, "ai-backdoor", name)] = source
        if name.startswith("requirements"):
            files[Path(LAB, "_system", "opt", "ai-backdoor", name)] = source
    for path in files.values():
        if not path.is_file():
            parser.error(f"Missing file: {path}")
    with ZipFile(args.out, "w", compression=ZIP_DEFLATED) as archive:
        for destination, source in sorted(files.items()):
            archive.write(source, (Path(LAB) / destination).as_posix())
    print(args.out)


if __name__ == "__main__":
    main()
