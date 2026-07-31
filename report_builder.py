# -*- coding: utf-8 -*-
"""
report_builder.py
Gera (ou regenera) o relatório CSV lendo o GPS que JÁ está gravado nas
fotos — sem tocar em nenhuma foto, sem precisar do GPX de novo.

Use isto quando as fotos já foram geotaggeadas e você só quer
reconstruir/atualizar o CSV (por exemplo, depois que o formato do
relatório ganhou uma coluna nova). Complementa o geotag_campo.py, que
por padrão PULA fotos que já têm GPS (não recalcula, não sobrescreve) —
e por isso não preenche lat/lon pra elas no CSV. Esta ferramenta lê o
valor real gravado na foto em vez de recalcular a partir do GPX.
"""

from __future__ import annotations

import csv
import logging
import os
from dataclasses import asdict, dataclass
from typing import List, Optional

from exif_utils import get_capture_time, read_exif, read_gps_decimal
from geotagger import list_photos

logger = logging.getLogger(__name__)


@dataclass
class ReportRow:
    filename: str
    nome_arquivo: str
    status: str  # "ok" | "sem_gps"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    capture_time_local: Optional[str] = None


def build_report_from_tagged_photos(photos_dir: str, utc_offset_hours: float = -4.0) -> List[ReportRow]:
    photo_paths = list_photos(photos_dir)
    logger.info("%s: %d fotos encontradas (em todas as subpastas)", photos_dir, len(photo_paths))

    rows: List[ReportRow] = []
    for photo_path in photo_paths:
        display_name = os.path.relpath(photo_path, photos_dir).replace(os.sep, "/")
        nome_arquivo = os.path.splitext(os.path.basename(photo_path))[0]

        exif_dict = read_exif(photo_path)
        capture_time = get_capture_time(exif_dict, utc_offset_hours)
        capture_str = capture_time.isoformat() if capture_time else None

        gps = read_gps_decimal(photo_path)
        if gps is None:
            rows.append(ReportRow(display_name, nome_arquivo, "sem_gps", capture_time_local=capture_str))
            logger.warning("SEM GPS: %s", display_name)
            continue

        lat, lon, alt = gps
        rows.append(ReportRow(
            display_name, nome_arquivo, "ok",
            latitude=lat, longitude=lon, altitude=alt,
            capture_time_local=capture_str,
        ))

    return rows


def write_report(rows: List[ReportRow], output_csv: str) -> None:
    """Sempre reescreve o CSV do zero (nunca em modo append)."""
    if not rows:
        logger.warning("Nenhuma linha para gravar em %s", output_csv)
        return
    out_dir = os.path.dirname(output_csv)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    fieldnames = list(asdict(rows[0]).keys())
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(asdict(r))
    logger.info("Relatório salvo: %s", output_csv)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--photos-root", required=True)
    parser.add_argument("--days", nargs="+", required=True)
    parser.add_argument("--report-dir", default=None, help="Padrão: --photos-root")
    parser.add_argument("--utc-offset", type=float, default=-4.0)
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    report_dir = args.report_dir or args.photos_root
    for day in args.days:
        day_dir = os.path.join(args.photos_root, day)
        if not os.path.isdir(day_dir):
            logging.warning("Pasta do dia não encontrada, pulando: %s", day_dir)
            continue
        logging.info("=== Lendo GPS já gravado: %s ===", day)
        rows = build_report_from_tagged_photos(day_dir, args.utc_offset)
        write_report(rows, os.path.join(report_dir, f"geotag_{day}.csv"))
