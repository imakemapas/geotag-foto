# -*- coding: utf-8 -*-
"""
kmz_export.py
"""

from __future__ import annotations

import logging
import os
from typing import List

import simplekml
from simplekml import Kml

from exif_utils import get_capture_time, read_exif, read_gps_decimal

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = (".jpg", ".jpeg")


def _list_photos_recursive(root_dir: str) -> List[str]:
    seen = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            if os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS:
                full = os.path.join(dirpath, name)
                seen[os.path.normcase(full)] = full
    return sorted(seen.values())


def build_kmz_per_day(photos_root: str, days: List[str], output_dir: str, utc_offset_hours: float = -4.0) -> None:

    os.makedirs(output_dir, exist_ok=True)
    for day in days:
        day_dir = os.path.join(photos_root, day)
        if not os.path.isdir(day_dir):
            logger.warning("Pasta do dia não encontrada, pulando: %s", day_dir)
            continue
        output_kmz = os.path.join(output_dir, f"campo_{day}.kmz")
        logger.info("=== Gerando KMZ do dia: %s ===", day)
        build_kmz(day_dir, output_kmz, utc_offset_hours)


def build_kmz(photos_root: str, output_kmz: str, utc_offset_hours: float = -4.0) -> None:
    photo_paths = _list_photos_recursive(photos_root)
    logger.info("Fotos encontradas em %s: %d", photos_root, len(photo_paths))
    if not photo_paths:
        logger.warning("Nenhuma foto encontrada, KMZ não será criado.")
        return

    kml = Kml()
    kml.document.name = os.path.splitext(os.path.basename(output_kmz))[0]
    kml.document.open = 1

    point_style = simplekml.Style()
    point_style.iconstyle.scale = 0.7
    point_style.labelstyle.scale = 0.8
    kml.document._addstyle(point_style)

    day_folders = {}
    exported, skipped = 0, 0

    for photo_path in photo_paths:
        filename = os.path.basename(photo_path)
        gps = read_gps_decimal(photo_path)
        if gps is None:
            logger.warning("Sem GPS no EXIF, ignorada: %s", filename)
            skipped += 1
            continue
        lat, lon, alt = gps

        exif_dict = read_exif(photo_path)
        capture_time = get_capture_time(exif_dict, utc_offset_hours)
        day_key = capture_time.date() if capture_time else None

        if day_key not in day_folders:
            label = day_key.strftime("%Y-%m-%d") if day_key else "Sem data"
            day_folders[day_key] = kml.newfolder(name=label)
        folder = day_folders[day_key]

        description = (
            f"<h3>{filename}</h3>"
            f"<p><b>Coordenadas:</b> {lat:.6f}, {lon:.6f}</p>"
            f"<p><b>Altitude:</b> {alt:.1f} m</p>"
            f"<p><b>Hora local:</b> {capture_time.strftime('%Y-%m-%d %H:%M:%S') if capture_time else 'desconhecida'}</p>"
        )

        point = folder.newpoint(name=filename, description=description, coords=[(lon, lat, alt)])
        point._placemark.styleurl = f"#{point_style.id}"
        exported += 1

    kml.savekmz(output_kmz)
    logger.info("KMZ criado: %s (%d fotos exportadas, %d ignoradas)", output_kmz, exported, skipped)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--photos-root", required=True, help="Pasta com as fotos já geotaggeadas")
    parser.add_argument("--output", help="Caminho do .kmz de saída (um único KMZ com todos os dias)")
    parser.add_argument("--days", nargs="+", help="Se informado, gera um .kmz por dia (subpastas dentro de --photos-root)")
    parser.add_argument("--output-dir", help="Pasta onde salvar os .kmz por dia (usado junto com --days)")
    parser.add_argument("--utc-offset", type=float, default=-4.0)
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    if args.days:
        build_kmz_per_day(args.photos_root, args.days, args.output_dir or args.photos_root, args.utc_offset)
    else:
        if not args.output:
            raise SystemExit("Informe --output (KMZ único) ou --days (um KMZ por dia).")
        build_kmz(args.photos_root, args.output, args.utc_offset)
