# -*- coding: utf-8 -*-
"""
gpx_loader.py
"""

from __future__ import annotations

import glob
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List

import gpxpy

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpsPoint:
    time: datetime          # sempre UTC (aware)
    latitude: float
    longitude: float
    elevation: float
    source_file: str


def _iter_points_from_file(gpx_path: str) -> Iterable[GpsPoint]:
    with open(gpx_path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    filename = os.path.basename(gpx_path)
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if point.time is None:
                    continue
                t = point.time
                t = t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)
                yield GpsPoint(
                    time=t,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    elevation=point.elevation if point.elevation is not None else 0.0,
                    source_file=filename,
                )


def load_and_merge_gpx(gpx_folder: str) -> List[GpsPoint]:
    gpx_files = sorted(glob.glob(os.path.join(gpx_folder, "*.gpx")))
    if not gpx_files:
        raise FileNotFoundError(f"Nenhum arquivo .gpx encontrado em: {gpx_folder}")

    all_points: List[GpsPoint] = []
    for gpx_file in gpx_files:
        try:
            points = list(_iter_points_from_file(gpx_file))
        except Exception as exc:
            logger.warning("Falha ao ler %s: %s", os.path.basename(gpx_file), exc)
            continue
        logger.info("%s: %d pontos", os.path.basename(gpx_file), len(points))
        all_points.extend(points)

    merged = _deduplicate(all_points)
    logger.info(
        "Trilha combinada: %d pontos brutos de %d arquivos -> %d pontos após remover duplicatas",
        len(all_points), len(gpx_files), len(merged),
    )
    return merged


def _deduplicate(points: List[GpsPoint]) -> List[GpsPoint]:
    """
    Remove pontos duplicados
    """
    best_by_time = {}
    for p in points:
        current = best_by_time.get(p.time)
        if current is None or (current.elevation == 0.0 and p.elevation != 0.0):
            best_by_time[p.time] = p

    return sorted(best_by_time.values(), key=lambda p: p.time)
