#!/usr/bin/env python
"""
Move all .md and .txt files into an /archive/ folder, preserving structure.

- Default root: current working directory
- Default mode: dry run (no changes)
- Use --really-move to actually move files
"""

import argparse
from pathlib import Path


def move_md_and_txt_to_archive(root: Path, dry_run: bool = True) -> None:
    """Recursively move all .md and .txt files into root/archive/."""
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Root path does not exist or is not a directory: {root}")

    archive_root = root / "archive"
    archive_root.mkdir(exist_ok=True)

    patterns = {".md", ".txt"}
    moved_count = 0

    print(f"Scanning under: {root}")
    print(f"Archive target: {archive_root}\n")

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        # Skip files already inside archive/
        if path.is_relative_to(archive_root):
            continue

        if path.suffix.lower() not in patterns:
            continue

        rel = path.relative_to(root)
        dest = archive_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest_rel = dest.relative_to(root)

        if dry_run:
            print(f"[DRY RUN] Would move: {rel} -> {dest_rel}")
        else:
            if dest.exists():
                print(f"[SKIP] Destination exists, not overwriting: {dest_rel}")
                continue

            print(f"Moving: {rel} -> {dest_rel}")
            path.rename(dest)
            moved_count += 1

    if dry_run:
        print("\nDry run complete. No files were moved.")
    else:
        print(f"\nDone. Moved {moved_count} files into {archive_root}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Move all .md and .txt files into /archive/."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Repo root directory (default: current working directory).",
    )
    parser.add_argument(
        "--really-move",
        action="store_true",
        help="Actually move files (default is dry-run).",
    )

    args = parser.parse_args()
    repo_root = Path(args.root).resolve()
    dry_run = not args.really_move

    move_md_and_txt_to_archive(repo_root, dry_run=dry_run)


if __name__ == "__main__":
    main()
