# -*- coding: utf-8 -*-
"""
geotag_campo.py
"""

from __future__ import annotations

import argparse
import logging
import os

from geotagger import geotag_folder, write_report
from gpx_loader import load_and_merge_gpx


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--gpx-dir", required=True, help="Pasta com todos os arquivos .gpx da campanha")
    p.add_argument("--photos-root", required=True, help="Pasta que contém as subpastas de cada dia")
    p.add_argument("--days", nargs="+", required=True, help="Nomes das subpastas de cada dia, ex.: 27_07 28_07 29_07")
    p.add_argument("--utc-offset", type=float, default=-4.0,
                    help="Deslocamento UTC do relógio da câmera em horas (padrão -4, horário do Amazonas/Rondônia)")
    p.add_argument("--max-diff", type=float, default=30.0,
                    help="Diferença máxima em segundos entre a foto e o ponto GPS (padrão 30s)")
    p.add_argument("--force", action="store_true", help="Sobrescreve o GPS de fotos que já foram geotaggeadas")
    p.add_argument("--report-dir", default=None, help="Pasta para salvar os relatórios CSV (padrão: photos-root)")
    return p.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    logging.info("Carregando e fundindo trilhas GPX de: %s", args.gpx_dir)
    points = load_and_merge_gpx(args.gpx_dir)
    if not points:
        raise SystemExit("Nenhum ponto GPS válido encontrado nos arquivos GPX.")

    report_dir = args.report_dir or args.photos_root
    all_results = []

    for day in args.days:
        day_dir = os.path.join(args.photos_root, day)
        if not os.path.isdir(day_dir):
            logging.warning("Pasta do dia não encontrada, pulando: %s", day_dir)
            continue

        logging.info("=== Processando dia: %s ===", day)
        results = geotag_folder(day_dir, points, args.utc_offset, args.max_diff, args.force)
        write_report(results, os.path.join(report_dir, f"geotag_{day}.csv"))
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
