# -*- coding: utf-8 -*-
"""
track_export.py
Exporta a trilha COMPLETA do GPX (não só onde há fotos) em GeoJSON e
KMZ, um arquivo por dia.

Usa a mesma fusão/deduplicação de gpx_loader.py (junta todos os .gpx da
pasta, remove pontos repetidos entre Current/Auto pelo timestamp real).
O "dia" de cada ponto é a data local (ponto UTC + utc_offset_hours), não
o nome do arquivo GPX.

Se houver um buraco de tempo grande entre dois pontos consecutivos
(ex.: GPS desligado no meio do dia), a trilha é quebrada em vários
trechos (MultiLineString / múltiplas linhas no KMZ) em vez de desenhar
uma linha reta ligando os dois lados do buraco.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta, timezone
from typing import Dict, List

from simplekml import Kml

from gpx_loader import GpsPoint, load_and_merge_gpx

logger = logging.getLogger(__name__)


def _group_by_local_date(points: List[GpsPoint], utc_offset_hours: float) -> Dict[date, List[GpsPoint]]:
    tz = timezone(timedelta(hours=utc_offset_hours))
    buckets: Dict[date, List[GpsPoint]] = {}
    for p in points:
        local_date = p.time.astimezone(tz).date()
        buckets.setdefault(local_date, []).append(p)
    for day_points in buckets.values():
        day_points.sort(key=lambda p: p.time)
    return buckets


def _split_into_segments(points: List[GpsPoint], gap_seconds: float) -> List[List[GpsPoint]]:
    """Quebra a lista em sub-trechos sempre que o intervalo entre pontos consecutivos passa de gap_seconds."""
    if not points:
        return []
    segments: List[List[GpsPoint]] = [[points[0]]]
    for prev, curr in zip(points, points[1:]):
        if (curr.time - prev.time).total_seconds() > gap_seconds:
            segments.append([])
        segments[-1].append(curr)
    return segments


def _write_geojson(segments: List[List[GpsPoint]], day: date, output_path: str) -> None:
    coords_per_segment = [[[p.longitude, p.latitude, p.elevation] for p in seg] for seg in segments if seg]
    geometry = (
        {"type": "LineString", "coordinates": coords_per_segment[0]}
        if len(coords_per_segment) == 1
        else {"type": "MultiLineString", "coordinates": coords_per_segment}
    )
    all_points = [p for seg in segments for p in seg]
    feature = {
        "type": "Feature",
        "properties": {
            "date": day.isoformat(),
            "point_count": len(all_points),
            "segment_count": len(coords_per_segment),
            "start_time_utc": all_points[0].time.isoformat() if all_points else None,
            "end_time_utc": all_points[-1].time.isoformat() if all_points else None,
        },
        "geometry": geometry,
    }
    fc = {"type": "FeatureCollection", "features": [feature]}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
    logger.info("GeoJSON salvo: %s (%d pontos, %d trecho(s))", output_path, len(all_points), len(coords_per_segment))


def _write_kmz(segments: List[List[GpsPoint]], day: date, output_path: str) -> None:
    kml = Kml()
    kml.document.name = f"Trilha {day.isoformat()}"
    kml.document.open = 1

    real_segments = [seg for seg in segments if seg]
    for i, seg in enumerate(real_segments, start=1):
        name = f"Trecho {i}" if len(real_segments) > 1 else "Trilha"
        line = kml.newlinestring(
            name=name,
            coords=[(p.longitude, p.latitude, p.elevation) for p in seg],
        )
        line.altitudemode = "absolute"
        line.extrude = 0
        line.style.linestyle.width = 3
        line.style.linestyle.color = "ff0000ff"  # KML aabbggrr: vermelho opaco

    kml.savekmz(output_path)
    total_points = sum(len(s) for s in real_segments)
    logger.info("KMZ salvo: %s (%d pontos, %d trecho(s))", output_path, total_points, len(real_segments))


def export_daily_tracks(gpx_dir: str, output_dir: str, utc_offset_hours: float = -4.0,
                         gap_seconds: float = 300.0, formats: tuple = ("geojson", "kmz")) -> None:
    """
    Gera um GeoJSON e/ou KMZ por dia com a trilha GPS completa (não só os
    pontos onde há foto). Arquivos nomeados track_<AAAA-MM-DD>.geojson /
    .kmz em output_dir.

    gap_seconds: intervalo (em segundos) acima do qual dois pontos
    consecutivos são considerados trechos diferentes (GPS desligado,
    etc.) em vez de conectados por uma linha reta.
    """
    os.makedirs(output_dir, exist_ok=True)

    points = load_and_merge_gpx(gpx_dir)
    if not points:
        logger.warning("Nenhum ponto GPS encontrado em %s", gpx_dir)
        return

    buckets = _group_by_local_date(points, utc_offset_hours)
    logger.info("Trilha dividida em %d dia(s): %s", len(buckets), sorted(d.isoformat() for d in buckets))

    for day, day_points in sorted(buckets.items()):
        segments = _split_into_segments(day_points, gap_seconds)
        base = os.path.join(output_dir, f"track_{day.isoformat()}")
        if "geojson" in formats:
            _write_geojson(segments, day, base + ".geojson")
        if "kmz" in formats:
            _write_kmz(segments, day, base + ".kmz")


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gpx-dir", required=True, help="Pasta com todos os .gpx da campanha")
    parser.add_argument("--output-dir", required=True, help="Pasta onde salvar os track_<data>.geojson/.kmz")
    parser.add_argument("--utc-offset", type=float, default=-4.0)
    parser.add_argument("--gap-seconds", type=float, default=300.0)
    parser.add_argument("--formats", nargs="+", choices=["geojson", "kmz"], default=["geojson", "kmz"])
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    export_daily_tracks(args.gpx_dir, args.output_dir, args.utc_offset, args.gap_seconds, tuple(args.formats))
