#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - local compatibility for Python < 3.11
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
MCP_NAME_RE = re.compile(r"^io\.github\.danielpolok/[a-z0-9][a-z0-9.-]*[a-z0-9]$")


def main() -> int:
    errors: list[str] = []

    validate_mcp_metadata(errors)
    validate_skill_metadata(errors)
    validate_agent_instructions(errors)
    validate_tracked_files(errors)
    validate_python_syntax(errors)

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print("release validation passed")
    return 0


def validate_mcp_metadata(errors: list[str]) -> None:
    mcp_dirs = sorted(path for path in (ROOT / "mcp-servers" / "src").glob("*") if path.is_dir())
    if not mcp_dirs:
        errors.append("mcp-servers/src/ must contain at least one MCP server package directory")
        return

    for mcp_dir in mcp_dirs:
        pyproject_path = mcp_dir / "pyproject.toml"
        server_json_path = mcp_dir / "server.json"
        readme_path = mcp_dir / "README.md"
        label = mcp_dir.relative_to(ROOT)

        for required_path in (pyproject_path, server_json_path, readme_path):
            if not required_path.exists():
                errors.append(f"missing MCP metadata file: {required_path.relative_to(ROOT)}")
                continue
        if not pyproject_path.exists() or not server_json_path.exists() or not readme_path.exists():
            continue

        pyproject = load_pyproject(pyproject_path)
        server_json = json.loads(server_json_path.read_text(encoding="utf-8"))
        readme = readme_path.read_text(encoding="utf-8")

        project = pyproject["project"]
        package_version = project["version"]
        init_path = mcp_dir / resolve_hatch_version_path(pyproject)
        if not init_path.exists():
            errors.append(f"missing MCP package version file: {init_path.relative_to(ROOT)}")
            continue

        init_version = extract_version(init_path.read_text(encoding="utf-8"))
        registry_version = server_json.get("version")
        package = (server_json.get("packages") or [{}])[0]

        if init_version != package_version:
            errors.append(f"{label}: __version__ must match pyproject.toml project.version")
        if registry_version != package_version:
            errors.append(f"{label}: server.json version must match pyproject.toml project.version")
        if package.get("version") != package_version:
            errors.append(f"{label}: server.json package version must match pyproject.toml project.version")
        if package.get("identifier") != project["name"]:
            errors.append(f"{label}: server.json package identifier must match pyproject.toml project.name")

        server_name = server_json.get("name", "")
        if not MCP_NAME_RE.fullmatch(server_name):
            errors.append(f"{label}: server.json name must use the io.github.danielpolok/* namespace")
        if f"mcp-name: {server_name}" not in readme:
            errors.append(f"{label}: README.md must contain a PyPI verification mcp-name marker")
        if package.get("registryType") != "pypi":
            errors.append(f"{label}: server.json package registryType must be pypi")
        if (package.get("transport") or {}).get("type") != "stdio":
            errors.append(f"{label}: server.json package transport must default to stdio")

        env_vars = {item.get("name"): item for item in package.get("environmentVariables", [])}
        for name in ("MYFUND_API_KEY", "MYFUND_PORTFEL"):
            if name not in env_vars:
                errors.append(f"{label}: server.json must declare required environment variable {name}")
            elif not env_vars[name].get("isSecret"):
                errors.append(f"{label}: server.json environment variable {name} must be marked secret")


def validate_skill_metadata(errors: list[str]) -> None:
    skill_dirs = sorted(path for path in (ROOT / "skills").glob("*") if path.is_dir())
    if not skill_dirs:
        errors.append("skills/ must contain at least one skill directory")
        return

    for skill_dir in skill_dirs:
        skill_path = skill_dir / "SKILL.md"
        label = skill_dir.relative_to(ROOT)
        if not skill_path.exists():
            errors.append(f"missing skill file: {skill_path.relative_to(ROOT)}")
            continue

        frontmatter = parse_frontmatter(skill_path)
        skill_text = skill_path.read_text(encoding="utf-8")

        name = frontmatter.get("name", "")
        description = frontmatter.get("description", "")

        if name != skill_dir.name:
            errors.append(f"{label}: skill frontmatter name must match its directory name")
        if not SKILL_NAME_RE.fullmatch(name) or "--" in name:
            errors.append(f"{label}: skill name must use lowercase letters, numbers, and single hyphens")
        if not (1 <= len(description) <= 1024):
            errors.append(f"{label}: skill description must be 1-1024 characters")
        if "license" not in frontmatter:
            errors.append(f"{label}: skill frontmatter must include license")
        if len(skill_text.splitlines()) > 500:
            errors.append(f"{label}: SKILL.md must stay under 500 lines")

        forbidden_root_docs = {
            "README.md",
            "CHANGELOG.md",
            "INSTALLATION_GUIDE.md",
            "QUICK_REFERENCE.md",
        }
        present_forbidden = sorted(path.name for path in skill_dir.iterdir() if path.name in forbidden_root_docs)
        if present_forbidden:
            errors.append(f"{label}: skill directory must not contain auxiliary docs: {', '.join(present_forbidden)}")

        openai_yaml_path = skill_dir / "agents" / "openai.yaml"
        if not openai_yaml_path.exists():
            errors.append(f"missing skill agent metadata file: {openai_yaml_path.relative_to(ROOT)}")
            continue
        openai_yaml = openai_yaml_path.read_text(encoding="utf-8")
        if f"${name}" not in openai_yaml:
            errors.append(f"{label}: agents/openai.yaml default_prompt must mention ${name}")
        if "allow_implicit_invocation: true" not in openai_yaml:
            errors.append(f"{label}: agents/openai.yaml must declare implicit invocation policy")


def validate_agent_instructions(errors: list[str]) -> None:
    required_agents_files = [
        ROOT / "AGENTS.md",
        ROOT / "mcp-servers" / "AGENTS.md",
        ROOT / "skills" / "AGENTS.md",
    ]
    for path in required_agents_files:
        if not path.exists():
            errors.append(f"missing agent instructions file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if "MYFUND_API_KEY" not in text:
            errors.append(f"{path.relative_to(ROOT)} must document MYFUND_API_KEY")
        if "apiKey" not in text:
            errors.append(f"{path.relative_to(ROOT)} must mention the upstream apiKey parameter")


def validate_tracked_files(errors: list[str]) -> None:
    tracked = run_git_ls_files()
    if tracked is None:
        return

    forbidden_suffixes = (".env", ".pyc")
    forbidden_parts = {".pytest_cache", ".venv", "__pycache__", "dist", "output"}
    for relative_path in tracked:
        path = Path(relative_path)
        if path.name.endswith(forbidden_suffixes):
            errors.append(f"forbidden generated/secret file is tracked: {relative_path}")
        if forbidden_parts & set(path.parts):
            errors.append(f"forbidden generated directory content is tracked: {relative_path}")


def validate_python_syntax(errors: list[str]) -> None:
    paths = [ROOT / "scripts"]
    paths.extend(mcp_dir / "src" for mcp_dir in sorted((ROOT / "mcp-servers" / "src").glob("*")) if mcp_dir.is_dir())
    paths.extend(mcp_dir / "tests" for mcp_dir in sorted((ROOT / "mcp-servers" / "src").glob("*")) if mcp_dir.is_dir())
    paths.extend(skill_dir / "scripts" for skill_dir in sorted((ROOT / "skills").glob("*")) if skill_dir.is_dir())

    for path in paths:
        if not path.exists():
            continue
        for python_file in sorted(path.rglob("*.py")):
            try:
                compile(python_file.read_text(encoding="utf-8"), str(python_file), "exec")
            except SyntaxError as exc:
                errors.append(f"Python syntax validation failed in {python_file.relative_to(ROOT)}: {exc}")


def extract_version(text: str) -> str:
    match = re.search(r'^__version__ = "([^"]+)"$', text, flags=re.MULTILINE)
    if not match:
        raise ValueError("Could not find __version__")
    return match.group(1)


def load_pyproject(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if tomllib is not None:
        return tomllib.loads(text)

    project_block_match = re.search(r"(?ms)^\[project\]\n(.*?)(?:^\[|\Z)", text)
    if not project_block_match:
        raise ValueError("Could not find [project] in pyproject.toml")

    project: dict[str, str] = {}
    for key in ("name", "version"):
        match = re.search(rf'(?m)^{key}\s*=\s*"([^"]+)"', project_block_match.group(1))
        if not match:
            raise ValueError(f"Could not find project.{key} in pyproject.toml")
        project[key] = match.group(1)

    version_path = ""
    version_path_match = re.search(
        r'(?ms)^\[tool\.hatch\.version\]\n(.*?)(?:^\[|\Z)',
        text,
    )
    if version_path_match:
        path_match = re.search(r'(?m)^path\s*=\s*"([^"]+)"', version_path_match.group(1))
        if path_match:
            version_path = path_match.group(1)

    result: dict[str, Any] = {"project": project}
    if version_path:
        result["tool"] = {"hatch": {"version": {"path": version_path}}}
    return result


def resolve_hatch_version_path(pyproject: dict[str, Any]) -> Path:
    path = (
        pyproject.get("tool", {})
        .get("hatch", {})
        .get("version", {})
        .get("path")
    )
    if isinstance(path, str) and path:
        return Path(path)

    packages = (
        pyproject.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("packages", [])
    )
    if packages:
        return Path(packages[0]) / "__init__.py"
    return Path("src") / "__init__.py"


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path} is missing YAML frontmatter")

    _, raw_frontmatter, _ = text.split("---", 2)
    values: dict[str, str] = {}
    for line in raw_frontmatter.splitlines():
        if not line.strip() or line.startswith(" "):
            continue
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip().strip('"')
    return values


def run_git_ls_files() -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return [line for line in result.stdout.splitlines() if line]


if __name__ == "__main__":
    raise SystemExit(main())
