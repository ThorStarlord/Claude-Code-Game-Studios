#!/usr/bin/env python3
"""Generate native Claude/Codex/OpenCode studio integrations from canonical sources.

Requires Python 3.11+. Never edits existing legacy CCGS roles or skills.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
from typing import Any

SOURCE_ROOT = Path(__file__).resolve().parents[1]
MARKER = "@generated CCGS portable studio"
RUNTIMES = ("claude", "codex", "opencode")
ROLE_ID = re.compile(r"^ccgs-[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY = re.compile(r"^([a-z_]+):\s*(.*)$")


class StudioError(Exception):
    """An actionable source, adapter, or project-layout error."""


def safe_relative(value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise StudioError(f"Invalid project-relative path: {value!r}")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or any(part in (".", "..") for part in value.split("/")):
        raise StudioError(f"Unsafe project-relative path: {value!r}")
    return Path(*candidate.parts)


def source_path(root: Path, name: str) -> Path:
    path = root / safe_relative(name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise StudioError(f"Source path escapes studio root: {name}")
    if not path.is_file():
        raise StudioError(f"Missing source file: {name}")
    return path


def parse_frontmatter(text: str, name: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise StudioError(f"Missing YAML frontmatter: {name}")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise StudioError(f"Unterminated frontmatter: {name}")
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        match = KEY.match(line.strip())
        if not match:
            raise StudioError(f"Unsupported frontmatter in {name}: {line.strip()!r}")
        key, value = match.groups()
        if key in meta or not value:
            raise StudioError(f"Repeated or empty metadata field {key}: {name}")
        meta[key] = value.strip('"').strip("'")
    if not meta.get("name") or not meta.get("description"):
        raise StudioError(f"name and description are required: {name}")
    body = "".join(lines[end + 1:]).strip() + "\n"
    if not body.strip():
        raise StudioError(f"Empty instructions: {name}")
    return meta, body


def read_manifest() -> dict[str, Any]:
    manifest_path = source_path(SOURCE_ROOT, "studio/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise StudioError("Unsupported studio manifest schema")
    for category in ("roles", "workflows"):
        items = manifest.get(category)
        if not isinstance(items, list) or not items:
            raise StudioError(f"Manifest requires nonempty {category}")
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                raise StudioError(f"Invalid {category} registry entry")
            ident = item.get("id", "")
            if not ROLE_ID.fullmatch(ident) or ident in seen:
                raise StudioError(f"Invalid/duplicate {category} ID: {ident!r}")
            seen.add(ident)
            path = source_path(SOURCE_ROOT, item.get("source", ""))
            meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"), str(path))
            if meta["name"] != ident:
                raise StudioError(f"ID/frontmatter mismatch: {ident} != {meta['name']}")
            if category == "roles" and item.get("kind") not in ("coordination", "implementation", "review"):
                raise StudioError(f"Unsupported role kind for {ident}")
    return manifest


def role_output(runtime: str, role: dict[str, str], meta: dict[str, str], body: str) -> tuple[str, str]:
    ident = role["id"]
    desc = meta["description"]
    if runtime == "claude":
        tools = "Read, Glob, Grep" if role["kind"] == "review" else "Read, Glob, Grep, Write, Edit, Bash, Agent"
        native = (f"---\nname: {ident}\ndescription: {desc}\ntools: {tools}\nmodel: inherit\n---\n"
                  f"<!-- {MARKER} -->\n\n{body}")
        return f".claude/agents/{ident}.md", native
    if runtime == "codex":
        native = (f"# {MARKER}\n"
                  f"name = {json.dumps(ident)}\n"
                  f"description = {json.dumps(desc, ensure_ascii=False)}\n"
                  f"developer_instructions = {json.dumps(body, ensure_ascii=False)}\n")
        return f".codex/agents/{ident}.toml", native
    if runtime == "opencode":
        permissions = "\npermission:\n  edit: deny\n  bash: deny" if role["kind"] == "review" else ""
        native = (f"---\ndescription: {desc}\nmode: subagent{permissions}\n---\n"
                  f"<!-- {MARKER} -->\n\n{body}")
        return f".opencode/agents/{ident}.md", native
    raise StudioError(f"Unsupported runtime {runtime}")


def generated_files(runtime: str) -> dict[str, str]:
    if runtime not in (*RUNTIMES, "all"):
        raise StudioError(f"Unknown runtime: {runtime}")
    manifest = read_manifest()
    selected = RUNTIMES if runtime == "all" else (runtime,)
    outputs: dict[str, str] = {}
    for runtime_name in selected:
        for role in manifest["roles"]:
            source = source_path(SOURCE_ROOT, role["source"])
            meta, body = parse_frontmatter(source.read_text(encoding="utf-8"), role["source"])
            dest, native = role_output(runtime_name, role, meta, body)
            outputs[dest] = native
        for workflow in manifest["workflows"]:
            source = source_path(SOURCE_ROOT, workflow["source"])
            meta, body = parse_frontmatter(source.read_text(encoding="utf-8"), workflow["source"])
            content = f"---\nname: {meta['name']}\ndescription: {meta['description']}\n---\n\n<!-- {MARKER} -->\n\n{body}"
            # Shared Agent Skills: Codex and OpenCode both discover .agents/skills.
            prefix = ".claude/skills" if runtime_name == "claude" else ".agents/skills"
            outputs[f"{prefix}/{workflow['id']}/SKILL.md"] = content
    return dict(sorted(outputs.items()))


def apply_generation(args: argparse.Namespace) -> int:
    files = generated_files(args.runtime)
    target = Path(args.output_root).resolve()
    if args.check:
        drift: list[str] = []
        for relative, expected in files.items():
            path = target / safe_relative(relative)
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                drift.append(relative)
        print(json.dumps({"status": "drift" if drift else "ok", "files": len(files), "drift": drift}, indent=2))
        return 1 if drift else 0
    if args.write:
        # Check every destination before writing anything, to avoid partial generation.
        for relative, content in files.items():
            path = target / safe_relative(relative)
            if path.exists() and path.read_text(encoding="utf-8") != content:
                if MARKER not in path.read_text(encoding="utf-8")[:512]:
                    raise StudioError(f"Refusing to overwrite a user-authored file: {path}")
        for relative, content in files.items():
            path = target / safe_relative(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                path.write_text(content, encoding="utf-8", newline="\n")
        print(json.dumps({"status": "written", "files": len(files), "output_root": str(target)}, indent=2))
    else:
        print(json.dumps({"status": "preview", "files": list(files)}, indent=2))
    return 0


def doctor(args: argparse.Namespace) -> int:
    project = Path(args.project_root).resolve()
    if not project.is_dir():
        raise StudioError(f"Project directory not found: {project}")
    layout_file = project / args.layout
    config: dict[str, Any] = {}
    if layout_file.exists():
        config = json.loads(layout_file.read_text(encoding="utf-8"))
        if config.get("schema_version") != 1:
            raise StudioError("Unknown layout schema version")
    root_label = args.code_root or config.get("code_root")
    if not root_label:
        # Never infer src/ when multiple candidate roots are plausible.
        candidates = [name for name in ("src", "game", "Assets", "Source") if (project / name).is_dir()]
        root_label = candidates[0] if len(candidates) == 1 else None
    code_root = project / safe_relative(root_label) if root_label else None
    tests = config.get("test_root", "tests")
    test_root = project / safe_relative(tests)
    runtime = args.runtime
    report = {
        "project": str(project),
        "runtime": runtime,
        "runtime_installed": shutil.which({"claude": "claude", "codex": "codex", "opencode": "opencode"}[runtime]) is not None,
        "engine_project_detected": (project / "project.godot").is_file(),
        "source_root": root_label,
        "source_root_exists": code_root is not None and code_root.is_dir(),
        "test_root": tests,
        "test_root_exists": test_root.is_dir(),
        "layout_declared": layout_file.exists(),
        "status": "ready-for-static-adoption" if code_root and code_root.is_dir() else "source-root-unresolved",
    }
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ready-for-static-adoption" else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CCGS portable studio generation and diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Validate canonical studio registry and source definitions")
    generate = sub.add_parser("generate", help="Generate native runtime agent and skill definitions")
    generate.add_argument("--runtime", choices=(*RUNTIMES, "all"), default="all")
    generate.add_argument("--output-root", default=str(SOURCE_ROOT))
    options = generate.add_mutually_exclusive_group()
    options.add_argument("--write", action="store_true")
    options.add_argument("--check", action="store_true")
    check = sub.add_parser("doctor", help="Read-only runtime and game project layout diagnostic")
    check.add_argument("--runtime", choices=RUNTIMES, required=True)
    check.add_argument("--project-root", default=".")
    check.add_argument("--layout", default="studio-layout.json")
    check.add_argument("--code-root")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            manifest = read_manifest()
            print(json.dumps({"status": "ok", "roles": len(manifest["roles"]), "workflows": len(manifest["workflows"])}, indent=2))
            return 0
        if args.command == "generate":
            return apply_generation(args)
        return doctor(args)
    except (StudioError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"STUDIO_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
