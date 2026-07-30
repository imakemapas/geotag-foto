# -*- coding: utf-8 -*-
"""
rodar_kmz.py
"""

import logging

from kmz_export import build_kmz_per_day

# ======================= CONFIG (edite aqui) =======================

PHOTOS_ROOT = r"D:\GP\SOBREVOOS\2026_07_resultados\geo-foto"
DAYS = ["27_07", "28_07", "29_07"]
OUTPUT_DIR = PHOTOS_ROOT

UTC_OFFSET = -4.0  # mesmo valor usado no rodar_geotag.py

# =====================================================================


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_kmz_per_day(
        photos_root=PHOTOS_ROOT,
        days=DAYS,
        output_dir=OUTPUT_DIR,
        utc_offset_hours=UTC_OFFSET,
    )


if __name__ == "__main__":
    main()


