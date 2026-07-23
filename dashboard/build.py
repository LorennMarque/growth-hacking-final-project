"""Genera dashboard/index.html autónomo a partir del CSV de encuestas."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR.parent / "data" / "raw" / "respuestas_encuestas.csv"
OUT_HTML = BASE_DIR / "index.html"
CSS_PATH = BASE_DIR / "static" / "css" / "app.css"
JS_PATH = BASE_DIR / "static" / "js" / "app.js"

COL_USER = "Código único de usuario"
COL_MOTIVATION = "Motivación para registrarse"
COL_CHANNEL = "Cómo se enteró de la plataforma"
COL_EXPLORED = "Exploró el catálogo"
COL_WATCHED = "Ha visto contenido"
COL_REASON = "Razón por no ver contenido"
COL_CONTENT = "Tipo de contenido de interés"
COL_PAYMENT = "Modalidad de pago preferida"
COL_IMPROVE = "Qué mejorar en la plataforma"
COL_AGE = "Edad"
COL_COUNTRY = "País o región"
COL_FAMILIARITY = "Nivel de familiaridad con streaming"

CATEGORICAL = [
    COL_MOTIVATION,
    COL_CHANNEL,
    COL_EXPLORED,
    COL_WATCHED,
    COL_REASON,
    COL_CONTENT,
    COL_PAYMENT,
    COL_IMPROVE,
    COL_AGE,
    COL_COUNTRY,
    COL_FAMILIARITY,
]

AGE_ORDER = ["18-24 años", "25-34 años", "35-44 años", "45+ años"]
FAMILIARITY_ORDER = ["Baja", "Media", "Alta"]
YES_NO_ORDER = ["Sí", "No"]

SHORT_LABELS = {
    COL_MOTIVATION: "Motivación",
    COL_CHANNEL: "Canal de adquisición",
    COL_EXPLORED: "Exploró catálogo",
    COL_WATCHED: "Vio contenido",
    COL_REASON: "Barrera (no vio)",
    COL_CONTENT: "Contenido de interés",
    COL_PAYMENT: "Modalidad de pago",
    COL_IMPROVE: "Qué mejorar",
    COL_AGE: "Edad",
    COL_COUNTRY: "País",
    COL_FAMILIARITY: "Familiaridad streaming",
}


def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    for col in CATEGORICAL:
        df[col] = df[col].fillna("").astype(str).str.strip()
        df.loc[df[col] == "", col] = "Sin respuesta"
    return df


def counts(series: pd.Series, order: list[str] | None = None) -> dict:
    counter = Counter(series.tolist())
    if order:
        labels = [x for x in order if x in counter] + [
            k for k in counter if k not in order
        ]
    else:
        labels = [k for k, _ in counter.most_common()]
    return {
        "labels": labels,
        "values": [counter[k] for k in labels],
        "pct": [round(100 * counter[k] / len(series), 1) for k in labels],
    }


def crosstab(df: pd.DataFrame, row: str, col: str) -> dict:
    table = pd.crosstab(df[row], df[col])
    return {
        "rows": table.index.tolist(),
        "cols": table.columns.tolist(),
        "matrix": table.values.tolist(),
        "row_totals": table.sum(axis=1).tolist(),
        "col_totals": table.sum(axis=0).tolist(),
    }


def compare_by_watched(df: pd.DataFrame, dim: str) -> dict:
    order = None
    if dim == COL_AGE:
        order = AGE_ORDER
    elif dim == COL_FAMILIARITY:
        order = FAMILIARITY_ORDER
    elif dim == COL_EXPLORED:
        order = YES_NO_ORDER

    watched = df[df[COL_WATCHED] == "Sí"]
    not_watched = df[df[COL_WATCHED] == "No"]

    series_w = watched[dim]
    series_n = not_watched[dim]
    if dim == COL_REASON:
        series_w = series_w[series_w != "Sin respuesta"]
        series_n = series_n[series_n != "Sin respuesta"]

    cw = Counter(series_w.tolist())
    cn = Counter(series_n.tolist())
    labels = list(dict.fromkeys([*(order or []), *cw.keys(), *cn.keys()]))
    labels = [k for k in labels if k in cw or k in cn]
    if not order:
        labels = sorted(labels, key=lambda k: -(cw.get(k, 0) + cn.get(k, 0)))

    n_w = max(len(series_w), 1)
    n_n = max(len(series_n), 1)
    return {
        "label": SHORT_LABELS[dim],
        "labels": labels,
        "watched": [cw.get(k, 0) for k in labels],
        "not_watched": [cn.get(k, 0) for k in labels],
        "watched_pct": [round(100 * cw.get(k, 0) / n_w, 1) for k in labels],
        "not_watched_pct": [round(100 * cn.get(k, 0) / n_n, 1) for k in labels],
        "n_watched": int(len(series_w)),
        "n_not_watched": int(len(series_n)),
    }


def conversion_by(df: pd.DataFrame, dim: str) -> dict:
    grouped = (
        df.groupby(dim, dropna=False)
        .agg(
            n=(COL_USER, "count"),
            explored=(COL_EXPLORED, lambda s: (s == "Sí").sum()),
            watched=(COL_WATCHED, lambda s: (s == "Sí").sum()),
        )
        .reset_index()
    )
    grouped["explore_rate"] = (100 * grouped["explored"] / grouped["n"]).round(1)
    grouped["watch_rate"] = (100 * grouped["watched"] / grouped["n"]).round(1)
    grouped = grouped.sort_values("watch_rate", ascending=False)
    return {
        "labels": grouped[dim].tolist(),
        "n": grouped["n"].tolist(),
        "explore_rate": grouped["explore_rate"].tolist(),
        "watch_rate": grouped["watch_rate"].tolist(),
    }


def build_insights(df: pd.DataFrame) -> list[dict]:
    n = len(df)
    explored = int((df[COL_EXPLORED] == "Sí").sum())
    watched = int((df[COL_WATCHED] == "Sí").sum())
    non_watchers = df[df[COL_WATCHED] == "No"]
    top_motivation = df[COL_MOTIVATION].value_counts().index[0]
    top_motivation_n = int(df[COL_MOTIVATION].value_counts().iloc[0])
    top_barrier = non_watchers[COL_REASON].value_counts()
    top_barrier = top_barrier[top_barrier.index != "Sin respuesta"]
    barrier_label = top_barrier.index[0] if len(top_barrier) else "—"
    barrier_n = int(top_barrier.iloc[0]) if len(top_barrier) else 0
    top_channel = df[COL_CHANNEL].value_counts().index[0]
    channel_conv = conversion_by(df, COL_CHANNEL)
    best_channel = channel_conv["labels"][0]
    best_channel_rate = channel_conv["watch_rate"][0]
    pay = df[COL_PAYMENT].value_counts()
    improve = df[COL_IMPROVE].value_counts()

    return [
        {
            "title": "Embudo de activación",
            "text": (
                f"De {n} registrados, {explored} exploraron el catálogo "
                f"({100 * explored / n:.0f}%) y {watched} vieron contenido "
                f"({100 * watched / n:.0f}%). Hay una fuga relevante entre "
                f"exploración y visionado."
            ),
        },
        {
            "title": "Motivo dominante",
            "text": (
                f"«{top_motivation}» concentra {top_motivation_n} respuestas "
                f"({100 * top_motivation_n / n:.0f}%). El registro se mueve "
                f"más por valor local/promo que por un único driver."
            ),
        },
        {
            "title": "Principal fricción",
            "text": (
                f"Entre quienes no vieron contenido, la barrera #1 es "
                f"«{barrier_label}» ({barrier_n} casos). El problema parece "
                f"más de fit de catálogo/UX que de falta de tiempo."
            ),
        },
        {
            "title": "Canal con mejor conversión",
            "text": (
                f"El canal más frecuente es «{top_channel}», pero el mejor "
                f"watch-rate es «{best_channel}» ({best_channel_rate}%). "
                f"Priorizar calidad de canal, no solo volumen."
            ),
        },
        {
            "title": "Monetización",
            "text": (
                f"La modalidad preferida es «{pay.index[0]}» "
                f"({pay.iloc[0]} votos). No hay consenso fuerte: conviene "
                f"testear flexibilidad (pago por ver + híbridos)."
            ),
        },
        {
            "title": "Prioridad de producto",
            "text": (
                f"Lo más pedido para mejorar: «{improve.index[0]}» "
                f"({improve.iloc[0]} menciones), seguido de "
                f"«{improve.index[1]}»."
            ),
        },
    ]


def build_payload() -> dict:
    df = load_data()
    n = len(df)
    explored = int((df[COL_EXPLORED] == "Sí").sum())
    watched = int((df[COL_WATCHED] == "Sí").sum())
    non_watchers = df[df[COL_WATCHED] == "No"]

    distributions = {}
    for col in CATEGORICAL:
        order = None
        if col == COL_AGE:
            order = AGE_ORDER
        elif col == COL_FAMILIARITY:
            order = FAMILIARITY_ORDER
        elif col in (COL_EXPLORED, COL_WATCHED):
            order = YES_NO_ORDER
        series = df[col]
        if col == COL_REASON:
            series = non_watchers[COL_REASON]
            series = series[series != "Sin respuesta"]
        distributions[col] = {
            "label": SHORT_LABELS[col],
            **counts(series, order),
        }

    return {
        "meta": {
            "n": n,
            "source": str(CSV_PATH.name),
        },
        "kpis": [
            {"label": "Respuestas", "value": str(n), "hint": "usuarios encuestados"},
            {
                "label": "Exploró catálogo",
                "value": f"{100 * explored / n:.0f}%",
                "hint": f"{explored} de {n}",
            },
            {
                "label": "Vio contenido",
                "value": f"{100 * watched / n:.0f}%",
                "hint": f"{watched} de {n}",
            },
            {
                "label": "Conversión exploración→visión",
                "value": f"{100 * watched / explored:.0f}%" if explored else "—",
                "hint": f"{watched} de {explored} exploradores",
            },
        ],
        "insights": build_insights(df),
        "funnel": {
            "labels": ["Registrados", "Exploró catálogo", "Vio contenido"],
            "values": [n, explored, watched],
        },
        "distributions": distributions,
        "conversion": {
            "by_motivation": conversion_by(df, COL_MOTIVATION),
            "by_channel": conversion_by(df, COL_CHANNEL),
            "by_age": conversion_by(df, COL_AGE),
            "by_familiarity": conversion_by(df, COL_FAMILIARITY),
            "by_content": conversion_by(df, COL_CONTENT),
        },
        "cross": {
            "motivation_x_watched": crosstab(df, COL_MOTIVATION, COL_WATCHED),
            "channel_x_watched": crosstab(df, COL_CHANNEL, COL_WATCHED),
            "age_x_content": crosstab(df, COL_AGE, COL_CONTENT),
            "payment_x_age": crosstab(df, COL_PAYMENT, COL_AGE),
        },
        "explore_by_watched": {
            "by_motivation": compare_by_watched(df, COL_MOTIVATION),
            "by_channel": compare_by_watched(df, COL_CHANNEL),
            "by_explored": compare_by_watched(df, COL_EXPLORED),
            "by_reason": compare_by_watched(df, COL_REASON),
            "by_content": compare_by_watched(df, COL_CONTENT),
            "by_payment": compare_by_watched(df, COL_PAYMENT),
            "by_improve": compare_by_watched(df, COL_IMPROVE),
            "by_age": compare_by_watched(df, COL_AGE),
            "by_country": compare_by_watched(df, COL_COUNTRY),
            "by_familiarity": compare_by_watched(df, COL_FAMILIARITY),
        },
        "labels": SHORT_LABELS,
    }


HTML_SHELL = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LatamTV · Exploración de encuestas</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/apexcharts@3.54.1"></script>
  <style>
__CSS__
  </style>
</head>
<body>
  <div class="page">
    <header class="hero">
      <p class="brand">LatamTV</p>
      <h1>Exploración de respuestas</h1>
      <p class="lede">
        Tablero analítico de la encuesta de onboarding: motivos, embudo de
        activación, fricciones y preferencias de producto.
      </p>
      <p class="meta" id="meta"></p>
    </header>

    <section class="kpis" id="kpis" aria-label="Indicadores clave"></section>

    <section class="insights" aria-labelledby="insights-title">
      <div class="section-head">
        <h2 id="insights-title">Lecturas clave</h2>
        <p>Síntesis del científico de datos a partir de las 11 variables.</p>
      </div>
      <div class="insight-grid" id="insights"></div>
    </section>

    <section class="panel" aria-labelledby="funnel-title">
      <div class="section-head">
        <h2 id="funnel-title">Embudo de activación</h2>
        <p>Del registro al visionado: dónde se pierde al usuario.</p>
      </div>
      <div id="chart-funnel" class="chart"></div>
    </section>

    <section class="panel" aria-labelledby="motives-title">
      <div class="section-head">
        <h2 id="motives-title">Motivos y adquisición</h2>
        <p>Por qué se registran y cómo llegan a la plataforma.</p>
      </div>
      <div class="grid-2">
        <div>
          <h3>Motivación para registrarse</h3>
          <div id="chart-motivation" class="chart"></div>
        </div>
        <div>
          <h3>Canal de adquisición</h3>
          <div id="chart-channel" class="chart"></div>
        </div>
      </div>
    </section>

    <section class="panel" aria-labelledby="barriers-title">
      <div class="section-head">
        <h2 id="barriers-title">Barreras y contenido</h2>
        <p>Por qué no ven contenido y qué tipo de título buscan.</p>
      </div>
      <div class="grid-2">
        <div>
          <h3>Razón por no ver (solo no-watchers)</h3>
          <div id="chart-reason" class="chart"></div>
        </div>
        <div>
          <h3>Tipo de contenido de interés</h3>
          <div id="chart-content" class="chart"></div>
        </div>
      </div>
    </section>

    <section class="panel" aria-labelledby="product-title">
      <div class="section-head">
        <h2 id="product-title">Producto y monetización</h2>
        <p>Preferencia de pago y pedidos de mejora.</p>
      </div>
      <div class="grid-2">
        <div>
          <h3>Modalidad de pago preferida</h3>
          <div id="chart-payment" class="chart"></div>
        </div>
        <div>
          <h3>Qué mejorar en la plataforma</h3>
          <div id="chart-improve" class="chart"></div>
        </div>
      </div>
    </section>

    <section class="panel" aria-labelledby="demo-title">
      <div class="section-head">
        <h2 id="demo-title">Demografía</h2>
        <p>Perfil de quienes respondieron.</p>
      </div>
      <div class="grid-3">
        <div>
          <h3>Edad</h3>
          <div id="chart-age" class="chart chart-sm"></div>
        </div>
        <div>
          <h3>País</h3>
          <div id="chart-country" class="chart chart-sm"></div>
        </div>
        <div>
          <h3>Familiaridad con streaming</h3>
          <div id="chart-familiarity" class="chart chart-sm"></div>
        </div>
      </div>
    </section>

    <section class="panel" aria-labelledby="conv-title">
      <div class="section-head">
        <h2 id="conv-title">Conversión por segmento</h2>
        <p>% que exploró y % que vio contenido, por dimensión.</p>
      </div>
      <div class="tabs" role="tablist" id="conversion-tabs">
        <button class="tab is-active" data-conv="by_motivation" type="button">Motivación</button>
        <button class="tab" data-conv="by_channel" type="button">Canal</button>
        <button class="tab" data-conv="by_age" type="button">Edad</button>
        <button class="tab" data-conv="by_familiarity" type="button">Familiaridad</button>
        <button class="tab" data-conv="by_content" type="button">Contenido</button>
      </div>
      <div id="chart-conversion" class="chart chart-lg"></div>
    </section>

    <section class="panel" aria-labelledby="cross-title">
      <div class="section-head">
        <h2 id="cross-title">Cruces</h2>
        <p>Relaciones entre variables para hipótesis de growth.</p>
      </div>
      <div class="grid-2">
        <div>
          <h3>Motivación × vio contenido</h3>
          <div id="chart-cross-motivation" class="chart"></div>
        </div>
        <div>
          <h3>Canal × vio contenido</h3>
          <div id="chart-cross-channel" class="chart"></div>
        </div>
        <div>
          <h3>Edad × tipo de contenido</h3>
          <div id="chart-cross-age-content" class="chart chart-lg"></div>
        </div>
        <div>
          <h3>Pago × edad</h3>
          <div id="chart-cross-payment-age" class="chart chart-lg"></div>
        </div>
      </div>
    </section>

    <section class="panel" aria-labelledby="explore-title">
      <div class="section-head">
        <h2 id="explore-title">Explorar según visionado</h2>
        <p>
          Compará cada variable entre quienes vieron y quienes no vieron
          contenido (barras agrupadas, % dentro de cada grupo).
        </p>
      </div>
      <div class="tabs" role="tablist" id="explore-tabs">
        <button class="tab is-active" data-explore="by_motivation" type="button">Motivación</button>
        <button class="tab" data-explore="by_channel" type="button">Canal</button>
        <button class="tab" data-explore="by_explored" type="button">Exploró catálogo</button>
        <button class="tab" data-explore="by_reason" type="button">Barrera</button>
        <button class="tab" data-explore="by_content" type="button">Contenido</button>
        <button class="tab" data-explore="by_payment" type="button">Pago</button>
        <button class="tab" data-explore="by_improve" type="button">Mejoras</button>
        <button class="tab" data-explore="by_age" type="button">Edad</button>
        <button class="tab" data-explore="by_country" type="button">País</button>
        <button class="tab" data-explore="by_familiarity" type="button">Familiaridad</button>
      </div>
      <p class="meta" id="explore-meta"></p>
      <div id="chart-explore" class="chart chart-lg"></div>
    </section>

    <footer class="footer">
      <p>Fuente: <code>respuestas_encuestas.csv</code> · ApexCharts</p>
    </footer>
  </div>

  <script>
window.DASHBOARD_DATA = __DATA__;
  </script>
  <script>
__JS__
  </script>
</body>
</html>
"""


def build_html() -> Path:
    css = CSS_PATH.read_text(encoding="utf-8")
    js = JS_PATH.read_text(encoding="utf-8")
    data_json = json.dumps(build_payload(), ensure_ascii=False)
    html = (
        HTML_SHELL.replace("__CSS__", css)
        .replace("__JS__", js)
        .replace("__DATA__", data_json)
    )
    OUT_HTML.write_text(html, encoding="utf-8")
    return OUT_HTML


if __name__ == "__main__":
    path = build_html()
    print(f"Generado: {path}")
