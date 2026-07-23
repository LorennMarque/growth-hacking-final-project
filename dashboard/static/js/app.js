const PALETTE = ["#172186", "#2f3aad", "#4a55c4", "#6b74d4", "#8e95e0", "#b0b5eb", "#0f1660", "#3d48b8"];

const COL = {
  motivation: "Motivación para registrarse",
  channel: "Cómo se enteró de la plataforma",
  reason: "Razón por no ver contenido",
  content: "Tipo de contenido de interés",
  payment: "Modalidad de pago preferida",
  improve: "Qué mejorar en la plataforma",
  age: "Edad",
  country: "País o región",
  familiarity: "Nivel de familiaridad con streaming",
};

const baseChart = {
  chart: {
    fontFamily: "Instrument Sans, system-ui, sans-serif",
    toolbar: { show: false },
    animations: {
      enabled: true,
      easing: "easeinout",
      speed: 650,
    },
  },
  dataLabels: { enabled: false },
  grid: {
    borderColor: "#e6e7ec",
    strokeDashArray: 3,
  },
  tooltip: {
    theme: "light",
    style: { fontSize: "13px" },
  },
  legend: {
    fontSize: "12px",
    labels: { colors: "#5a5d6b" },
  },
};

function truncate(label, max = 28) {
  return label.length > max ? `${label.slice(0, max - 1)}…` : label;
}

function barHorizontal(el, dist, color = PALETTE[0]) {
  const options = {
    ...baseChart,
    chart: { ...baseChart.chart, type: "bar", height: 300 },
    series: [{ name: "Respuestas", data: dist.values }],
    plotOptions: {
      bar: {
        horizontal: true,
        borderRadius: 0,
        barHeight: "62%",
      },
    },
    colors: [color],
    xaxis: {
      categories: dist.labels.map((l) => truncate(l)),
      labels: { style: { colors: "#5a5d6b", fontSize: "12px" } },
    },
    yaxis: {
      labels: { style: { colors: "#12131a", fontSize: "12px" }, maxWidth: 180 },
    },
    tooltip: {
      ...baseChart.tooltip,
      y: {
        formatter: (val, opts) => {
          const i = opts.dataPointIndex;
          return `${val} (${dist.pct[i]}%)`;
        },
      },
    },
  };
  new ApexCharts(document.querySelector(el), options).render();
}

function donut(el, dist, height = 280) {
  const options = {
    ...baseChart,
    chart: { ...baseChart.chart, type: "donut", height },
    series: dist.values,
    labels: dist.labels,
    colors: PALETTE,
    stroke: { width: 2, colors: ["#ffffff"] },
    plotOptions: {
      pie: {
        donut: {
          size: "68%",
          labels: {
            show: true,
            name: { fontSize: "12px", color: "#5a5d6b" },
            value: {
              fontSize: "22px",
              fontFamily: "Newsreader, Georgia, serif",
              fontWeight: 600,
              color: "#12131a",
            },
            total: {
              show: true,
              label: "Total",
              color: "#5a5d6b",
              formatter: () => dist.values.reduce((a, b) => a + b, 0),
            },
          },
        },
      },
    },
    legend: {
      ...baseChart.legend,
      position: "bottom",
      fontSize: "11px",
    },
  };
  new ApexCharts(document.querySelector(el), options).render();
}

function funnel(el, data) {
  const options = {
    ...baseChart,
    chart: { ...baseChart.chart, type: "bar", height: 280 },
    series: [{ name: "Usuarios", data: data.values }],
    plotOptions: {
      bar: {
        borderRadius: 0,
        columnWidth: "42%",
        distributed: true,
        dataLabels: { position: "top" },
      },
    },
    colors: ["#172186", "#4a55c4", "#8e95e0"],
    dataLabels: {
      enabled: true,
      offsetY: -18,
      style: {
        fontSize: "13px",
        fontWeight: 600,
        colors: ["#12131a"],
      },
      formatter: (val, opts) => {
        const base = data.values[0] || 1;
        const pct = Math.round((100 * val) / base);
        return `${val} · ${pct}%`;
      },
    },
    legend: { show: false },
    xaxis: {
      categories: data.labels,
      labels: { style: { colors: "#12131a", fontSize: "13px" } },
    },
    yaxis: {
      labels: { style: { colors: "#5a5d6b", fontSize: "12px" } },
    },
  };
  new ApexCharts(document.querySelector(el), options).render();
}

let conversionChart = null;

function renderConversion(key, conversion) {
  const data = conversion[key];
  const options = {
    ...baseChart,
    chart: { ...baseChart.chart, type: "bar", height: 380 },
    series: [
      { name: "% exploró", data: data.explore_rate },
      { name: "% vio contenido", data: data.watch_rate },
    ],
    plotOptions: {
      bar: {
        horizontal: true,
        borderRadius: 0,
        barHeight: "70%",
      },
    },
    colors: ["#8e95e0", "#172186"],
    xaxis: {
      categories: data.labels.map((l) => truncate(l, 32)),
      max: 100,
      labels: {
        style: { colors: "#5a5d6b", fontSize: "12px" },
        formatter: (v) => `${v}%`,
      },
    },
    yaxis: {
      labels: { style: { colors: "#12131a", fontSize: "12px" }, maxWidth: 200 },
    },
    tooltip: {
      ...baseChart.tooltip,
      y: {
        formatter: (val, opts) => {
          const n = data.n[opts.dataPointIndex];
          return `${val}% (n=${n})`;
        },
      },
    },
  };

  if (conversionChart) {
    conversionChart.updateOptions(options, true, true);
  } else {
    conversionChart = new ApexCharts(document.querySelector("#chart-conversion"), options);
    conversionChart.render();
  }
}

function dodgedBars(el, cross, height = 320) {
  const series = cross.cols.map((col, colIdx) => ({
    name: col,
    data: cross.matrix.map((row) => row[colIdx]),
  }));

  const options = {
    ...baseChart,
    chart: { ...baseChart.chart, type: "bar", stacked: false, height },
    series,
    plotOptions: {
      bar: {
        horizontal: true,
        borderRadius: 0,
        barHeight: "70%",
      },
    },
    colors: PALETTE,
    xaxis: {
      categories: cross.rows.map((l) => truncate(l, 30)),
      labels: { style: { colors: "#5a5d6b", fontSize: "12px" } },
    },
    yaxis: {
      labels: { style: { colors: "#12131a", fontSize: "12px" }, maxWidth: 180 },
    },
  };
  new ApexCharts(document.querySelector(el), options).render();
}

let exploreChart = null;

function renderExplore(key, explore) {
  const data = explore[key];
  const meta = document.getElementById("explore-meta");
  meta.textContent = `${data.label} · vio contenido n=${data.n_watched} · no vio n=${data.n_not_watched}`;

  const options = {
    ...baseChart,
    chart: { ...baseChart.chart, type: "bar", stacked: false, height: 400 },
    series: [
      { name: "Vio contenido (%)", data: data.watched_pct },
      { name: "No vio contenido (%)", data: data.not_watched_pct },
    ],
    plotOptions: {
      bar: {
        horizontal: true,
        borderRadius: 0,
        barHeight: "70%",
      },
    },
    colors: ["#172186", "#8e95e0"],
    xaxis: {
      categories: data.labels.map((l) => truncate(l, 32)),
      max: 100,
      labels: {
        style: { colors: "#5a5d6b", fontSize: "12px" },
        formatter: (v) => `${v}%`,
      },
    },
    yaxis: {
      labels: { style: { colors: "#12131a", fontSize: "12px" }, maxWidth: 200 },
    },
    tooltip: {
      ...baseChart.tooltip,
      y: {
        formatter: (val, opts) => {
          const i = opts.dataPointIndex;
          const counts = opts.seriesIndex === 0 ? data.watched : data.not_watched;
          return `${val}% (${counts[i]} respuestas)`;
        },
      },
    },
  };

  if (exploreChart) {
    exploreChart.updateOptions(options, true, true);
  } else {
    exploreChart = new ApexCharts(document.querySelector("#chart-explore"), options);
    exploreChart.render();
  }
}

function renderKpis(kpis) {
  const root = document.getElementById("kpis");
  root.innerHTML = kpis
    .map(
      (k) => `
      <article class="kpi">
        <p class="label">${k.label}</p>
        <p class="value">${k.value}</p>
        <p class="hint">${k.hint}</p>
      </article>`
    )
    .join("");
}

function renderInsights(insights) {
  const root = document.getElementById("insights");
  root.innerHTML = insights
    .map(
      (i) => `
      <article class="insight">
        <h3>${i.title}</h3>
        <p>${i.text}</p>
      </article>`
    )
    .join("");
}

function main() {
  const data = window.DASHBOARD_DATA;
  const d = data.distributions;

  document.getElementById("meta").textContent =
    `${data.meta.n} respuestas · fuente ${data.meta.source}`;

  renderKpis(data.kpis);
  renderInsights(data.insights);
  funnel("#chart-funnel", data.funnel);

  barHorizontal("#chart-motivation", d[COL.motivation], PALETTE[0]);
  barHorizontal("#chart-channel", d[COL.channel], PALETTE[1]);
  barHorizontal("#chart-reason", d[COL.reason], PALETTE[2]);
  donut("#chart-content", d[COL.content]);
  donut("#chart-payment", d[COL.payment]);
  barHorizontal("#chart-improve", d[COL.improve], PALETTE[3]);
  donut("#chart-age", d[COL.age], 260);
  donut("#chart-country", d[COL.country], 260);
  donut("#chart-familiarity", d[COL.familiarity], 260);

  renderConversion("by_motivation", data.conversion);

  document.querySelectorAll("#conversion-tabs .tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#conversion-tabs .tab").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      renderConversion(btn.dataset.conv, data.conversion);
    });
  });

  dodgedBars("#chart-cross-motivation", data.cross.motivation_x_watched);
  dodgedBars("#chart-cross-channel", data.cross.channel_x_watched);
  dodgedBars("#chart-cross-age-content", data.cross.age_x_content, 360);
  dodgedBars("#chart-cross-payment-age", data.cross.payment_x_age, 360);

  renderExplore("by_motivation", data.explore_by_watched);
  document.querySelectorAll("#explore-tabs .tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#explore-tabs .tab").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      renderExplore(btn.dataset.explore, data.explore_by_watched);
    });
  });
}

try {
  main();
} catch (err) {
  console.error(err);
  document.getElementById("meta").textContent = "No se pudieron cargar los datos.";
}
