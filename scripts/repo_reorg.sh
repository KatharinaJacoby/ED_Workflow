#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "Running in DRY RUN mode (no changes will be made)."
fi

# Helpers
tracked() {
  git ls-files --error-unmatch "$1" >/dev/null 2>&1
}

do_mv() {
  local src="$1" dst="$2"
  if $DRY_RUN; then
    echo "[dry-run] move '$src' -> '$dst'"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  if tracked "$src"; then
    git mv -f "$src" "$dst"
  else
    mv -f "$src" "$dst"
  fi
}

maybe_delete_if_identical() {
  # If dst exists and files are byte-identical, delete src (or skip move).
  local src="$1" dst="$2"
  if [[ -f "$dst" ]]; then
    local a b
    a=$(sha256sum -- "$src" | awk '{print $1}')
    b=$(sha256sum -- "$dst" | awk '{print $1}')
    if [[ "$a" == "$b" ]]; then
      if $DRY_RUN; then
        echo "[dry-run] identical to existing '$dst' -> would remove '$src'"
      else
        if tracked "$src"; then
          # If tracked, git rm the duplicate
          git rm -f -- "$src"
        else
          rm -f -- "$src"
        fi
      fi
      return 0
    fi
  fi
  return 1
}

normalize_nb_name() {
  # Strip trailing " HH.MM.SS" or " HH.MM.SS.ext" patterns and excessive spaces
  local base="$1"
  # Remove trailing " <hh.mm.ss>" just before extension
  base="$(echo "$base" | sed -E 's/ ([0-9]{2}\.[0-9]{2}\.[0-9]{2})(\.[[:alnum:]]+)?$/\2/')"
  # Collapse spaces
  echo "$base" | sed -E 's/[[:space:]]+/ /g'
}

ensure_dirs() {
  mkdir -p notebooks data data/models docs artifacts
}

move_notebooks_from_root() {
  shopt -s nullglob
  for f in ./*.ipynb*; do
    [[ -f "$f" ]] || continue
    local name="$(basename "$f")"
    local clean="$(normalize_nb_name "$name")"
    local dst="notebooks/$clean"

    # If a clean normalization removed the name entirely, fallback
    if [[ -z "$clean" ]]; then
      clean="$name"
      dst="notebooks/$clean"
    fi

    # If identical target exists, remove src
    if maybe_delete_if_identical "$f" "$dst"; then
      continue
    fi

    # If different target exists, append -ALT
    if [[ -e "$dst" ]]; then
      local stem="${clean%.*}"
      local ext="${clean##*.}"
      if [[ "$ext" == "$stem" ]]; then ext=""; else ext=".$ext"; fi
      dst="notebooks/${stem}-ALT${ext}"
      echo "Target exists and differs; using alt name: $(basename "$dst")"
    fi

    do_mv "$f" "$dst"
  done
  shopt -u nullglob
}

move_configs_from_root() {
  local files=(
    "ai_coordinator_policy.yaml"
    "ed_config.example.yaml"
    "ed_synth_blueprints.yaml"
    "synthetic_config.yaml"
  )
  for f in "${files[@]}"; do
    [[ -f "$f" ]] || continue
    local dst="data/$f"
    if maybe_delete_if_identical "$f" "$dst"; then continue; fi
    do_mv "$f" "$dst"
  done
}

move_models_from_root() {
  local files=(
    "ed_operational_classifier.joblib"
    "ed_phase2_model.joblib"
    "ed_phase2_model_thr_patched.joblib"
    "ed_phase2_model_thr_patched(1).joblib"
  )
  for f in "${files[@]}"; do
    [[ -f "$f" ]] || continue
    local dst="data/models/$(basename "$f")"
    if maybe_delete_if_identical "$f" "$dst"; then continue; fi
    do_mv "$f" "$dst"
  done
}

move_docs_from_root() {
  local files=(
    "Day 4 — Simplified Baseline Modeling"
    "ED_Project_Mandate_MACHINE.yaml"
    "ed_integration_checklist.html"
    "MIMIC-MLP Pipeline Phase1+2-baseline"
  )
  for f in "${files[@]}"; do
    [[ -e "$f" ]] || continue
    local dst="docs/$(basename "$f")"
    if [[ -f "$f" ]]; then
      if maybe_delete_if_identical "$f" "$dst"; then continue; fi
    fi
    do_mv "$f" "$dst"
  done
}

move_artifacts_from_root() {
  local files=(
    "ed_demo_bundle_20250820T083737Z.zip"
    "ed_demo_bundle_20250820T083737Z(1).zip"
    "mimic-iv-ed-demo-2.2.zip"
    "results.zip"
  )
  for f in "${files[@]}"; do
    [[ -f "$f" ]] || continue
    local dst="artifacts/$(basename "$f")"
    if maybe_delete_if_identical "$f" "$dst"; then continue; fi
    do_mv "$f" "$dst"
  done
}

main() {
  # sanity: ensure we're at repo root by checking for .git and README.md
  if [[ ! -d .git ]]; then
    echo "⚠️  This does not look like a Git repository root ('.git' not found)."
    echo "    If this is correct, remove this check or run from repo root."
    exit 1
  fi

  ensure_dirs
  move_notebooks_from_root
  move_configs_from_root
  move_models_from_root
  move_docs_from_root
  move_artifacts_from_root

  echo
  echo "✅ Done."
  if $DRY_RUN; then
    echo "This was a dry run. Re-run without --dry-run to apply changes."
  else
    echo "Next steps:"
    echo "  - Review with: git status && git diff --staged"
    echo "  - Commit:      git commit -m 'repo: move loose files into folders and normalize notebook names'"
  fi
}

main "$@"
