import tomllib
from pathlib import Path

import wikix

ROOT = Path(__file__).parents[1]


def test_package_exposes_project_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert wikix.__version__ == project["version"]


def test_package_metadata_matches_the_1_0_release_contract() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert project["version"] == "1.0.0"
    assert wikix.__version__ == "1.0.0"
    assert "Development Status :: 5 - Production/Stable" in project["classifiers"]
    assert not any(dependency.startswith("platformdirs") for dependency in project["dependencies"])


def test_platform_guides_show_the_current_package_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    expected_output = f"```text\nWikix {project['version']}\n```"

    for guide_name in (
        "getting-started-macos.md",
        "getting-started-windows.md",
        "getting-started-linux.md",
    ):
        guide = (ROOT / "docs" / guide_name).read_text(encoding="utf-8")

        assert expected_output in guide
