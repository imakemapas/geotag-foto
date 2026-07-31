# Geotag de campo

Geotaggeia fotos de campo (várias câmeras, vários dias) usando GPX do GPS, e exporta os resultados em CSV, KMZ e GeoJSON.

## Instalação

```bash
pip install gpxpy piexif pillow simplekml
```

## Estrutura de pastas esperada

```
geo-foto/
├── gpx/                          ← todos os .gpx
│   ├── *.gpx

├── 27_07/                        ← um dia de campo
│   ├── R6/*.jpg                  ← câmera 1
│   └── R7/*.jpg                  ← câmera 2
├── 28_07/
└── 29_07/
```

## Fluxo de uso

Todos os scripts `rodar_*.py` são feitos para rodar direto na IDE

| Ordem | Script | O que faz | Gera |
|---|---|---|---|
| 1 | `rodar_geotag.py` | Grava o GPS no EXIF de cada foto, casando com o ponto GPX mais próximo no tempo | `geotag_<dia>.csv` |
| 2 | `rodar_regerar_csv.py` | *(opcional)* Reconstrói o CSV lendo o GPS já gravado, sem reprocessar fotos | `geotag_<dia>.csv` |
| 3 | `rodar_kmz.py` | KMZ enxuto (só texto) — para **Google My Maps** | `campo_<dia>.kmz` |
| 4 | `rodar_kmz_cfoto.py` | KMZ com miniatura de cada foto — para **Google Earth Pro** | `campo_<dia>_cfoto.kmz` |
| 5 | `rodar_track.py` | Trilha GPS completa do dia (não só onde há foto) | `track_<data>.geojson` / `.kmz` |

## Parâmetros importantes

- **`UTC_OFFSET`**: deslocamento do relógio da câmera em relação ao  UTC. Confira contra o horário do próprio GPS.
- **`MAX_DIFF_SECONDS`**: diferença máxima aceita entre a hora da foto e o ponto GPS mais próximo (padrão 30s).
- **`FORCE_OVERWRITE`**: `True` sobrescreve o GPS de fotos já geotaggeadas (padrão `False`).

## Módulos internos

| Arquivo | Função |
|---|---|
| `gpx_loader.py` | Funde todos os `.gpx` numa trilha única, removendo pontos duplicados pelo timestamp real |
| `exif_utils.py` | Leitura/escrita de data-hora e GPS no EXIF, sem recomprimir a foto |
| `geotagger.py` | Casa cada foto com o ponto GPS mais próximo e grava o resultado |
| `report_builder.py` | Lê o GPS já gravado nas fotos para reconstruir o CSV |
| `kmz_export.py` | Monta o KMZ enxuto (texto) |
| `kmz_export_cfoto.py` | Monta o KMZ com fotos embutidas |
| `track_export.py` | Monta a trilha GPS completa em GeoJSON/KMZ |
| `geotag_campo.py` | Versão do passo 1 para rodar por linha de comando (`--gpx-dir`, `--photos-root`, `--days`, ...) em vez de editar CONFIG |

## Colunas do CSV

`filename` (caminho relativo à pasta do dia, ex.: `R6/jpg bruto
baixa/R_BK9151.jpg`) · `nome_arquivo` (só o nome, sem pasta nem
extensão) · `status` (`ok` / `ja_tinha_gps` / `sem_data` /
`sem_ponto_proximo` / `erro`) · `latitude` · `longitude` · `altitude` ·
`capture_time_local` · `gpx_point_time_utc` · `diff_seconds` · `detail`