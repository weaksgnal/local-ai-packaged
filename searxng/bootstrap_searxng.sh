#!/usr/bin/env bash
# bootstrap_searxng.sh — apply settings.overrides.yml on top of machine-local
# settings.yml in place. Idempotent. Does not touch any field other than the
# `disabled:` line of the engines listed in settings.overrides.yml.
#
# Run from the repo (~/local-ai). After running, restart searxng:
#   docker compose -p local-ai \
#     -f docker-compose.yml -f docker-compose.override.private.yml \
#     restart searxng
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS="${HERE}/settings.yml"
OVERRIDES="${HERE}/settings.overrides.yml"

if [[ ! -f "${SETTINGS}" ]]; then
  echo "ERROR: ${SETTINGS} not found (expected machine-local, gitignored)." >&2
  exit 1
fi
if [[ ! -f "${OVERRIDES}" ]]; then
  echo "ERROR: ${OVERRIDES} not found (expected tracked override file)." >&2
  exit 1
fi

python3 - "${SETTINGS}" "${OVERRIDES}" <<'PY'
import re
import sys
from pathlib import Path

import yaml

settings_path = Path(sys.argv[1])
overrides_path = Path(sys.argv[2])

overrides = yaml.safe_load(overrides_path.read_text()) or {}
engines = overrides.get("engines") or []
if not engines:
    print(f"no engine overrides in {overrides_path.name}; nothing to do")
    sys.exit(0)

text = settings_path.read_text()
lines = text.splitlines(keepends=True)

# Find each top-level `engines:` list entry by scanning for lines that start
# with `  - name: <engine>` (two-space indent matches the searxng default
# settings.yml layout). For each target engine, within its block (up to the
# next `  - ` at the same indent OR end of engines: section), flip the
# `disabled:` line only.

def find_engine_block(lines, engine_name):
    """Return (start_idx, end_idx) for the engine whose name == engine_name.

    start_idx is the index of the `  - name: <engine>` line.
    end_idx is the index one past the last line of the block (exclusive).
    Returns None if not found.
    """
    name_re = re.compile(r"^  - name:\s*" + re.escape(engine_name) + r"\s*$")
    next_item_re = re.compile(r"^  - ")  # next list item at same indent
    outdent_re = re.compile(r"^[^ #]")  # new top-level key -> end of engines:

    for i, line in enumerate(lines):
        if name_re.match(line):
            # Walk forward until next sibling item or outdent.
            j = i + 1
            while j < len(lines):
                ln = lines[j]
                if next_item_re.match(ln):
                    break
                if outdent_re.match(ln):
                    break
                j += 1
            return (i, j)
    return None

changed = False
summary = []
for ov in engines:
    name = ov.get("name")
    desired = ov.get("disabled")
    if name is None or desired is None:
        print(f"skipping malformed override: {ov!r}")
        continue

    block = find_engine_block(lines, name)
    if block is None:
        print(f"WARN: engine '{name}' not found in settings.yml; skipping")
        summary.append((name, "missing"))
        continue

    start, end = block
    # Find `    disabled:` line within the block (4-space indent under list item).
    disabled_re = re.compile(r"^(    disabled:\s*)(true|false)(\s*(?:#.*)?)$")
    found_idx = None
    current = None
    for k in range(start + 1, end):
        m = disabled_re.match(lines[k].rstrip("\n"))
        if m:
            found_idx = k
            current = m.group(2)
            break

    desired_str = "true" if desired else "false"
    if found_idx is None:
        # No existing disabled: line. Insert one at end of block.
        # Preserve trailing newline state.
        insert_line = f"    disabled: {desired_str}\n"
        # Keep block contiguous — insert just before end, making sure the
        # previous line ends with \n.
        if end > 0 and not lines[end - 1].endswith("\n"):
            lines[end - 1] = lines[end - 1] + "\n"
        lines.insert(end, insert_line)
        changed = True
        summary.append((name, f"inserted disabled: {desired_str}"))
    elif current == desired_str:
        summary.append((name, f"already disabled: {desired_str}"))
    else:
        # Replace only the boolean token, preserve indent and any trailing comment.
        orig = lines[found_idx]
        m = disabled_re.match(orig.rstrip("\n"))
        new = f"{m.group(1)}{desired_str}{m.group(3)}\n"
        lines[found_idx] = new
        changed = True
        summary.append((name, f"flipped {current} -> {desired_str}"))

new_text = "".join(lines)
if changed:
    settings_path.write_text(new_text)
    print(f"wrote {settings_path}")
else:
    print("no changes (already in desired state)")

for name, action in summary:
    print(f"  {name}: {action}")
PY
