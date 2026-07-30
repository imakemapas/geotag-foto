# -*- coding: utf-8 -*-
"""
geotagger.py
"""

from __future__ import annotations

import bisect
import csv
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from exif_utils import get_capture_time, has_gps, read_exif, write_gps
from gpx_loader import GpsPoint

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = (".jpg", ".jpeg")


@dataclass
class TagResult:
    filename: str
    nome_arquivo: str  # nome do arquivo (ex.: "2A3A8143")
    status: str 
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    capture_time_local: Optional[str] = None
    gpx_point_time_utc: Optional[str] = None
    diff_seconds: Optional[float] = None
    detail: str = ""


def list_photos(photos_dir: str) -> List[str]:
    seen = {}
    for dirpath, _, filenames in os.walk(photos_dir):
        for name in filenames:
            if os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS:
                full = os.path.join(dirpath, name)
                seen[os.path.normcase(full)] = full
    return sorted(seen.values())


def find_closest_point(points: List[GpsPoint], target_time: datetime) -> Tuple[Optional[GpsPoint], float]:
    if not points:
        return None, float("inf")

    times = [p.time for p in points]
    idx = bisect.bisect_left(times, target_time)
    candidates = [i for i in (idx - 1, idx) if 0 <= i < len(points)]
    best_idx = min(candidates, key=lambda i: abs((points[i].time - target_time).total_seconds()))
    diff = abs((points[best_idx].time - target_time).total_seconds())
    return points[best_idx], diff


def geotag_photo(photo_path: str, points: List[GpsPoint], utc_offset_hours: float,
                  max_diff_seconds: float, overwrite_existing: bool = False,
                  display_name: Optional[str] = None) -> TagResult:
    filename = display_name or os.path.basename(photo_path)
    nome_arquivo = os.path.splitext(os.path.basename(photo_path))[0]
    exif_dict = read_exif(photo_path)

    if has_gps(exif_dict) and not overwrite_existing:
        return TagResult(filename, nome_arquivo, "ja_tinha_gps",
                          detail="Foto já possuía GPS; use --force para sobrescrever")

    capture_time = get_capture_time(exif_dict, utc_offset_hours)
    if capture_time is None:
        return TagResult(filename, nome_arquivo, "sem_data", detail="Sem DateTimeOriginal no EXIF")

    point, diff = find_closest_point(points, capture_time)
    if point is None or diff > max_diff_seconds:
        return TagResult(
            filename, nome_arquivo, "sem_ponto_proximo",
            capture_time_local=capture_time.isoformat(),
            diff_seconds=None if point is None else round(diff, 1),
            detail=f"Ponto mais próximo a {diff:.1f}s (limite: {max_diff_seconds}s)",
        )

    try:
        write_gps(photo_path, exif_dict, point.latitude, point.longitude, point.elevation, point.time)
    except Exception as exc:
        return TagResult(filename, nome_arquivo, "erro", detail=str(exc))

    return TagResult(
        filename, nome_arquivo, "ok",
        latitude=point.latitude, longitude=point.longitude, altitude=point.elevation,
        capture_time_local=capture_time.isoformat(),
        gpx_point_time_utc=point.time.isoformat(),
        diff_seconds=round(diff, 1),
    )


def geotag_folder(photos_dir: str, points: List[GpsPoint], utc_offset_hours: float,
                   max_diff_seconds: float, overwrite_existing: bool = False) -> List[TagResult]:
    photo_paths = list_photos(photos_dir)
    logger.info("%s: %d fotos encontradas (em todas as subpastas)", photos_dir, len(photo_paths))

    results = []
    for photo_path in photo_paths:
        display_name = os.path.relpath(photo_path, photos_dir).replace(os.sep, "/")
        result = geotag_photo(photo_path, points, utc_offset_hours, max_diff_seconds,
                               overwrite_existing, display_name=display_name)
        results.append(result)
        _log_result(result)
    return results


def _log_result(result: TagResult) -> None:
    if result.status == "ok":
        logger.info("OK    %s (diferença %.1fs)", result.filename, result.diff_seconds)
    elif result.status == "ja_tinha_gps":
        logger.info("SKIP  %s (já geotaggeada)", result.filename)
    else:
        logger.warning("FALHA %s: %s", result.filename, result.detail)


def write_report(results: List[TagResult], output_csv: str) -> None:
    if not results:
        logger.warning("Nenhum resultado para gravar em %s", output_csv)
        return
    out_dir = os.path.dirname(output_csv)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    fieldnames = list(asdict(results[0]).keys())
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))
    logger.info("Relatório salvo: %s", output_csv)
