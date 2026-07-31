# -*- coding: utf-8 -*-
"""
rodar_kmz_cfoto.py
"""

import logging

from kmz_export_cfoto import build_kmz_cfoto_per_day

# ======================= CONFIG (edite aqui) =======================

PHOTOS_ROOT = r"D:\GP\SOBREVOOS\2026_07_resultados\geotag-foto"
DAYS = ["27_07", "28_07", "29_07"]
OUTPUT_DIR = PHOTOS_ROOT  # onde salvar os campo_<dia>_cfoto.kmz

UTC_OFFSET = -4.0  # mesmo valor usado no rodar_geotag.py

# Tamanho/qualidade das imagens dentro do KMZ (quanto maior, mais pesado o arquivo)
MAX_FULL_DIM = 1600
FULL_QUALITY = 82
THUMB_SIZE = 320
THUMB_QUALITY = 65

# =====================================================================


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_kmz_cfoto_per_day(
        photos_root=PHOTOS_ROOT,
        days=DAYS,
        output_dir=OUTPUT_DIR,
        utc_offset_hours=UTC_OFFSET,
        max_full_dim=MAX_FULL_DIM,
        full_quality=FULL_QUALITY,
        thumb_size=THUMB_SIZE,
        thumb_quality=THUMB_QUALITY,
    )


if __name__ == "__main__":
    main()
