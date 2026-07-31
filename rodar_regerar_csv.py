# -*- coding: utf-8 -*-
"""
rodar_regerar_csv.py
"""

import logging
import os

from report_builder import build_report_from_tagged_photos, write_report

# ======================= CONFIG (edite aqui) =======================

PHOTOS_ROOT = r"D:\GP\SOBREVOOS\2026_07_resultados\geotag-foto"
DAYS = ["27_07", "28_07", "29_07"]
REPORT_DIR = PHOTOS_ROOT  # onde salvar os geotag_<dia>.csv

UTC_OFFSET = -4.0  # mesmo valor usado no rodar_geotag.py

# =====================================================================


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    for day in DAYS:
        day_dir = os.path.join(PHOTOS_ROOT, day)
        if not os.path.isdir(day_dir):
            logging.warning("Pasta do dia não encontrada, pulando: %s", day_dir)
            continue
        logging.info("=== Lendo GPS já gravado: %s ===", day)
        rows = build_report_from_tagged_photos(day_dir, UTC_OFFSET)
        write_report(rows, os.path.join(REPORT_DIR, f"geotag_{day}.csv"))


if __name__ == "__main__":
    main()
