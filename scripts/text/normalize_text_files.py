#!/usr/bin/env python3
"""
Normalize text file encodings to UTF-8 (no BOM) and line endings to LF.
Usage:
  python scripts/text/normalize_text_files.py --root . --fix
  python scripts/text/normalize_text_files.py --root . --dry-run

Notes:
- Skips binary files and common asset directories by default.
- If `chardet` is installed it will be used for encoding detection.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

try:
    import chardet
except Exception:
    chardet = None

SKIP_DIRS = {".git", "runtime", "node_modules", "venv", "__pycache__"}
SKIP_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".pb",
    ".bin",
    ".exe",
    ".dll",
    ".so",
}

CHUNK = 8192
DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def is_binary_bytes(data: bytes) -> bool:
    return b"\x00" in data


def detect_encoding(data: bytes) -> str:
    # BOM checks
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return "utf-16"
    # use chardet if available
    if chardet is not None:
        res = chardet.detect(data)
        enc = res.get("encoding")
        if enc:
            return enc
    # fallback
    try:
        data.decode("utf-8")
        return "utf-8"
    except Exception:
        return "latin-1"


def normalize_text(text: str) -> str:
    # Normalize CRLF and CR to LF
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    return text


def process_file(path: Path, fix: bool) -> Optional[str]:
    try:
        with path.open("rb") as f:
            data = f.read()
    except Exception as e:
        return f"ERROR reading: {e}"

    # ignore binary files heuristically
    if is_binary_bytes(data[:CHUNK]):
        return None

    enc = detect_encoding(data[:CHUNK*4])

    try:
        text = data.decode(enc, errors="strict")
    except Exception:
        # final fallback: latin-1 with replacement to preserve bytes
        try:
            text = data.decode("latin-1")
            enc = "latin-1"
        except Exception as e:
            return f"ERROR decoding: {e}"

    new_text = normalize_text(text)
    new_bytes = new_text.encode("utf-8")  # no BOM

    changed = False
    # compare normalized bytes with original content normalized for BOM and line endings
    # Build canonical original as decoded then encoded utf-8
    try:
        canonical_orig = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    except Exception:
        canonical_orig = data

    if canonical_orig != new_bytes:
        changed = True

    if changed and fix:
        try:
            with path.open("wb") as f:
                f.write(new_bytes)
        except Exception as e:
            return f"ERROR writing: {e}"

    if changed:
        return f"CHANGED (encoding={enc})"
    else:
        return "OK"


def should_skip(path: Path) -> bool:
    # skip directories
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    if path.suffix.lower() in SKIP_EXT:
        return True
    return False


def walk_and_apply(root: Path, fix: bool, dry_run: bool):
    summary = {"total": 0, "changed": 0, "skipped": 0, "errors": 0}
    for dirpath, dirnames, filenames in os.walk(root):
        # filter out skip dirs in-place to speed up
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            p = Path(dirpath) / fname
            summary["total"] += 1
            if should_skip(p):
                summary["skipped"] += 1
                continue
            result = process_file(p, fix and not dry_run)
            if result is None:
                summary["skipped"] += 1
                continue
            if result.startswith("ERROR"):
                summary["errors"] += 1
                print(f"{p}: {result}")
            elif result == "OK":
                # no change
                pass
            elif result.startswith("CHANGED"):
                summary["changed"] += 1
                action = "would change" if dry_run or not fix else "changed"
                print(f"{p}: {action} - {result}")
            else:
                print(f"{p}: {result}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Normalize text files to UTF-8 (no BOM) and LF line endings")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Project root to scan")
    parser.add_argument("--fix", action="store_true", help="Actually write changes")
    parser.add_argument("--dry-run", action="store_true", help="Do not write, only show what would change")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root path not found: {root}")
        sys.exit(2)

    if args.dry_run and args.fix:
        print("Cannot use --dry-run and --fix together")
        sys.exit(2)

    print(f"Scanning {root} (fix={args.fix}, dry_run={args.dry_run})")
    summary = walk_and_apply(root, fix=args.fix, dry_run=args.dry_run)
    print("---")
    print(f"Total files: {summary['total']}")
    print(f"Changed: {summary['changed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Errors: {summary['errors']}")

    if summary['errors'] > 0:
        sys.exit(3)


if __name__ == '__main__':
    main()
