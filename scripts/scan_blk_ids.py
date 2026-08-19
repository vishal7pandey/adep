"""Scan for duplicate BLK-IDs in the codebase [BLK-292]."""

import re
from collections import Counter
from pathlib import Path

BLK_PATTERN = re.compile(r"BLK-(\d{3})")

def scan_blk_ids(root: str = ".") -> dict:
    root_path = Path(root)
    all_ids = []
    file_locations: dict[str, list[tuple[str, int]]] = {}

    for ext in ("*.py", "*.ts", "*.tsx", "*.md"):
        for filepath in root_path.rglob(ext):
            # Skip common irrelevant dirs
            if any(part in {".venv", "node_modules", "__pycache__", ".git", ".next"} for part in filepath.parts):
                continue
            try:
                text = filepath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for m in BLK_PATTERN.finditer(line):
                    blk_id = m.group()
                    all_ids.append(blk_id)
                    file_locations.setdefault(blk_id, []).append((str(filepath), i))

    counts = Counter(all_ids)
    duplicates = {k: v for k, v in counts.items() if v > 1}
    return {
        "total_ids": len(all_ids),
        "unique_ids": len(counts),
        "duplicates": duplicates,
        "all_counts": dict(counts.most_common()),
        "file_locations": file_locations,
    }


if __name__ == "__main__":
    result = scan_blk_ids(".")
    print(f"Total BLK-ID references: {result['total_ids']}")
    print(f"Unique BLK-IDs: {result['unique_ids']}")
    print(f"Duplicate BLK-IDs: {len(result['duplicates'])}")
    print()
    if result["duplicates"]:
        print("Duplicate BLK-IDs (count > 1):")
        for blk_id, count in sorted(result["duplicates"].items(), key=lambda x: -x[1]):
            print(f"  {blk_id}: {count} references")
            for filepath, line in result["file_locations"][blk_id][:5]:
                print(f"    - {filepath}:{line}")
            if len(result["file_locations"][blk_id]) > 5:
                print(f"    ... and {len(result['file_locations'][blk_id]) - 5} more")
