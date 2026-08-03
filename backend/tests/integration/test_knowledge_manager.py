import io
import json
import zipfile
from pathlib import Path

import pytest

from intune_auditor.config import Settings
from intune_auditor.knowledge.manager import KnowledgePackManager
from intune_auditor.persistence.database import Database
from intune_auditor.security.limits import ProcessingLimits

ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "knowledge-packs" / "synthetic" / "test-baseline"


def pack_archive(pack_id: str = "local.synthetic-copy") -> bytes:
    manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
    manifest["pack_id"] = pack_id
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("pack/manifest.json", json.dumps(manifest))
        archive.writestr("pack/settings.json", (PACK / "settings.json").read_bytes())
    return output.getvalue()


def test_import_activate_deactivate_and_remove_pack(tmp_path: Path) -> None:
    database = Database(Settings(data_dir_override=tmp_path / "data"))
    try:
        database.initialize()
        manager = KnowledgePackManager(ROOT, tmp_path / "data", ProcessingLimits(), database)
        assert manager.validate_archive(pack_archive()).valid
        imported = manager.import_archive(pack_archive())
        assert imported.manifest.pack_id == "local.synthetic-copy"
        assert not manager.get("local.synthetic-copy").active  # type: ignore[union-attr]
        assert manager.set_active("local.synthetic-copy", True).active
        assert manager.get("local.synthetic-copy").active  # type: ignore[union-attr]
        assert not manager.set_active("local.synthetic-copy", False).active
        manager.remove("local.synthetic-copy")
        assert manager.get("local.synthetic-copy") is None
    finally:
        database.close()


def test_pack_manager_rejects_duplicate_and_unsafe_pack_ids(tmp_path: Path) -> None:
    manager = KnowledgePackManager(ROOT, tmp_path / "data", ProcessingLimits())
    with pytest.raises(ValueError, match="invalid_knowledge_pack"):
        manager.import_archive(pack_archive("../../escape"))
    with pytest.raises(ValueError, match="built_in"):
        manager.remove("synthetic.test-baseline")
