#!/usr/bin/env python3
"""
Generate lightweight per-folder marquee filename catalogs under `_catalog/`
for zero-404 O(1)-request artwork resolution on ArcadeMatrix (ESP32 & RPi).

Rules:
- Does NOT touch any upstream Pixelcade artwork or CSV/JSON file (zero merge conflicts).
- Validates PNG/GIF binary headers and dimensions (<= 512x512, non-interlaced PNG, > 100 B)
  so corrupt 0-byte or misnamed files are never selected over valid marquees.
- Outputs deterministic UTF-8 `\n`-delimited sorted manifests in `_catalog/<folder>.txt`
  plus `_catalog/_folders.txt`.
"""

import os
import struct
import sys

SKIP_DIRS = {
    ".git",
    ".github",
    "_catalog",
    "scripts",
    "metadata",
    "fonts",
    "user",
    "system",
    "toolkit",
    "sidekickwidgetart",
}

MAX_DIM = 512
MIN_FILE_BYTES = 100


def is_valid_marquee_file(filepath: str, ext_lower: str) -> bool:
    try:
        sz = os.path.getsize(filepath)
        if sz <= MIN_FILE_BYTES:
            return False
        with open(filepath, "rb") as f:
            hdr = f.read(29)
        if ext_lower == ".png":
            if len(hdr) < 29 or hdr[:8] != b"\x89PNG\r\n\x1a\n":
                return False
            w, h, _bd, _ct, _comp, _filt, interlace = struct.unpack(">IIBBBBB", hdr[16:29])
            return 1 <= w <= MAX_DIM and 1 <= h <= MAX_DIM and interlace == 0
        if ext_lower == ".gif":
            if len(hdr) < 10 or hdr[:6] not in (b"GIF87a", b"GIF89a"):
                return False
            w, h = struct.unpack("<HH", hdr[6:10])
            return 1 <= w <= MAX_DIM and 1 <= h <= MAX_DIM
    except OSError:
        return False
    return False


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog_dir = os.path.join(repo_root, "_catalog")
    os.makedirs(catalog_dir, exist_ok=True)

    valid_folders = []
    expected_catalog_files = {"_folders.txt"}
    total_entries = 0

    for entry in sorted(os.listdir(repo_root)):
        if entry.startswith(".") or entry in SKIP_DIRS:
            continue
        folder_path = os.path.join(repo_root, entry)
        if not os.path.isdir(folder_path):
            continue

        valid_files = []
        for fname in sorted(os.listdir(folder_path)):
            if fname.startswith(".") or "\n" in fname or "\r" in fname:
                continue
            ext_lower = os.path.splitext(fname)[1].lower()
            if ext_lower not in (".png", ".gif"):
                continue
            fpath = os.path.join(folder_path, fname)
            if os.path.isfile(fpath) and is_valid_marquee_file(fpath, ext_lower):
                valid_files.append(fname)

        if not valid_files:
            continue

        valid_folders.append(entry)
        cat_name = f"{entry}.txt"
        expected_catalog_files.add(cat_name)
        cat_path = os.path.join(catalog_dir, cat_name)
        payload = ("\n".join(valid_files) + "\n").encode("utf-8")

        existing = None
        if os.path.exists(cat_path):
            with open(cat_path, "rb") as rf:
                existing = rf.read()
        if existing != payload:
            with open(cat_path, "wb") as wf:
                wf.write(payload)

        total_entries += len(valid_files)

    folders_path = os.path.join(catalog_dir, "_folders.txt")
    folders_payload = ("\n".join(valid_folders) + "\n").encode("utf-8")
    existing_folders = None
    if os.path.exists(folders_path):
        with open(folders_path, "rb") as rf:
            existing_folders = rf.read()
    if existing_folders != folders_payload:
        with open(folders_path, "wb") as wf:
            wf.write(folders_payload)

    for fname in os.listdir(catalog_dir):
        if fname.endswith(".txt") and fname not in expected_catalog_files:
            os.remove(os.path.join(catalog_dir, fname))

    print(f"Generated _catalog for {len(valid_folders)} folders ({total_entries} valid marquee files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
