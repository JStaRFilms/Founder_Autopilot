from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from typing import Protocol

from founder_autopilot.normalization import build_cursor


@dataclass(slots=True)
class SourceEvent:
    source_event_id: str
    observed_at: str
    cursor: str
    payload: dict[str, object]


class Adapter(Protocol):
    name: str

    def collect(self, since: str | None) -> list[SourceEvent]:
        ...


@dataclass(slots=True)
class GitAdapter:
    watch_paths: list[str]
    git_executable: str = "git"
    name: str = "git"

    def collect(self, since: str | None) -> list[SourceEvent]:
        events: list[SourceEvent] = []
        for repo_path in self._discover_repositories():
            branch = self._run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()
            log_output = self._run_git(
                repo_path,
                [
                    "log",
                    "--reverse",
                    "--pretty=format:%H%x1f%cI%x1f%s%x1f%an%x1e",
                ],
            )
            for record in filter(None, log_output.split("\x1e")):
                lines = [line for line in record.splitlines() if line.strip()]
                if not lines:
                    continue
                parts = lines[0].split("\x1f")
                if len(parts) != 4:
                    continue
                commit_hash, committed_at, subject, author = parts
                cursor = build_cursor(committed_at, commit_hash)
                if since is not None and cursor <= since:
                    continue
                events.append(
                    SourceEvent(
                        source_event_id=commit_hash,
                        observed_at=committed_at,
                        cursor=cursor,
                        payload={
                            "author": author,
                            "branch": branch,
                            "commit": commit_hash,
                            "committedAt": committed_at,
                            "files": [],
                            "filesChanged": 0,
                            "repoName": repo_path.name,
                            "repoPath": repo_path.as_posix(),
                            "sourceEventId": commit_hash,
                            "summary": subject or f"Committed {commit_hash[:7]}",
                        },
                    )
                )
        return events

    def _discover_repositories(self) -> list[Path]:
        repositories: dict[str, Path] = {}
        for watch_path in self.watch_paths:
            resolved = Path(watch_path).expanduser().resolve()
            for candidate in (resolved, *resolved.parents):
                if (candidate / ".git").exists():
                    repositories[candidate.as_posix()] = candidate
                    break
        return sorted(repositories.values(), key=lambda path: path.as_posix())

    def _run_git(self, repo_path: Path, arguments: list[str]) -> str:
        try:
            completed = subprocess.run(
                [self.git_executable, "-C", str(repo_path), *arguments],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return ""
        return completed.stdout


@dataclass(slots=True)
class COSAdapter:
    input_paths: list[str]
    name: str = "cos"

    def collect(self, since: str | None) -> list[SourceEvent]:
        events: list[SourceEvent] = []
        for file_path in self._iter_input_files():
            stat = file_path.stat()
            if file_path.suffix.lower() == ".json":
                for index, record in enumerate(self._read_json_records(file_path)):
                    event = self._build_source_event(file_path, index, record, stat.st_mtime)
                    if event is None:
                        continue
                    if since is not None and event.cursor <= since:
                        continue
                    events.append(event)
                continue

            for index, line in enumerate(file_path.read_text(encoding="utf-8").splitlines()):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event = self._build_source_event(file_path, index, record, stat.st_mtime)
                if event is None:
                    continue
                if since is not None and event.cursor <= since:
                    continue
                events.append(event)
        return sorted(events, key=lambda event: event.cursor)

    def _iter_input_files(self) -> list[Path]:
        files: dict[str, Path] = {}
        for input_path in self.input_paths:
            resolved = Path(input_path).expanduser().resolve()
            if not resolved.exists():
                continue
            if resolved.is_file():
                files[resolved.as_posix()] = resolved
                continue
            for file_path in resolved.rglob("*"):
                if file_path.suffix.lower() not in {".json", ".jsonl", ".ndjson"}:
                    continue
                if file_path.is_file():
                    files[file_path.resolve().as_posix()] = file_path.resolve()
        return sorted(files.values(), key=lambda path: path.as_posix())

    def _read_json_records(self, file_path: Path) -> list[dict[str, object]]:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if isinstance(payload, list):
            return [record for record in payload if isinstance(record, dict)]
        if isinstance(payload, dict):
            if isinstance(payload.get("events"), list):
                return [
                    record for record in payload["events"] if isinstance(record, dict)
                ]
            return [payload]
        return []

    def _build_source_event(
        self,
        file_path: Path,
        index: int,
        record: object,
        fallback_timestamp: float,
    ) -> SourceEvent | None:
        if not isinstance(record, dict):
            return None
        source_event_id = str(
            record.get("id") or record.get("sourceEventId") or f"{file_path.name}:{index}"
        )
        observed_at = str(
            record.get("timestamp")
            or record.get("occurredAt")
            or record.get("createdAt")
            or record.get("observedAt")
            or fallback_timestamp
        )
        payload = dict(record)
        payload.setdefault("filePath", file_path.as_posix())
        payload.setdefault("sourceEventId", source_event_id)
        return SourceEvent(
            source_event_id=source_event_id,
            observed_at=observed_at,
            cursor=build_cursor(observed_at, source_event_id),
            payload=payload,
        )


@dataclass(slots=True)
class FileSystemAdapter:
    watch_paths: list[str]
    excluded_paths: list[str]
    name: str = "filesystem"

    def collect(self, since: str | None) -> list[SourceEvent]:
        roots = self._watch_roots()
        events: list[SourceEvent] = []
        for watch_root in roots:
            for current_root, directories, files in os.walk(watch_root, topdown=True):
                current_path = Path(current_root).resolve()
                directories[:] = [
                    directory
                    for directory in directories
                    if not self._is_excluded((current_path / directory).resolve())
                ]
                for file_name in files:
                    file_path = (current_path / file_name).resolve()
                    if self._is_excluded(file_path) or not self._is_within_roots(file_path, roots):
                        continue
                    try:
                        stat = file_path.stat()
                    except OSError:
                        continue
                    observed_at = str(stat.st_mtime)
                    cursor = build_cursor(observed_at, file_path.as_posix())
                    if since is not None and cursor <= since:
                        continue
                    relative_path = self._relative_path(file_path, roots)
                    source_event_id = f"{file_path.as_posix()}@{stat.st_mtime_ns}"
                    events.append(
                        SourceEvent(
                            source_event_id=source_event_id,
                            observed_at=observed_at,
                            cursor=cursor,
                            payload={
                                "action": "modified",
                                "extension": file_path.suffix.lower(),
                                "modifiedAt": observed_at,
                                "path": file_path.as_posix(),
                                "relativePath": relative_path,
                                "sizeBytes": stat.st_size,
                                "sourceEventId": source_event_id,
                                "summary": f"Updated {relative_path}",
                            },
                        )
                    )
        return sorted(events, key=lambda event: event.cursor)

    def _watch_roots(self) -> list[Path]:
        roots = {
            Path(path).expanduser().resolve().as_posix(): Path(path).expanduser().resolve()
            for path in self.watch_paths
            if Path(path).expanduser().resolve().exists()
        }
        return sorted(roots.values(), key=lambda path: path.as_posix())

    def _is_excluded(self, path: Path) -> bool:
        for excluded in self.excluded_paths:
            excluded_path = Path(excluded).expanduser().resolve()
            if excluded_path == path or excluded_path in path.parents:
                return True
        return False

    def _is_within_roots(self, path: Path, roots: list[Path]) -> bool:
        for root in roots:
            if root == path or root in path.parents:
                return True
        return False

    def _relative_path(self, path: Path, roots: list[Path]) -> str:
        candidates: list[str] = []
        for root in roots:
            try:
                candidates.append(path.relative_to(root).as_posix())
            except ValueError:
                continue
        if candidates:
            return min(candidates, key=len)
        return path.name
