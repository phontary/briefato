#!/usr/bin/env python3
"""Package the Musterbrief library into the product image.

Copies the Schreibdienst templates from the read-only source archive into
``brain/musterbriefe/templates/`` and applies the near-duplicate **merge map**
(``brain/merges/merge-map.json``) so the deployed container ships one consolidated
template per merged group — the author's archive is never touched.

Data-hygiene gates (unchanged):

* **locked** (never packaged): templates carrying patient traces.
* **reference_only** (packaged, flagged): templates whose prose is derived from licensed
  sources (DocCheck/MSD/AWMF/PubMed) — they may inform structure in-house, but their prose
  must be paraphrased by us before any paying customer sees output built on them.

Merge behaviour:

* Merged entries are generated deterministically by
  ``briefato.brain.muster_merge.build_merged_content`` (four clinical sections merged,
  ``## Quellen`` preserved, all remaining statements kept). Their sha256 is recorded like
  any other packaged file.
* Superseded files are deleted from the packaged copy and dropped from
  ``brain/musterbriefe/manifest.json`` (whose kept entry folds the absorbed synonyms into
  ``indication_keywords`` and records ``merged_from``).

Run:  .venv/bin/python tools/pack-brain.py [--check]
      --check  verify the packaged copy matches what would be packaged (non-zero exit on drift)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "app"))

from briefato.brain import muster_merge  # noqa: E402

BRAIN = REPO / "brain" / "musterbriefe"
MANIFEST = BRAIN / "manifest.json"
DEST = BRAIN / "templates"
SOURCE_FALLBACK = Path("/workspace/schreibdienst/musterbriefe")

# Patient traces found 2026-10-02 (see docs/compliance/11-template-hygiene-checklist.md).
LOCKED = {
    "Cholezystolithiasis.md",
    "Acne-inversa.md",
    "Struma_nodosa_Hyperthyreose.md",
}

_METADATA_FILES = {"packaged.json", "README-PACKAGING.md"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def source_dir(manifest: dict) -> Path:
    src = Path(str(manifest.get("source") or SOURCE_FALLBACK))
    return src if src.is_dir() else SOURCE_FALLBACK


def expected_bytes(entry: dict, src: Path) -> bytes:
    """The bytes the packaged copy must hold for ``entry`` (merged or plain)."""
    if entry.get("merged_from") or entry.get("merged_group"):
        group = next((g for g in muster_merge.groups() if g.file == entry.get("file")), None)
        if group is None:  # pragma: no cover - defensive
            raise RuntimeError(f"no merge group for {entry.get('file')}")
        return muster_merge.build_merged_content(src, group).encode("utf-8")
    return (src / str(entry.get("file"))).read_bytes()


def build(check_only: bool = False) -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    src = source_dir(manifest)

    effective, merge_stats = muster_merge.apply_merges(manifest.get("templates") or [], src)

    packaged: list[dict] = []
    missing: list[str] = []
    for entry in effective:
        name = str(entry.get("file", ""))
        if not name or name in LOCKED:
            continue
        try:
            data = expected_bytes(entry, src)
        except FileNotFoundError:
            missing.append(name)
            continue
        digest = sha256_bytes(data)
        packed = DEST / name
        if check_only:
            if not packed.is_file() or sha256(packed) != digest:
                print(f"DRIFT: {name}", file=sys.stderr)
                return 1
        else:
            packed.write_bytes(data)
        packaged.append(
            {
                "file": name,
                "sha256": digest,
                "licence_risk": entry.get("licence_risk", "low"),
                "merged": bool(entry.get("merged_from")),
                "merged_from": list(entry.get("merged_from", [])),
            }
        )

    if check_only:
        expected_names = {p["file"] for p in packaged}
        stale = sorted(
            path.name
            for path in DEST.glob("*.md")
            if path.name not in expected_names and path.name not in _METADATA_FILES
        )
        if stale:
            for name in stale:
                print(f"STALE: {name}", file=sys.stderr)
            return 1
        print(
            f"OK: {len(packaged)} packaged templates match ({merge_stats['merged_groups']} merged groups, "
            f"{len(LOCKED)} locked)"
        )
        return 0

    # Persist the merge-applied manifest (the archive-derived manifest is the input).
    merged_count = sum(1 for entry in effective if entry.get("merged_from"))
    manifest["templates"] = effective
    manifest["count"] = len(effective)
    counts = dict(manifest.get("counts") or {})
    counts["files"] = len(effective)
    counts["duplicate_pairs"] = 0
    counts["merged_groups"] = merge_stats["merged_groups"]
    counts["files_absorbed"] = merge_stats["files_absorbed"]
    manifest["counts"] = counts
    manifest["merge_map"] = "brain/merges/merge-map.json"
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Delete superseded / stale markdown in the packaged copy.
    expected_names = {p["file"] for p in packaged}
    removed: list[str] = []
    for path in sorted(DEST.glob("*.md")):
        if path.name not in expected_names and path.name not in _METADATA_FILES:
            path.unlink()
            removed.append(path.name)

    stats = {
        "packaged": len(packaged),
        "merged": merged_count,
        "locked": sorted(LOCKED),
        "removed_stale": removed,
        "missing_in_source": sorted(missing),
        "licence_review": sorted(p["file"] for p in packaged if p["licence_risk"] == "review"),
        "source": str(src),
        "templates": packaged,
    }
    (DEST / "packaged.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    note = f"""# Musterbriefe — packaged copy (product image)

Generated by `tools/pack-brain.py` from the read-only Schreibdienst archive
(`{src}`) and the merge map `brain/merges/merge-map.json`. Do not edit files in this
directory by hand: edit the source archive (or the brain update process) and re-run the packer.

- packaged: **{stats['packaged']}** templates ({merged_count} generated from merged groups)
- merged groups: {merge_stats['merged_groups']} ({merge_stats['files_absorbed']} source files absorbed)
- removed superseded files: {", ".join(removed) or "none"}
- locked (patient traces — never packaged): {", ".join(stats['locked'])}
- licence review (structure may be used, prose must be paraphrased before paying customers):
  {", ".join(stats['licence_review']) or "none"}
- missing in source: {", ".join(stats['missing_in_source']) or "none"}

Integrity: every file's sha256 is recorded in `packaged.json`; `tools/pack-brain.py --check`
regenerates merged files and verifies the packaged copy against source + merge map.
"""
    (DEST / "README-PACKAGING.md").write_text(note, encoding="utf-8")
    print(
        f"packaged {stats['packaged']} templates ({merged_count} merged, removed {len(removed)} stale), "
        f"locked {len(stats['locked'])}, licence-review {len(stats['licence_review'])}, "
        f"missing {len(missing)}"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify without writing")
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    raise SystemExit(build(check_only=args.check))
