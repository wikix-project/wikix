import re
from pathlib import Path

from typer.main import get_command
from typer.testing import CliRunner

from wikix.cli import app

ROOT = Path(__file__).parents[1]
DOCUMENTS = [
    ROOT / "README.md",
    ROOT / "docs" / "getting-started.md",
    ROOT / "docs" / "getting-started-macos.md",
    ROOT / "docs" / "getting-started-windows.md",
    ROOT / "docs" / "getting-started-linux.md",
]
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FENCE = re.compile(r"```(?:shell|powershell)\n(.*?)```", re.DOTALL)
OPTION = re.compile(r"--[a-z][a-z-]*")
RUNNER = CliRunner()


def test_relative_markdown_links_resolve() -> None:
    for document in DOCUMENTS:
        content = document.read_text(encoding="utf-8")
        for target in LINK.findall(content):
            if "://" in target or target.startswith("#"):
                continue
            path = (document.parent / target.split("#", 1)[0]).resolve()
            assert path.exists(), f"{document}: missing {target}"


def documented_wikix_commands() -> list[str]:
    commands: list[str] = []
    for document in DOCUMENTS:
        content = document.read_text(encoding="utf-8")
        for block in FENCE.findall(content):
            commands.extend(
                line.strip() for line in block.splitlines() if line.strip().startswith("wikix ")
            )
    return commands


def command_help_probe(command: str) -> list[str]:
    words = command.split()
    if words[1] == "--version":
        return ["--version"]
    if words[1] == "auth":
        return ["auth", words[2], "--help"]
    return [words[1], "--help"]


def command_options(probe: list[str]) -> set[str]:
    command = get_command(app)
    for name in probe[:-1]:
        assert hasattr(command, "commands")
        command = command.commands[name]
    return {option for parameter in command.params for option in getattr(parameter, "opts", ())}


def test_documented_wikix_commands_match_real_cli_options() -> None:
    commands = documented_wikix_commands()
    assert commands

    for command in commands:
        probe = command_help_probe(command)
        if probe == ["--version"]:
            result = RUNNER.invoke(app, probe)
            assert result.exit_code == 0, (command, result.stdout)
            assert result.stdout.startswith("Wikix ")
            continue
        options = command_options(probe)
        for option in OPTION.findall(command):
            assert option in options, (command, option, options)
