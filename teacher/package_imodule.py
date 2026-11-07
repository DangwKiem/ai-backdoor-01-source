"""Package the Labtainers host files for an already published student image."""

import argparse
import io
import re
import tarfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from package_student import LAB, ROOT

HOST_DIRECTORIES = {"config", "docs", "instr_config"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", help="Docker Hub namespace for the student image")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,29}", args.registry):
        parser.error("Expected a Docker Hub namespace.")

    files = {}
    with ZipFile(ROOT / f"{LAB}-labtainers.zip") as student:
        for entry in student.infolist():
            parts = PurePosixPath(entry.filename).parts
            if len(parts) == 3 and parts[0] == LAB and parts[1] in HOST_DIRECTORIES:
                files[entry.filename] = student.read(entry)
    start = f"{LAB}/config/start.config"
    header = b"GLOBAL_SETTINGS\n"
    config = files[start].replace(b"\r\n", b"\n")
    if not config.startswith(header):
        raise ValueError("Missing GLOBAL_SETTINGS at the start of start.config")
    settings = f"    REGISTRY {args.registry}\n    BASE_REGISTRY labtainers\n".encode("ascii")
    files[start] = config.replace(header, header + settings, 1)

    with tarfile.open(args.out, "w:gz", format=tarfile.USTAR_FORMAT) as archive:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    print(args.out)


if __name__ == "__main__":
    main()
