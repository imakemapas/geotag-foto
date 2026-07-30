# Pipeline de geotag de campo

Reescrita organizada dos scripts `geotag_photos.py`, `kmz_geotag_photos.py`
e `investigar_metadados_photos.py`. Mesma lógica central, mas dividida em
módulos, com deduplicação de verdade e os bugs do KMZ corrigidos.

## Estrutura

| Arquivo | O que faz |
|---|---|
| `gpx_loader.py` | Lê todos os `.gpx` de uma pasta, funde numa única trilha e **remove pontos duplicados** (mesmo timestamp) causados pela sobreposição entre `Current.gpx`, `Current (2).gpx`, arquivos `Auto.gpx`, etc. |
| `exif_utils.py` | Lê/grava data-hora e GPS no EXIF. Usa `piexif.insert()`, que edita só o segmento EXIF **sem recomprimir a foto** (a versão antiga reabria com PIL e salvava de novo, perdendo qualidade a cada execução). |
| `geotagger.py` | Casa cada foto com o ponto GPS mais próximo no tempo (busca binária) e grava o resultado. |
| `geotag_campo.py` | Script principal (CLI) — roda o processo para as pastas de cada dia de campo. |
| `kmz_export.py` | Gera o KMZ com miniaturas, lendo o GPS direto do EXIF das fotos já geotaggeadas. |

## Estrutura de pastas esperada

`--photos-root` é a pasta que contém as subpastas de cada dia, e
`--days` são os nomes dessas subpastas. **Dentro** de cada dia, o script
busca as fotos em qualquer nível de subpasta — não importa se elas estão
soltas ou dentro de `R6/jpg bruto baixa/`, `R7/...`, etc. Exemplo real:

```
geo-foto/
├── gpx/                         ← --gpx-dir
│   ├── Current.gpx
│   └── 2026-07-27 08.54.40 Auto.gpx
├── 27_07/                       ← um dos --days
│   ├── R6/jpg bruto baixa/*.jpg
│   └── R7/jpg bruto baixa/*.jpg
├── 28_07/
│   └── ...
└── 29_07/
    └── ...
```

O resultado é **um único relatório por dia** (`geotag_27_07.csv`, etc.),
juntando tudo que estava em R6 e R7. Como pode haver fotos de mesmo nome
em R6 e R7 (câmeras diferentes), o relatório identifica cada foto pelo
caminho relativo à pasta do dia (ex.: `R6/jpg bruto baixa/R_BK9151.jpg`),
não só pelo nome do arquivo.

## Uso

```bash
python geotag_campo.py \
    --gpx-dir "D:\GP\SOBREVOOS\2026_07_resultados\geo-foto\gpx" \
    --photos-root "D:\GP\SOBREVOOS\2026_07_resultados\geo-foto" \
    --days 27_07 28_07 29_07 \
    --utc-offset -4 \
    --max-diff 30
```

- `--utc-offset`: deslocamento do relógio da câmera em relação ao UTC.
  Nas amostras do projeto (região Humaitá/AM, ~lon -63.9), a hora local
  bate com **UTC-4**, não UTC-3 como estava fixo no script antigo — vale
  conferir contra o nome da trilha no GPS (ex.: "Trajecto Actual: 29 JUL
  2026 08:10" ↔ ponto às 12:10 UTC).
- `--max-diff`: quantos segundos de diferença entre foto e ponto GPS
  ainda são aceitos (padrão 30s).
- `--force`: sobrescreve fotos que já tenham GPS gravado (por padrão elas
  são puladas, o que torna seguro rodar o script de novo sobre a mesma
  pasta).

Isso grava o GPS direto nas fotos (em cada pasta de dia) e gera um
`geotag_<dia>.csv` por dia dentro de `--photos-root`.

Depois de geotaggear, gerar o KMZ (lê o GPS direto do EXIF, não precisa
mais do CSV):

```bash
python kmz_export.py \
    --photos-root "D:\GP\SOBREVOOS\2026_07_resultados\geo-foto" \
    --output "D:\GP\SOBREVOOS\2026_07_resultados\geo-foto\campo.kmz" \
    --utc-offset -4
```

O KMZ organiza as fotos em pastas por data (lidas do EXIF) e cada
Placemark mostra a miniatura clicável com link para a foto em tamanho
original.

## Dependências

```bash
pip install gpxpy piexif pillow simplekml
```
