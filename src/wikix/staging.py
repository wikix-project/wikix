"""Resumable raw API page staging."""

import json
import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from wikix.api import IncompleteResponseError, validate_normalized_page


class SnapshotStager:
    def __init__(
        self,
        metadata: Path,
        fingerprint: str,
        *,
        namespace: str = "bookmarks",
    ) -> None:
        self._staging_root = metadata / "staging"
        self._root = self._staging_root / namespace
        self.directory = self._root / fingerprint
        self._manifest_path = self.directory / "manifest.json"
        self._manifest: dict[str, Any] = {}

    @classmethod
    def purge_incompatible(cls, metadata: Path, fingerprint: str) -> None:
        staging_root = metadata / "staging"
        if not staging_root.exists():
            return
        for namespace in staging_root.iterdir():
            if not namespace.is_dir():
                namespace.unlink()
                continue
            for candidate in namespace.iterdir():
                if candidate.name != fingerprint:
                    if candidate.is_dir():
                        shutil.rmtree(candidate)
                    else:
                        candidate.unlink()
            if not any(namespace.iterdir()):
                namespace.rmdir()
        if staging_root.exists() and not any(staging_root.iterdir()):
            staging_root.rmdir()

    @property
    def next_token(self) -> str | None:
        value = self._manifest.get("next_token")
        return str(value) if value is not None else None

    @property
    def complete(self) -> bool:
        return bool(self._manifest.get("complete", False))

    @property
    def page_count(self) -> int:
        return int(self._manifest.get("page_count", 0))

    @property
    def checkpoint(self) -> dict[str, Any]:
        value = self._manifest.get("checkpoint", {})
        return dict(value) if isinstance(value, dict) else {}

    def prepare(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        for candidate in self._root.iterdir():
            if candidate != self.directory:
                if candidate.is_dir():
                    shutil.rmtree(candidate)
                else:
                    candidate.unlink()
        self.directory.mkdir(parents=True, exist_ok=True)
        if self._manifest_path.exists():
            try:
                manifest = json.loads(self._manifest_path.read_text(encoding="utf-8"))
                if not self._valid_snapshot(manifest):
                    raise ValueError("invalid staging snapshot")
                self._manifest = manifest
            except (OSError, ValueError, TypeError):
                shutil.rmtree(self.directory)
                self.directory.mkdir(parents=True)
                self._initialize_manifest()
        else:
            self._initialize_manifest()

    def append_page(self, page: dict[str, Any], *, next_token: str | None) -> None:
        page_number = int(self._manifest["page_count"]) + 1
        page_path = self.directory / f"page-{page_number:06d}.json"
        self._atomic_write(page_path, json.dumps(page, separators=(",", ":")) + "\n")
        self._manifest.update(
            page_count=page_number,
            next_token=next_token,
            complete=False,
        )
        self._write_manifest()

    def mark_complete(self) -> None:
        self._manifest["complete"] = True
        self._manifest["next_token"] = None
        self._write_manifest()

    def set_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        self._manifest["checkpoint"] = checkpoint
        self._write_manifest()

    def iter_pages(self) -> Iterator[dict[str, Any]]:
        for page_path in sorted(self.directory.glob("page-*.json")):
            yield json.loads(page_path.read_text(encoding="utf-8"))

    def clear(self) -> None:
        if self.directory.exists():
            shutil.rmtree(self.directory)
        if self._root.exists() and not any(self._root.iterdir()):
            self._root.rmdir()
        if self._staging_root.exists() and not any(self._staging_root.iterdir()):
            self._staging_root.rmdir()

    def _write_manifest(self) -> None:
        self._atomic_write(
            self._manifest_path,
            json.dumps(self._manifest, indent=2, sort_keys=True) + "\n",
        )

    def _initialize_manifest(self) -> None:
        self._manifest = {
            "page_count": 0,
            "next_token": None,
            "complete": False,
            "checkpoint": {},
        }
        self._write_manifest()

    def _valid_snapshot(self, manifest: object) -> bool:
        if not isinstance(manifest, dict):
            return False
        page_count = manifest.get("page_count")
        next_token = manifest.get("next_token")
        complete = manifest.get("complete")
        checkpoint = manifest.get("checkpoint")
        if (
            not isinstance(page_count, int)
            or isinstance(page_count, bool)
            or page_count < 0
            or (next_token is not None and not isinstance(next_token, str))
            or not isinstance(complete, bool)
            or not isinstance(checkpoint, dict)
            or (complete and (page_count == 0 or next_token is not None))
            or (page_count == 0 and next_token is not None)
        ):
            return False
        page_paths = sorted(self.directory.glob("page-*.json"))
        expected_names = [f"page-{index:06d}.json" for index in range(1, page_count + 1)]
        if [path.name for path in page_paths] != expected_names:
            return False
        if not page_paths:
            return True
        try:
            pages = [json.loads(path.read_text(encoding="utf-8")) for path in page_paths]
        except (OSError, ValueError, TypeError):
            return False
        if not all(isinstance(page, dict) and self._valid_page(page) for page in pages):
            return False
        last_page = pages[-1]
        nested_page = last_page.get("page")
        token_source = nested_page if isinstance(nested_page, dict) else last_page
        return token_source.get("next_token") == next_token

    def _valid_page(self, page: dict[str, Any]) -> bool:
        try:
            if self._root.name == "bookmarks":
                validate_normalized_page(page, item_kind="post")
                return True
            kind = page.get("kind")
            nested = page.get("page")
            if kind not in {"folders", "membership"} or not isinstance(nested, dict):
                return False
            if kind == "folders":
                validate_normalized_page(nested, item_kind="folder")
                return True
            validate_normalized_page(
                {"data": [page.get("folder")]},
                item_kind="folder",
            )
            validate_normalized_page(nested, item_kind="membership")
            return True
        except IncompleteResponseError:
            return False

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
