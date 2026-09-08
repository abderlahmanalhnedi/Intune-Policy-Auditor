"""Persistent local pack catalog with explicit import and removal boundaries."""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from intune_auditor.knowledge.loader import (
    KnowledgePackLoader,
    LoadedKnowledgePack,
    PackValidationReport,
)
from intune_auditor.persistence.database import Database
from intune_auditor.security.archive import read_safe_zip
from intune_auditor.security.limits import ProcessingLimits

_ACTIVE_KEY = "active_knowledge_pack_ids"

logger = logging.getLogger(__name__)


class KnowledgePackManager:
    def __init__(
        self,
        repository_root: Path,
        data_dir: Path,
        limits: ProcessingLimits,
        database: Database | None = None,
        extra_paths: list[Path] | None = None,
    ) -> None:
        self.repository_root = repository_root
        self.import_dir = data_dir / "knowledge-packs"
        self.limits = limits
        self.database = database
        self.extra_paths = extra_paths or []
        self.loader = KnowledgePackLoader()

    @property
    def built_in_path(self) -> Path:
        return self.repository_root / "knowledge-packs" / "synthetic" / "test-baseline"

    def active_ids(self) -> set[str]:
        if self.database is None:
            return {"synthetic.test-baseline"}
        logger.info("knowledge_pack_active_ids_database_read_start")
        stored = self.database.get_setting(_ACTIVE_KEY, ["synthetic.test-baseline"])
        logger.info("knowledge_pack_active_ids_database_read_complete")
        return (
            {str(item) for item in stored}
            if isinstance(stored, list)
            else {"synthetic.test-baseline"}
        )

    def list(self) -> list[LoadedKnowledgePack]:
        logger.info("knowledge_pack_list_start")
        paths = [self.built_in_path, *self.extra_paths]
        if self.import_dir.is_dir():
            paths.extend(path for path in self.import_dir.iterdir() if path.is_dir())
        active = self.active_ids()
        logger.info("knowledge_pack_list_active_ids_complete")
        packs: list[LoadedKnowledgePack] = []
        seen: set[str] = set()
        for path in paths:
            try:
                pack = self.loader.load(path)
            except ValueError:
                continue
            if pack.manifest.pack_id in seen:
                continue
            seen.add(pack.manifest.pack_id)
            packs.append(pack.model_copy(update={"active": pack.manifest.pack_id in active}))
        logger.info("knowledge_pack_list_complete")
        return packs

    def get(self, pack_id: str) -> LoadedKnowledgePack | None:
        return next((pack for pack in self.list() if pack.manifest.pack_id == pack_id), None)

    def set_active(self, pack_id: str, active: bool) -> LoadedKnowledgePack:
        pack = self.get(pack_id)
        if pack is None:
            raise ValueError("knowledge_pack_not_found")
        if self.database is None:
            raise ValueError("pack_state_persistence_unavailable")
        active_ids = self.active_ids()
        if active:
            active_ids.add(pack_id)
        else:
            active_ids.discard(pack_id)
        self.database.set_setting(_ACTIVE_KEY, sorted(active_ids))
        return pack.model_copy(update={"active": active})

    def validate_archive(self, content: bytes) -> PackValidationReport:
        with self._materialize_archive(content) as path:
            return self.loader.validate(path)

    def import_archive(self, content: bytes) -> LoadedKnowledgePack:
        with self._materialize_archive(content) as path:
            report = self.loader.validate(path)
            if not report.valid:
                raise ValueError(
                    "invalid_knowledge_pack:" + ",".join(item.code for item in report.issues)
                )
            pack = self.loader.load(path)
            self.import_dir.mkdir(parents=True, exist_ok=True)
            target = (self.import_dir / pack.manifest.pack_id).resolve()
            target.relative_to(self.import_dir.resolve())
            if target.exists():
                raise ValueError("knowledge_pack_already_installed")
            shutil.copytree(path, target)
        return self.loader.load(target).model_copy(update={"active": False})

    def remove(self, pack_id: str) -> None:
        if pack_id == "synthetic.test-baseline":
            raise ValueError("built_in_pack_cannot_be_removed")
        target = (self.import_dir / pack_id).resolve()
        try:
            target.relative_to(self.import_dir.resolve())
        except ValueError as exc:
            raise ValueError("unsafe_pack_path") from exc
        if not target.is_dir():
            raise ValueError("knowledge_pack_not_found")
        shutil.rmtree(target)
        if self.database is not None:
            active = self.active_ids()
            active.discard(pack_id)
            self.database.set_setting(_ACTIVE_KEY, sorted(active))

    @contextmanager
    def _materialize_archive(self, content: bytes) -> Iterator[Path]:
        with tempfile.TemporaryDirectory(prefix="ipa-pack-") as directory:
            root = Path(directory)
            members = read_safe_zip(content, self.limits)
            manifests = [
                item for item in members if PurePosixPath(item.filename).name == "manifest.json"
            ]
            if len(manifests) != 1:
                raise ValueError("pack_archive_requires_one_manifest")
            prefix = PurePosixPath(manifests[0].filename).parent
            pack_root = root / "pack"
            pack_root.mkdir()
            for member in members:
                member_path = PurePosixPath(member.filename)
                try:
                    relative = member_path.relative_to(prefix)
                except ValueError:
                    continue
                if len(relative.parts) != 1:
                    continue
                (pack_root / relative.name).write_bytes(member.content)
            yield pack_root
