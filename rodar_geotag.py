# -*- coding: utf-8 -*-
"""
rodar_geotag.py
"""

import logging

from geotagger import geotag_folder, write_report
from gpx_loader import load_and_merge_gpx

# ======================= CONFIG (edite aqui) =======================

GPX_DIR = r"D:\GP\SOBREVOOS\2026_07_resultados\geo-foto\gpx"
PHOTOS_ROOT = r"D:\GP\SOBREVOOS\2026_07_resultados\geo-foto"
DAYS = ["27_07", "28_07", "29_07"]

UTC_OFFSET = -4.0      # deslocamento do relógio da câmera em relação ao UTC
MAX_DIFF_SECONDS = 30  # diferença máxima aceita entre foto e ponto GPS
FORCE_OVERWRITE = False  # True sobrescreve fotos que já têm GPS

REPORT_DIR = PHOTOS_ROOT

# =====================================================================

import os


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logging.info("Carregando e fundindo trilhas GPX de: %s", GPX_DIR)
    points = load_and_merge_gpx(GPX_DIR)
    if not points:
        raise SystemExit("Nenhum ponto GPS válido encontrado nos arquivos GPX.")

    all_results = []
    for day in DAYS:
        day_dir = os.path.join(PHOTOS_ROOT, day)
        if not os.path.isdir(day_dir):
            logging.warning("Pasta do dia não encontrada, pulando: %s", day_dir)
            continue

        logging.info("=== Processando dia: %s ===", day)
        results = geotag_folder(day_dir, points, UTC_OFFSET, MAX_DIFF_SECONDS, FORCE_OVERWRITE)
        write_report(results, os.path.join(REPORT_DIR, f"geotag_{day}.csv"))
        all_results.extend(results)

    if not all_results:
        logging.warning("Nenhuma foto processada.")
        return

    ok = sum(1 for r in all_results if r.status == "ok")
    skip = sum(1 for r in all_results if r.status == "ja_tinha_gps")
    fail = len(all_results) - ok - skip
    logging.info("Concluído: %d geotaggeadas | %d já tinham GPS | %d falharam (de %d fotos)",
                 ok, skip, fail, len(all_results))


if __name__ == "__main__":
    main()
