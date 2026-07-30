# -*- coding: utf-8 -*-
"""
rodar_track.py
"""

import logging

from track_export import export_daily_tracks

# ======================= CONFIG (edite aqui) =======================

GPX_DIR = r"D:\GP\SOBREVOOS\2026_07_resultados\geo-foto\gpx"
OUTPUT_DIR = r"D:\GP\SOBREVOOS\2026_07_resultados\geo-foto"

UTC_OFFSET = -4.0  # mesmo valor usado no rodar_geotag.py

GAP_SECONDS = 300.0

FORMATS = ("geojson", "kmz")

# =====================================================================


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    export_daily_tracks(
        gpx_dir=GPX_DIR,
        output_dir=OUTPUT_DIR,
        utc_offset_hours=UTC_OFFSET,
        gap_seconds=GAP_SECONDS,
        formats=FORMATS,
    )


if __name__ == "__main__":
    main()
