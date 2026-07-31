# -*- coding: utf-8 -*-
"""
kmz_export_cfoto.py
Gera um KMZ COM as fotos embutidas (miniatura clicável no popup),
específico para o Google Earth Pro desktop.

Diferente de kmz_export.py (versão enxuta, só texto, pensada para o
Google My Maps — que não exibe imagens embutidas em KMZ de jeito
nenhum), este módulo empacota as fotos dentro do .kmz. Só funciona
corretamente em visualizadores que extraem o KMZ localmente, como o
Google Earth Pro; no My Maps as imagens não aparecem.

Correções aplicadas (mesmas do kmz_export.py):
  1. Caminhos internos do KMZ sempre com posixpath (barra normal) -
     nunca os.path.join, que no Windows gera barra invertida e quebra
     o arquivo.
  2. Fotos duplicadas: a varredura deduplica por caminho normalizado.
  3. Estilo único e compartilhado por todos os pontos — evita estourar
     o limite de estilos por camada (relevante sobretudo se o KMZ for
     aberto em algo além do Earth Pro; no Earth Pro isso também deixa
     o arquivo mais leve e rápido de abrir).
"""

from __future__ import annotations

import logging
import os
import posixpath
import tempfile
import zipfile
from typing import List

import simplekml
from PIL import Image
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


def _resize(src_path: str, dst_path: str, max_dim: int, quality: int) -> None:
    with Image.open(src_path) as img:
        img.thumbnail((max_dim, max_dim))
        img.convert("RGB").save(dst_path, "JPEG", quality=quality, optimize=True)


def build_kmz_cfoto_per_day(photos_root: str, days: List[str], output_dir: str, utc_offset_hours: float = -4.0,
                             max_full_dim: int = 1600, full_quality: int = 82,
                             thumb_size: int = 320, thumb_quality: int = 65) -> None:
    """
    Gera um campo_<dia>_cfoto.kmz por dia (com fotos embutidas), lendo só
    a subpasta daquele dia (ex.: 27_07/R6/..., 27_07/R7/...).
    """
    os.makedirs(output_dir, exist_ok=True)
    for day in days:
        day_dir = os.path.join(photos_root, day)
        if not os.path.isdir(day_dir):
            logger.warning("Pasta do dia não encontrada, pulando: %s", day_dir)
            continue
        output_kmz = os.path.join(output_dir, f"campo_{day}_cfoto.kmz")
        logger.info("=== Gerando KMZ com fotos do dia: %s ===", day)
        build_kmz_cfoto(day_dir, output_kmz, utc_offset_hours, max_full_dim, full_quality, thumb_size, thumb_quality)


def build_kmz_cfoto(photos_root: str, output_kmz: str, utc_offset_hours: float = -4.0,
                     max_full_dim: int = 1600, full_quality: int = 82,
                     thumb_size: int = 320, thumb_quality: int = 65) -> None:
    photo_paths = _list_photos_recursive(photos_root)
    logger.info("Fotos encontradas em %s: %d", photos_root, len(photo_paths))
    if not photo_paths:
        logger.warning("Nenhuma foto encontrada, KMZ não será criado.")
        return

    kml = Kml()
    kml.document.name = os.path.splitext(os.path.basename(output_kmz))[0]
    kml.document.open = 1

    # Estilo único compartilhado por todos os pontos (ver docstring do módulo).
    point_style = simplekml.Style()
    point_style.iconstyle.scale = 0.7
    point_style.labelstyle.scale = 0.8
    kml.document._addstyle(point_style)

    day_folders = {}
    exported, skipped = 0, 0

    with tempfile.TemporaryDirectory() as tmp:
        resized_dir = os.path.join(tmp, "resized")
        thumbs_dir = os.path.join(tmp, "thumbs")
        os.makedirs(resized_dir, exist_ok=True)
        os.makedirs(thumbs_dir, exist_ok=True)

        with zipfile.ZipFile(output_kmz, "w", zipfile.ZIP_DEFLATED) as kmz:
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

                # Nome único dentro do KMZ: evita colisão entre fotos de
                # mesmo nome vindas de pastas de dias diferentes.
                safe_name = f"{day_key}_{filename}" if day_key else filename

                resized_path = os.path.join(resized_dir, safe_name)
                thumb_path = os.path.join(thumbs_dir, safe_name)
                try:
                    _resize(photo_path, resized_path, max_full_dim, full_quality)
                    _resize(photo_path, thumb_path, thumb_size, thumb_quality)
                except Exception as exc:
                    logger.warning("Falha ao processar imagem %s: %s", filename, exc)
                    skipped += 1
                    continue

                # Caminhos SEMPRE com posixpath (barra normal) - nunca
                # os.path.join, senão as miniaturas quebram quando o
                # script roda no Windows.
                thumb_arc = posixpath.join("files", "thumbs", safe_name)
                image_arc = posixpath.join("files", "images", safe_name)

                description = (
                    f"<h3>{filename}</h3>"
                    f"<p><b>Coordenadas:</b> {lat:.6f}, {lon:.6f}</p>"
                    f"<p><b>Altitude:</b> {alt:.1f} m</p>"
                    f"<p><b>Hora local:</b> {capture_time.strftime('%Y-%m-%d %H:%M:%S') if capture_time else 'desconhecida'}</p>"
                    f'<img src="{thumb_arc}" width="300"><br>'
                    f'<a href="{image_arc}">Abrir foto em tamanho original</a>'
                )

                point = folder.newpoint(name=filename, description=description, coords=[(lon, lat, alt)])
                point._placemark.styleurl = f"#{point_style.id}"

                kmz.write(resized_path, image_arc)
                kmz.write(thumb_path, thumb_arc)
                exported += 1

            kmz.writestr("doc.kml", kml.kml().encode("utf-8"))

    logger.info("KMZ criado: %s (%d fotos exportadas, %d ignoradas)", output_kmz, exported, skipped)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--photos-root", required=True, help="Pasta com as fotos já geotaggeadas")
    parser.add_argument("--days", nargs="+", required=True, help="Subpastas de cada dia, ex.: 27_07 28_07 29_07")
    parser.add_argument("--output-dir", help="Pasta onde salvar os campo_<dia>_cfoto.kmz (padrão: --photos-root)")
    parser.add_argument("--utc-offset", type=float, default=-4.0)
    parser.add_argument("--max-full-dim", type=int, default=1600)
    parser.add_argument("--full-quality", type=int, default=82)
    parser.add_argument("--thumb-size", type=int, default=320)
    parser.add_argument("--thumb-quality", type=int, default=65)
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    build_kmz_cfoto_per_day(
        args.photos_root, args.days, args.output_dir or args.photos_root, args.utc_offset,
        args.max_full_dim, args.full_quality, args.thumb_size, args.thumb_quality,
    )
