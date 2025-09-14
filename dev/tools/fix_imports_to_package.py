#!/usr/bin/env python3
from __future__ import annotations
import argparse, re
from pathlib import Path
from typing import Dict, List, Iterable

PKG = "carefirst"
SRC = Path("src") / PKG

RE_FROM = re.compile(r"^(?P<indent>\s*)from\s+(?P<mod>[A-Za-z_][\w\.]*)\s+import\s+(?P<rest>.+)$")
RE_IMPORT = re.compile(r"^(?P<indent>\s*)import\s+(?P<rest>.+)$")

def all_module_paths() -> Dict[str, List[str]]:
    """Map leaf module name -> list of full dotted paths under carefirst."""
    m: Dict[str, List[str]] = {}
    if not SRC.exists():
        return m
    for p in SRC.rglob("*.py"):
        if p.name == "__init__.py":
            continue
        rel = p.relative_to(SRC).with_suffix("")  # e.g. app/core_services_sop_registry
        dotted = ".".join(rel.parts)              # e.g. app.core_services_sop_registry
        leaf = rel.name                           # e.g. core_services_sop_registry
        m.setdefault(leaf, []).append(dotted)
    return m

def is_parenthesized(line: str) -> bool:
    return "(" in line and ")" not in line and "\\" not in line

def rewrite_file(path: Path, leaf_index: Dict[str, List[str]]) -> tuple[str, List[str]]:
    changes: List[str] = []
    out: List[str] = []
    lines = path.read_text(encoding="utf-8").splitlines(True)

    for i, line in enumerate(lines):
        orig = line
        if is_parenthesized(line):
            out.append(line); continue

        m = RE_FROM.match(line)
        if m:
            indent, mod, rest = m.group("indent", "mod", "rest")
            if mod.startswith(f"{PKG}.") or mod.startswith("."):
                out.append(line); continue
            first = mod.split(".")[0]
            # If module is a bare leaf and unique, expand to full path
            if "." not in mod and first in leaf_index and len(leaf_index[first]) == 1:
                full = leaf_index[first][0]                  # e.g. app.core_services_sop_registry
                new = f"{indent}from {PKG}.{full} import {rest}\n"
                if new != line:
                    changes.append(f"{path}:{i+1}: {orig.rstrip()}  -->  {new.rstrip()}")
                    line = new
            out.append(line); continue

        m = RE_IMPORT.match(line)
        if m:
            indent, rest = m.group("indent", "rest")
            parts = [p.strip() for p in rest.split(",")]
            new_parts = []
            changed = False
            for part in parts:
                if not part: continue
                toks = part.split()
                name = toks[0]; alias = toks[2] if len(toks)>=3 and toks[1]=="as" else None

                if name.startswith(f"{PKG}.") or name.startswith("."):
                    new_parts.append(part); continue

                first = name.split(".")[0]
                if "." not in name and first in leaf_index and len(leaf_index[first]) == 1:
                    full = f"{PKG}.{leaf_index[first][0]}"
                    repl = f"{full}" + (f" as {alias}" if alias else "")
                    new_parts.append(repl); changed = True
                else:
                    new_parts.append(part)

            if changed:
                changes.append(f"{path}:{i+1}: {orig.rstrip()}  -->  {indent}import " + ", ".join(new_parts))
                line = f"{indent}import " + ", ".join(new_parts) + "\n"
            out.append(line); continue

        out.append(line)

    return "".join(out), changes

def files_to_scan() -> Iterable[Path]:
    for root in ["src/carefirst", "scripts"]:
        base = Path(root)
        if base.exists():
            yield from base.rglob("*.py")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    leaf_index = all_module_paths()
    if not leaf_index:
        print(f"[warn] No modules found under {SRC}")
        return

    any_changes = False
    for path in files_to_scan():
        new_text, changes = rewrite_file(path, leaf_index)
        if changes:
            any_changes = True
            print("\n".join(changes))
            if args.apply:
                path.write_text(new_text, encoding="utf-8")
    if not any_changes:
        print("[ok] No import rewrites needed.")
    elif not args.apply:
        print("\n[DRY-RUN] Re-run with --apply to write changes.")

if __name__ == "__main__":
    main()
