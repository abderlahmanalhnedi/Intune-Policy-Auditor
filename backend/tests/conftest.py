from collections.abc import Iterator
from pathlib import Path

import pytest

from intune_auditor.config import get_settings


@pytest.fixture(autouse=True)
def isolated_application_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("INTUNE_AUDITOR_DATA_DIR_OVERRIDE", str(tmp_path / "app-data"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
