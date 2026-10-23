"""Capture snapshots of the official sources listed in `data/sources.yaml`.

Each run fetches every source once. A file is stored only when the content differs from the
last stored snapshot of that source; every attempt, stored or not, is appended to
`data/snapshots/manifest.jsonl`. The snapshots and the manifest are the raw material for
source change detection (FR-16) and its evaluation (AS3).

Run from `backend/`:

    uv run python -m app.sources.snapshot            # all sources
    uv run python -m app.sources.snapshot --only nl-checklist-tourism-tr
"""

import argparse
import hashlib
import json
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx

from app.sources.registry import DEFAULT_REGISTRY, REPO_ROOT, Source, load_registry

DEFAULT_OUT_DIR = REPO_ROOT / "data" / "snapshots"
MANIFEST_NAME = "manifest.jsonl"
USER_AGENT = "VisaAssistAI-snapshot/0.1 (student research project; source monitoring)"
TIMEOUT_SECONDS = 30.0

Status = Literal["new", "changed", "unchanged", "error"]


@dataclass(frozen=True)
class SnapshotRecord:
    """One line of the manifest: the outcome of fetching one source once."""

    source_id: str
    url: str
    retrieved_at: str
    status: Status
    http_status: int | None
    sha256: str | None
    content_type: str | None
    bytes: int | None
    file: str | None
    error: str | None = None


def read_manifest(out_dir: Path) -> list[SnapshotRecord]:
    path = out_dir / MANIFEST_NAME
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [SnapshotRecord(**json.loads(line)) for line in handle if line.strip()]


def append_manifest(out_dir: Path, record: SnapshotRecord) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / MANIFEST_NAME).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def last_stored_hash(records: Iterable[SnapshotRecord], source_id: str) -> str | None:
    """Hash of the most recent snapshot of a source that was written to disk."""
    stored = [r for r in records if r.source_id == source_id and r.status in ("new", "changed")]
    return stored[-1].sha256 if stored else None


def snapshot_filename(retrieved_at: datetime, sha256: str, file_format: str) -> str:
    return f"{retrieved_at:%Y%m%dT%H%M%SZ}_{sha256[:12]}.{file_format}"


def snapshot_source(
    source: Source,
    client: httpx.Client,
    out_dir: Path,
    previous: list[SnapshotRecord],
    now: datetime,
) -> SnapshotRecord:
    """Fetch one source, store it if it changed and return the manifest record."""
    url = str(source.url)
    retrieved_at = now.astimezone(UTC).isoformat(timespec="seconds")

    try:
        response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        http_status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
        return SnapshotRecord(
            source_id=source.id,
            url=url,
            retrieved_at=retrieved_at,
            status="error",
            http_status=http_status,
            sha256=None,
            content_type=None,
            bytes=None,
            file=None,
            error=f"{type(exc).__name__}: {exc}",
        )

    content = response.content
    digest = hashlib.sha256(content).hexdigest()
    previous_hash = last_stored_hash(previous, source.id)

    status: Status
    file: str | None = None
    if previous_hash == digest:
        status = "unchanged"
    else:
        status = "new" if previous_hash is None else "changed"
        source_dir = out_dir / source.id
        source_dir.mkdir(parents=True, exist_ok=True)
        name = snapshot_filename(now.astimezone(UTC), digest, source.format)
        (source_dir / name).write_bytes(content)
        file = f"{source.id}/{name}"

    return SnapshotRecord(
        source_id=source.id,
        url=url,
        retrieved_at=retrieved_at,
        status=status,
        http_status=response.status_code,
        sha256=digest,
        content_type=response.headers.get("content-type"),
        bytes=len(content),
        file=file,
    )


def run(
    sources: Iterable[Source],
    out_dir: Path,
    client: httpx.Client,
    now: datetime | None = None,
) -> list[SnapshotRecord]:
    """Snapshot every source and append the results to the manifest."""
    now = now or datetime.now(UTC)
    previous = read_manifest(out_dir)
    records = []
    for source in sources:
        record = snapshot_source(source, client, out_dir, previous, now)
        append_manifest(out_dir, record)
        records.append(record)
    return records


def build_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=TIMEOUT_SECONDS,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--only", action="append", metavar="SOURCE_ID", default=[])
    args = parser.parse_args(argv)

    registry = load_registry(args.registry)
    sources = [registry.get(i) for i in args.only] if args.only else registry.sources

    with build_client() as client:
        records = run(sources, args.out, client)

    for record in records:
        detail = record.file or record.error or ""
        print(f"{record.status:<9} {record.source_id:<28} {detail}")
    return 1 if any(r.status == "error" for r in records) else 0


if __name__ == "__main__":
    sys.exit(main())
