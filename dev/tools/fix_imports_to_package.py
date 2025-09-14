#!/usr/bin/env python3
"""
Rewrite bare imports to 'carefirst.<module>' when the imported top-level name
matches a module/package under src/carefirst/.

Examples:
  from core_services_sop_registry import SOPRegistry -> from carefirst.core_services_sop_registry import SOPRegistry
  import core_services_sop_registry as csr           -> import carefirst.core_services_sop_registry as csr

Safe guards:
- Skips lines already importing from 'carefirst.' or using relative imports (from .foo import ...).
- Only rewrites when the FIRST segment (before any dot) matches a top-level name found under src/carefirst/.
- Expands comma imports into separate lines to avoid tricky formatting.
- Leaves multiline/parenthesized imports untouched (reported but not changed).
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path
from typing import Iterable

PKG = "carefirst"
SRC = Path("src") / PKG

# Simple regexes (single-line imports only)
RE_FROM = re.compile(r"^(?P<indent>\s*)from\s+(?P<mod>[A-Za-z_][\w\.]*)\s+import\s+(?P<rest>.+)$")
RE_IMPORT = re.compile(r"^(?P<indent>\s*)import\s+(?P<rest>.+)$")

def top_level_names() -> set[str]:
    names: set[str] = set()
    if not SRC.exists():
        return names
    for p in SRC.iterdir():
        if p.name.startswith("_"):
            continue
        if p.is_dir() and (p / "__init__.py").exists():
            names.add(p.name)
        elif p.is_file() and p.suffix == ".py":
            names.add(p.stem)
    return names

def is_parenthesized(line: str) -> bool:
    # crude heuristic; skip to be safe
    return "(" in line and ")" not in line and "\\" not in line

def rewrite_lines(path: Path, topnames: set[str]) -> tuple[str, list[str]]:
    changed_lines: list[str] = []
    new_text_lines: list[str] = []

    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        orig = line

        # Skip obviously dangerous cases
        if is_parenthesized(line):
            new_text_lines.append(line)
            continue

        m = RE_FROM.match(line)
        if m:
            indent, mod, rest = m.group("indent", "mod", "rest")
            if mod.startswith(PKG + ".") or mod.startswith("."):
                new_text_lines.append(line)
                continue
            first = mod.split(".")[0]
            if first in topnames:
                new = f"{indent}from {PKG}.{mod} import {rest}\n"
                if new != line:
                    changed_lines.append(f"{path}:{i+1}: {line.rstrip()}  -->  {new.rstrip()}")
                    line = new
            new_text_lines.append(line)
            continue

        m = RE_IMPORT.match(line)
        if m:
            indent, rest = m.group("indent", "rest")
            # Split on commas at top level (no parentheses handling)
            parts = [p.strip() for p in rest.split(",")]
            out_lines: list[str] = []
            changed_any = False
            for part in parts:
                if not part:
                    continue
                # part can be "name" or "name as alias"
                tokens = part.split()
                name = tokens[0]
                alias = None
                if len(tokens) >= 3 and tokens[1] == "as":
                    alias = tokens[2]

                if name.startswith(PKG + ".") or name.startswith("."):
                    out = f"{indent}import {name}"
                    if alias:
                        out += f" as {alias}"
                    out_lines.append(out + "\n")
                    continue

                first = name.split(".")[0]
                if first in topnames:
                    changed_any = True
                    newname = f"{PKG}.{name}"
                    out = f"{indent}import {newname}"
                    if alias:
                        out += f" as {alias}"
                    out_lines.append(out + "\n")
                else:
                    # leave as-is
                    out = f"{indent}import {name}"
                    if alias:
                        out += f" as {alias}"
                    out_lines.append(out + "\n")

            if changed_any:
                changed_lines.append(f"{path}:{i+1}: {orig.rstrip()}  -->")
                for ol in out_lines:
                    changed_lines.append(f"    {ol.rstrip()}")
                new_text_lines.extend(out_lines)
            else:
                new_text_lines.append(orig)
            continue

        # default: unchanged
        new_text_lines.append(line)

    return "".join(new_text_lines), changed_lines

def iter_py_files() -> Iterable[Path]:
    # Scan your code and scripts; skip venv/tests
    for root in ["src/carefirst", "scripts"]:
        base = Path(root)
        if base.exists():
            for p in base.rglob("*.py"):
                yield p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Write changes to files")
    args = ap.parse_args()

    topnames = top_level_names()
    if not topnames:
        print(f"[warn] No modules detected under {SRC}. Nothing to do.")
        return

    all_changes: list[str] = []
    for path in iter_py_files():
        new_text, changed = rewrite_lines(path, topnames)
        if changed:
            all_changes.extend(changed)
            if args.apply:
                path.write_text(new_text, encoding="utf-8")

    if all_changes:
        print("\n".join(all_changes))
        if not args.apply:
            print("\n[DRY-RUN] Changes not written. Re-run with --apply to modify files.")
    else:
        print("[ok] No import rewrites needed.")

if __name__ == "__main__":
    main()
