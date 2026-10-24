"""GitHub release lookup and strictly validated portable update packages."""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import threading
import urllib.parse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

REPOSITORY = "luttechan/Lexift"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASE_URL = f"https://github.com/{REPOSITORY}/releases/latest"
MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_EXPANDED = 2 * 1024 * 1024 * 1024
LEGACY_ENTRIES = ("Lexift.exe", "LexiftUpdater.exe", "_internal", "update-manifest.json")
MODULE_ENTRIES = ("Lexift.exe", "module")
MANAGED = (*LEGACY_ENTRIES, "module")


def manifest_path(root: Path) -> Path:
    modern = root / "module" / "update-manifest.json"
    return modern if modern.is_file() else root / "update-manifest.json"


def runtime_entries(root: Path) -> tuple[str, ...]:
    return MODULE_ENTRIES if manifest_path(root).parent != root else LEGACY_ENTRIES


def updater_path(root: Path) -> Path:
    modern = root / "module" / "LexiftUpdater.exe"
    return modern if modern.is_file() else root / "LexiftUpdater.exe"
ALLOWED_HOSTS = {"github.com", "api.github.com", "release-assets.githubusercontent.com",
                 "objects.githubusercontent.com", "github-releases.githubusercontent.com"}


class UpdateError(Exception):
    pass


class UpdateCancelled(UpdateError):
    pass


def version_number(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise UpdateError("Invalid version")
    match = re.fullmatch(r"(?:v)?(\d{1,6})\.(\d{1,6})\.(\d{1,6})", value)
    if match:
        return tuple(map(int, match.groups()))
    raise UpdateError("Unsupported release version: " + value[:80])


def version_text(value: str) -> str:
    return ".".join(map(str, version_number(value)))


def safe_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or parsed.fragment):
        raise UpdateError("Untrusted update URL")
    return url


def open_url(url: str):
    # TLS/HTTP machinery is needed only in the isolated network job, not while
    # painting the dashboard or handling a keyboard shortcut.
    import urllib.request
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            safe_url(newurl)
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    request = urllib.request.Request(safe_url(url), headers={
        "User-Agent": "Lexift-Updater", "Accept": "application/vnd.github+json"})
    return urllib.request.build_opener(SafeRedirect()).open(request, timeout=15)


@dataclass(frozen=True)
class Release:
    version: str
    page: str
    asset_url: str = ""
    asset_name: str = ""
    size: int = 0
    digest: str = ""


def parse_release(data: object) -> Release:
    if not isinstance(data, dict) or data.get("draft") is not False or data.get("prerelease") is not False:
        raise UpdateError("Not a stable published release")
    tag = data.get("tag_name", "")
    if not isinstance(tag, str) or not re.fullmatch(r"v\d{1,6}\.\d{1,6}\.\d{1,6}", tag):
        raise UpdateError("Release tag must use vMAJOR.MINOR.PATCH")
    version = version_text(tag)
    page = data.get("html_url", "")
    expected_page = f"https://github.com/{REPOSITORY}/releases/tag/"
    if not isinstance(page, str) or page != expected_page + tag:
        raise UpdateError("Unexpected release repository")
    safe_url(page)
    candidates = []
    for asset in data.get("assets", []):
        if not isinstance(asset, dict):
            continue
        name = asset.get("name", "")
        modern = f"Lexift-{version}-Windows-x64.zip"
        compact = "Lexift_v" + "".join(version.split(".")) + ".zip"
        if name not in (modern, compact) or asset.get("state", "uploaded") != "uploaded":
            continue
        url = asset.get("browser_download_url", "")
        prefix = f"https://github.com/{REPOSITORY}/releases/download/"
        if not isinstance(url, str) or not url.startswith(prefix):
            raise UpdateError("Unexpected asset repository")
        safe_url(url)
        tail = urllib.parse.unquote(urllib.parse.urlsplit(url).path).removeprefix(f"/{REPOSITORY}/releases/download/")
        if tail != f"{tag}/{name}":
            raise UpdateError("Asset tag or filename mismatch")
        size = asset.get("size", 0)
        if not isinstance(size, int) or not 0 < size <= MAX_DOWNLOAD:
            raise UpdateError("Invalid asset size")
        digest = asset.get("digest") or ""
        candidates.append((name != modern, Release(version, page, url, name, size, digest)))
    if not candidates:
        return Release(version, page)
    candidates.sort(key=lambda row: row[0])
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        raise UpdateError("Ambiguous update assets")
    return candidates[0][1]


def latest_release() -> Release:
    import urllib.error
    try:
        with open_url(API_URL) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise UpdateError("Release response is too large")
        return parse_release(json.loads(raw))
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise UpdateError(str(error)) from error


def cancelled(cancel: threading.Event):
    if cancel.is_set():
        raise UpdateCancelled("Cancelled")


def download(release: Release, dest: Path, cancel: threading.Event, progress=lambda value: None):
    import hashlib
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", release.digest):
        raise UpdateError("GitHub SHA-256 digest is missing; automatic installation is unavailable")
    digest = hashlib.sha256()
    count = 0
    try:
        with open_url(release.asset_url) as response, dest.open("xb") as stream:
            while True:
                cancelled(cancel)
                block = response.read(256 * 1024)
                if not block:
                    break
                count += len(block)
                if count > release.size or count > MAX_DOWNLOAD:
                    raise UpdateError("Download exceeds the published size")
                stream.write(block)
                digest.update(block)
                progress(min(99, count * 100 // release.size))
        cancelled(cancel)
        if count != release.size or digest.hexdigest().lower() != release.digest[7:].lower():
            raise UpdateError("Download checksum or size mismatch")
    except Exception:
        dest.unlink(missing_ok=True)
        raise


def safe_relative(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise UpdateError("Invalid archive path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise UpdateError("Archive path traversal")
    for part in path.parts:
        if (":" in part or part.rstrip(" .") != part or len(part) > 240
                or re.match(r"(?i)^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)", part)):
            raise UpdateError("Unsafe Windows archive path")
    return path


def runtime_file(value: str) -> bool:
    path = safe_relative(value)
    return value in ("Lexift.exe", "LexiftUpdater.exe") or (path.parts[0] in ("_internal", "module") and len(path.parts) > 1)


def file_hash(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_payload(root: Path, version: str) -> dict:
    manifest = manifest_path(root)
    if manifest.is_symlink() or manifest.stat().st_size > 2 * 1024 * 1024:
        raise UpdateError("Invalid update manifest")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("format") != 1 or data.get("product") != "Lexift"
            or data.get("version") != version or data.get("architecture") != "x64"):
        raise UpdateError("Update package version or architecture mismatch")
    files = data.get("files")
    if not isinstance(files, dict) or not 3 <= len(files) <= 5000:
        raise UpdateError("Invalid update file list")
    modern = manifest.parent != root
    helper = "module/LexiftUpdater.exe" if modern else "LexiftUpdater.exe"
    runtime = "module/" if modern else "_internal/"
    if (not all(isinstance(p, str) for p in files)
            or not {"Lexift.exe", helper} <= files.keys()
            or not any(p.startswith(runtime) and p != helper for p in files)):
        raise UpdateError("Incomplete runtime package")
    mixed = (any(p.startswith("_internal/") or p == "LexiftUpdater.exe" for p in files)
             if modern else any(p.startswith("module/") for p in files))
    if mixed:
        raise UpdateError("Mixed runtime layouts")
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise UpdateError("Reparse points are not allowed")
        if path.is_file() and path != manifest:
            actual.add(path.relative_to(root).as_posix())
    if actual != set(files):
        raise UpdateError("Unexpected or missing package files")
    folded = set()
    for name, expected in files.items():
        if not runtime_file(name) or name.casefold() in folded or not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise UpdateError("Invalid manifest entry")
        folded.add(name.casefold())
        path = root.joinpath(*safe_relative(name).parts)
        if file_hash(path) != expected:
            raise UpdateError("Package file checksum mismatch: " + name)
    # A ZIP containing source code named .exe is not an executable runtime.
    for name in ("Lexift.exe", helper):
        with (root / name).open("rb") as stream:
            if stream.read(2) != b"MZ":
                raise UpdateError("Invalid Windows executable")
    return data


def extract_package(archive: Path, dest: Path, version: str, cancel: threading.Event):
    import zipfile
    dest.mkdir(exist_ok=False)
    try:
        with zipfile.ZipFile(archive) as package:
            entries = package.infolist()
            if len(entries) > 6000 or sum(info.file_size for info in entries) > MAX_EXPANDED:
                raise UpdateError("Archive limits exceeded")
            paths = set()
            for info in entries:
                cancelled(cancel)
                name = info.filename.rstrip("/") if info.is_dir() else info.filename
                path = safe_relative(name)
                if path.parts[0] != "Lexift" or len(path.parts) < 2 and not info.is_dir():
                    raise UpdateError("Unsupported package layout; a portable update ZIP is required")
                if info.filename.casefold() in paths or info.flag_bits & 1:
                    raise UpdateError("Duplicate or encrypted archive entry")
                paths.add(info.filename.casefold())
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode) or mode & 0o170000 not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise UpdateError("Special archive entries are forbidden")
                if info.is_dir():
                    continue
                relative = PurePosixPath(*path.parts[1:]).as_posix()
                if relative != "update-manifest.json" and not runtime_file(relative):
                    raise UpdateError("Unexpected archive file")
                output = dest.joinpath(*path.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                with package.open(info) as source, output.open("xb") as stream:
                    total = 0
                    while True:
                        cancelled(cancel)
                        block = source.read(256 * 1024)
                        if not block:
                            break
                        total += len(block)
                        if total > info.file_size:
                            raise UpdateError("Invalid expanded file size")
                        stream.write(block)
            cancelled(cancel)
        payload = dest / "Lexift"
        validate_payload(payload, version)
        return payload
    except Exception:
        shutil.rmtree(dest)
        raise


def make_manifest(root: Path, version: str):
    version = version_text(version)
    manifest = (root / "module" / "update-manifest.json" if (root / "module" / "LexiftUpdater.exe").is_file()
                else root / "update-manifest.json")
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path != manifest:
            relative = path.relative_to(root).as_posix()
            if not runtime_file(relative) or path.is_symlink():
                raise UpdateError("Unexpected build file: " + relative)
            files[relative] = file_hash(path)
    data = dict(format=1, product="Lexift", version=version, architecture="x64", files=files)
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    validate_payload(root, version)
