# -*- coding: utf-8 -*-
"""
exif_utils.py
Leitura e escrita de metadados EXIF (data/hora e GPS) em fotos JPEG.

Usa piexif.insert() para gravar o GPS, que edita apenas o segmento EXIF
do arquivo sem recodificar a imagem — ao contrário de abrir com PIL e
salvar de novo, isso NÃO perde qualidade nem recomprime a foto.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import piexif
from piexif import ExifIFD, GPSIFD, ImageIFD

_DATETIME_TAGS = (ExifIFD.DateTimeOriginal, ExifIFD.DateTimeDigitized, ImageIFD.DateTime)


def read_exif(photo_path: str) -> dict:
    """Lê o dicionário EXIF de uma foto. Nunca lança exceção: devolve um dict vazio se falhar."""
    try:
        return piexif.load(photo_path)
    except Exception:
        return {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}


def get_capture_time(exif_dict: dict, utc_offset_hours: float) -> Optional[datetime]:
    """
    Lê a data/hora de captura gravada pela câmera (hora local, sem timezone
    no EXIF) e devolve um datetime timezone-aware, assumindo o deslocamento
    UTC informado (ex.: -4.0 para horário do Amazonas/Rondônia).
    """
    tz = timezone(timedelta(hours=utc_offset_hours))
    for tag in _DATETIME_TAGS:
        for ifd in ("Exif", "0th"):
            raw = exif_dict.get(ifd, {}).get(tag)
            if not raw:
                continue
            try:
                dt_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S").replace(tzinfo=tz)
            except ValueError:
                continue
    return None


def has_gps(exif_dict: dict) -> bool:
    gps = exif_dict.get("GPS") or {}
    return GPSIFD.GPSLatitude in gps


def _decimal_to_dms(value: float) -> Tuple[tuple, tuple, tuple]:
    value = abs(value)
    degrees = int(value)
    minutes_full = (value - degrees) * 60
    minutes = int(minutes_full)
    seconds = round((minutes_full - minutes) * 60, 4)
    return (degrees, 1), (minutes, 1), (int(seconds * 10000), 10000)


def write_gps(photo_path: str, exif_dict: dict, latitude: float, longitude: float,
              elevation: float, point_time_utc: datetime) -> None:
    """Grava as coordenadas GPS no EXIF e salva no arquivo, sem recomprimir a imagem."""
    exif_dict["GPS"] = {
        GPSIFD.GPSVersionID: (2, 3, 0, 0),
        GPSIFD.GPSLatitudeRef: "N" if latitude >= 0 else "S",
        GPSIFD.GPSLatitude: _decimal_to_dms(latitude),
        GPSIFD.GPSLongitudeRef: "E" if longitude >= 0 else "W",
        GPSIFD.GPSLongitude: _decimal_to_dms(longitude),
        GPSIFD.GPSAltitudeRef: 0 if elevation >= 0 else 1,
        GPSIFD.GPSAltitude: (int(abs(elevation) * 100), 100),
        GPSIFD.GPSDateStamp: point_time_utc.strftime("%Y:%m:%d"),
        GPSIFD.GPSTimeStamp: (
            (point_time_utc.hour, 1),
            (point_time_utc.minute, 1),
            (point_time_utc.second, 1),
        ),
    }
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, photo_path)


def read_gps_decimal(photo_path: str) -> Optional[Tuple[float, float, float]]:
    """Devolve (lat, lon, alt) em graus decimais/metros, ou None se a foto não tiver GPS."""
    exif_dict = read_exif(photo_path)
    gps = exif_dict.get("GPS", {})
    if GPSIFD.GPSLatitude not in gps:
        return None

    def to_decimal(dms, ref) -> float:
        d = dms[0][0] / dms[0][1]
        m = dms[1][0] / dms[1][1]
        s = dms[2][0] / dms[2][1]
        sign = -1 if ref in (b"S", b"W", "S", "W") else 1
        return sign * (d + m / 60 + s / 3600)

    lat = to_decimal(gps[GPSIFD.GPSLatitude], gps.get(GPSIFD.GPSLatitudeRef, b"N"))
    lon = to_decimal(gps[GPSIFD.GPSLongitude], gps.get(GPSIFD.GPSLongitudeRef, b"E"))
    alt_num, alt_den = gps.get(GPSIFD.GPSAltitude, (0, 1))
    alt = alt_num / alt_den if alt_den else 0.0
    if gps.get(GPSIFD.GPSAltitudeRef, 0) == 1:
        alt = -alt
    return lat, lon, alt
