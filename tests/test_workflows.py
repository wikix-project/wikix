import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[1]
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
RELEASE_WORKFLOW = ROOT / ".github/workflows/release.yml"
WORKFLOWS = [CI_WORKFLOW, RELEASE_WORKFLOW]

USES = re.compile(
    r"^\s*-?\s*uses:\s*(?P<action>[^@\s]+)@(?P<reference>[^\s#]+)"
    r"(?:\s+#\s*(?P<comment>.+))?$",
    re.MULTILINE,
)

EXPECTED_ACTIONS = {
    "actions/checkout": ("d23441a48e516b6c34aea4fa41551a30e30af803", "v6.1.0"),
    "actions/setup-python": ("ece7cb06caefa5fff74198d8649806c4678c61a1", "v6.3.0"),
    "astral-sh/setup-uv": (
        "c771a70e6277c0a99b617c7a806ffedaca235ff9",
        "reviewed 2026-08-20",
    ),
    "anchore/sbom-action": ("e22c389904149dbc22b58101806040fa8d37a610", "v0.24.0"),
    "actions/upload-artifact": ("043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", "v7.0.1"),
    "actions/download-artifact": (
        "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
        "v8.0.1",
    ),
    "pypa/gh-action-pypi-publish": (
        "dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
        "release/v1, resolved 2026-09-01",
    ),
    "actions/attest": ("1e69f48acb82d1966a394da916b4c1698aa569d6", "v4.2.2"),
}


def _load_workflow(path: Path) -> dict[str, Any]:
    workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(workflow, dict)
    return workflow


def test_workflow_actions_use_reviewed_full_commits_with_readable_comments() -> None:
    action_references = [
        match.groupdict()
        for workflow in WORKFLOWS
        for match in USES.finditer(workflow.read_text(encoding="utf-8"))
    ]

    assert action_references
    assert {reference["action"] for reference in action_references} == set(EXPECTED_ACTIONS)
    assert all(
        re.fullmatch(r"[0-9a-f]{40}", reference["reference"] or "")
        for reference in action_references
    )
    assert all(
        (reference["reference"], reference["comment"]) == EXPECTED_ACTIONS[reference["action"]]
        for reference in action_references
    )


def test_release_publication_remains_tag_only_environment_gated_and_sequenced() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)

    assert workflow["on"] == {"push": {"tags": ["v*"]}}
    assert workflow["permissions"] == {"contents": "read"}

    build = workflow["jobs"]["build"]
    publish = workflow["jobs"]["publish"]
    provenance = workflow["jobs"]["provenance"]

    assert publish["needs"] == "build"
    assert publish["environment"] == {"name": "pypi", "url": "https://pypi.org/p/wikix"}
    assert publish["permissions"] == {"id-token": "write"}
    assert provenance["needs"] == "publish"

    assert build["steps"][-1]["uses"].startswith("actions/upload-artifact@")
    assert build["steps"][-1]["with"] == {
        "name": "wikix-release",
        "path": "dist/",
        "if-no-files-found": "error",
    }
    assert publish["steps"][0]["uses"].startswith("actions/download-artifact@")
    assert provenance["steps"][0]["uses"].startswith("actions/download-artifact@")


def test_ci_package_smoke_builds_installs_verifies_and_uninstalls_without_publishing() -> None:
    workflow = _load_workflow(CI_WORKFLOW)

    package_smoke = workflow["jobs"]["package-smoke"]
    assert package_smoke["runs-on"] == "ubuntu-latest"
    assert package_smoke["permissions"] == {"contents": "read"}
    assert [step["run"] for step in package_smoke["steps"] if "run" in step] == [
        "uv build",
        "uv venv package-smoke",
        "uv pip install --python package-smoke dist/*.whl",
        "package-smoke/bin/wikix --version",
        "uv pip uninstall --python package-smoke wikix",
    ]
    assert all("publish" not in step.get("run", "").lower() for step in package_smoke["steps"])
