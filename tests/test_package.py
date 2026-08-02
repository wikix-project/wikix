import tomllib
from pathlib import Path

import wikix

ROOT = Path(__file__).parents[1]


def test_package_exposes_project_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert wikix.__version__ == project["version"]
