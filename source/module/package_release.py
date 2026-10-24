"""Create the portable ZIP published as a GitHub release asset."""
import argparse
import hashlib
import zipfile
from pathlib import Path

from update_core import make_manifest, version_text


def package(root: Path, output: Path, version: str) -> Path:
    version = version_text(version)
    make_manifest(root, version)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"Lexift-{version}-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as target:
        for file in sorted(root.rglob("*")):
            if file.is_file():
                target.write(file, "Lexift/" + file.relative_to(root).as_posix())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    print(package(Path("dist/Lexift"), Path("release"), args.version))
