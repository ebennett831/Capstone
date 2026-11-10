import argparse
from collections.abc import Callable, Sequence

from backend.storage.local_storage import LocalStorage


def clear_uploads(
    storage: LocalStorage,
    *,
    dry_run: bool,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    files = storage.clear_managed_files(dry_run=True)
    action = "Would delete" if dry_run else "Found"
    output_fn(f"{action} {len(files)} managed file(s):")
    for path in files:
        output_fn(f"- {path.relative_to(storage.data_root)}")

    if dry_run or not files:
        return 0

    confirmation = input_fn('Type "DELETE" to remove these managed files: ')
    if confirmation != "DELETE":
        output_fn("Cleanup cancelled; no files were deleted.")
        return 1

    deleted = storage.clear_managed_files(dry_run=False)
    output_fn(f"Deleted {len(deleted)} managed file(s).")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Safely remove locally stored AI Lacrosse Coach uploads and metadata."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List managed files without deleting them.",
    )
    args = parser.parse_args(argv)
    return clear_uploads(LocalStorage(), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
