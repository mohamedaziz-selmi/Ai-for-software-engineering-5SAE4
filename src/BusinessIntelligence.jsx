import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./bi-workspace.css";

const API = "/api/module5";

// Categorical slots (validated on the workspace surface #f1edf4): blue, orange, aqua, yellow.
// Orange/aqua/yellow sit below 3:1 contrast, so every chart ships a legend and a table view.
const COLOR = {
	ink: "#302b39",
	model: "#2a78d6",
	baseline: "#eb6834",
	advanced: "#1baf7a",
	extra: "#eda100",
};
const CLUSTER_COLORS = [COLOR.model, COLOR.baseline, COLOR.advanced, COLOR.extra, "#e87ba4", "#008300", "#6250d6", "#e34948"];

const TABS = [
	{ id: "overview", label: "Overview" },
	{ id: "sales", label: "Sales forecasting" },
	{ id: "segments", label: "Customer segments" },
	{ id: "data", label: "Data & evaluation" },
];

const METRIC_HELP = {
	mae: "Mean Absolute Error: average absolute difference between actual and predicted daily sales, in units sold. Lower is better.",
	rmse: "Root Mean Squared Error: like MAE but penalises large misses more. Units sold. Lower is better.",
	wape: "Weighted Absolute Percentage Error: sum(|actual − predicted|) / sum(|actual|) × 100. Lower is better.",
	r2: "Coefficient of determination; descriptive only. 1 = perfect, 0 = as good as predicting the mean.",
	silhouette: "Silhouette score (−1 to 1): how much closer customers are to their own cluster than to the next one, in the model's feature space.",
	inertia: "Sum of squared distances from each customer to its cluster centre, in the model's feature space. Only comparable within one feature space.",
};

/* ---------- formatting ---------- */

const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const fmtInt = (value) => (value == null || Number.isNaN(value) ? "—" : numberFormat.format(value));
const fmtNum = (value, digits = 2) => (value == null || Number.isNaN(value) ? "—" : Number(value).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }));
const fmtCompact = (value) => {
	if (value == null || Number.isNaN(value)) return "—";
	const abs = Math.abs(value);
	if (abs >= 1e9) return `${(value / 1e9).toFixed(abs >= 1e10 ? 0 : 1)}B`;
	if (abs >= 1e6) return `${(value / 1e6).toFixed(abs >= 1e7 ? 1 : 2)}M`;
	if (abs >= 1e3) return `${(value / 1e3).toFixed(abs >= 1e4 ? 0 : 1)}K`;
	return `${Math.round(value * 100) / 100}`;
};
const fmtPct = (value, digits = 1) => (value == null || Number.isNaN(value) ? "—" : `${Number(value).toFixed(digits)}%`);
const fmtGbp = (value) => (value == null ? "—" : `£${fmtInt(value)}`);
const fmtDate = (iso) => (iso ? new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }) : "—");
const fmtStamp = (iso) => (iso ? new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "—");
const titleCase = (key) => key.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());

/* ---------- data loading ---------- */

async function readError(response) {
	try {
		const data = await response.json();
		if (typeof data.detail === "string") return data.detail;
		if (Array.isArray(data.detail)) return data.detail.map((item) => `${item.loc?.slice(-1)[0] ?? "input"}: ${item.msg}`).join("; ");
	} catch {
		// Non-JSON body: the dev proxy answers 500/502/504 when the API process is not listening.
	}
	if (response.status >= 500) return `The Module 5 API is not responding (HTTP ${response.status}). Make sure it is running: "uvicorn api:app --port 8002" in module5_business_intelligence/.`;
	return `The Module 5 API returned HTTP ${response.status}.`;
}

function useJson(path, { method = "GET", body = null, enabled = true } = {}) {
	const [state, setState] = useState({ status: enabled ? "loading" : "idle", data: null, error: "" });
	const [attempt, setAttempt] = useState(0);
	const bodyKey = body ? JSON.stringify(body) : "";

	useEffect(() => {
		if (!enabled || !path) return undefined;
		const controller = new AbortController();
		setState((current) => ({ ...current, status: "loading", error: "" }));
		fetch(path, {
			method,
			headers: bodyKey ? { "Content-Type": "application/json" } : undefined,
			body: bodyKey || undefined,
			signal: controller.signal,
		})
			.then(async (response) => {
				if (!response.ok) throw new Error(await readError(response));
				return response.json();
			})
			.then((data) => setState({ status: "ready", data, error: "" }))
			.catch((error) => {
				if (error.name === "AbortError") return;
				const message = error.message === "Failed to fetch" ? "Could not reach the Module 5 API." : error.message;
				setState({ status: "error", data: null, error: message });
			});
		return () => controller.abort();
	}, [path, method, bodyKey, enabled, attempt]);

	const reload = useCallback(() => setAttempt((value) => value + 1), []);
	return { ...state, reload };
}

function useWidth() {
	const ref = useRef(null);
	const [width, setWidth] = useState(640);
	useEffect(() => {
		if (!ref.current) return undefined;
		const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, Math.floor(entry.contentRect.width))));
		observer.observe(ref.current);
		return () => observer.disconnect();
	}, []);
	return [ref, width];
}

/* ---------- shared UI ---------- */

function Status({ resource, children, empty, label = "data" }) {
	if (resource.status === "loading" || resource.status === "idle") return <div className="bi-state" role="status"><span className="bi-spinner" aria-hidden="true" />Loading {label}…</div>;
	if (resource.status === "error") {
		return (
			<div className="review-error bi-state--error" role="alert">
				<strong>Unavailable.</strong> {resource.error}
				<button type="button" className="bi-link-button" onClick={resource.reload}>Retry</button>
			</div>
		);
	}
	if (empty?.(resource.data)) return <div className="review-empty"><strong>No data.</strong><span>{typeof empty.message === "string" ? empty.message : "Nothing matches the current selection."}</span></div>;
	return children(resource.data);
}

function Info({ text }) {
	return <span className="bi-info" title={text} aria-label={text} tabIndex={0}>i</span>;
}

function Section({ eyebrow, title, description, actions, children }) {
	return (
		<section className="bi-section">
			<div className="bi-section__head">
				<div className="review-section-heading">
					{eyebrow && <p className="eyebrow">{eyebrow}</p>}
					<h3>{title}</h3>
					{description && <p>{description}</p>}
				</div>
				{actions && <div className="bi-section__actions">{actions}</div>}
			</div>
			{children}
		</section>
	);
}

function Tile({ label, value, detail, help }) {
	return (
		<div className="bi-tile">
			<span className="bi-tile__label">{label}{help && <Info text={help} />}</span>
			<strong className="bi-tile__value">{value}</strong>
			{detail && <span className="bi-tile__detail">{detail}</span>}
		</div>
	);
}

function Badge({ tone = "neutral", children }) {
	const icon = { pass: "✓", warn: "!", fail: "×", info: "i", neutral: "·" }[tone] ?? "·";
	return <span className={`bi-badge bi-badge--${tone}`}><span aria-hidden="true">{icon}</span>{children}</span>;
}

function Legend({ items }) {
	if (items.length < 2) return null;
	return (
		<ul className="bi-legend" aria-label="Legend">
			{items.map((item) => (
				<li key={item.label}>
					<span className={`bi-legend__key${item.dashed ? " bi-legend__key--dashed" : ""}${item.box ? " bi-legend__key--box" : ""}`} style={{ "--key": item.color }} aria-hidden="true" />
					{item.label}
				</li>
			))}
		</ul>
	);
}

function DataTable({ columns, rows, caption, maxHeight = "18rem" }) {
	return (
		<div className="bi-table-wrap" style={{ maxHeight }}>
			<table className="bi-table">
				{caption && <caption className="visually-hidden">{caption}</caption>}
				<thead><tr>{columns.map((column) => <th key={column.key} scope="col" className={column.numeric ? "is-numeric" : ""}>{column.label}</th>)}</tr></thead>
				<tbody>
					{rows.map((row, index) => (
						<tr key={row.id ?? index}>
							{columns.map((column) => <td key={column.key} className={column.numeric ? "is-numeric" : ""}>{column.render ? column.render(row) : row[column.key]}</td>)}
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

function ChartFrame({ title, legend, table, children, note }) {
	const [showTable, setShowTable] = useState(false);
	return (
		<figure className="bi-chart">
			<figcaption className="bi-chart__head">
				<span className="bi-chart__title">{title}</span>
				{table && (
					<button type="button" className="bi-link-button" aria-pressed={showTable} onClick={() => setShowTable((value) => !value)}>
						{showTable ? "Show chart" : "Show table"}
					</button>
				)}
			</figcaption>
			{legend && !showTable && <Legend items={legend} />}
			{showTable ? table() : children}
			{note && <p className="bi-chart__note">{note}</p>}
		</figure>
	);
}

/* ---------- scales ---------- */

function niceTicks(min, max, count = 5) {
	if (min === max) {
		const pad = Math.abs(min) * 0.1 || 1;
		min -= pad;
		max += pad;
	}
	const span = max - min;
	const step0 = span / count;
	const magnitude = 10 ** Math.floor(Math.log10(step0));
	const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => span / s <= count) ?? magnitude * 10;
	const start = Math.floor(min / step) * step;
	const end = Math.ceil(max / step) * step;
	const ticks = [];
	for (let value = start; value <= end + step / 2; value += step) ticks.push(Math.round(value / step) * step);
	return ticks;
}

const linear = (d0, d1, r0, r1) => (value) => (d1 === d0 ? (r0 + r1) / 2 : r0 + ((value - d0) / (d1 - d0)) * (r1 - r0));
const dayNumber = (iso) => Date.parse(`${iso}T00:00:00Z`) / 86400000;

function Tooltip({ x, y, width, children }) {
	const left = Math.min(Math.max(x + 12, 4), width - 190);
	return <div className="bi-tooltip" style={{ left, top: Math.max(4, y - 12) }} role="status">{children}</div>;
}

/* ---------- charts ---------- */

function LineChart({ series, height = 260, formatY = fmtCompact, shadeFrom, shadeLabel = "Forecast", includeZero = false }) {
	const [ref, width] = useWidth();
	const [hover, setHover] = useState(null);
	const margin = { top: 14, right: 16, bottom: 28, left: 52 };
	const innerW = width - margin.left - margin.right;
	const innerH = height - margin.top - margin.bottom;

	const dates = useMemo(() => [...new Set(series.flatMap((s) => s.points.map((p) => p.date)))].sort(), [series]);
	const values = series.flatMap((s) => s.points.map((p) => p.value)).filter((v) => v != null);
	if (!dates.length || !values.length) return <div className="review-empty"><strong>No points to plot.</strong></div>;

	const ticks = niceTicks(includeZero ? Math.min(0, ...values) : Math.min(...values), Math.max(...values));
	const x = linear(dayNumber(dates[0]), dayNumber(dates[dates.length - 1]), 0, innerW);
	const y = linear(ticks[0], ticks[ticks.length - 1], innerH, 0);
	const lookup = series.map((s) => new Map(s.points.map((p) => [p.date, p.value])));

	const xTicks = [];
	const spanDays = dayNumber(dates[dates.length - 1]) - dayNumber(dates[0]);
	const every = Math.max(1, Math.ceil(dates.length / Math.max(2, Math.floor(innerW / 90))));
	for (let i = 0; i < dates.length; i += every) xTicks.push(dates[i]);
	const tickLabel = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", spanDays > 400 ? { month: "short", year: "2-digit", timeZone: "UTC" } : { day: "2-digit", month: "short", timeZone: "UTC" });

	const path = (s, i) => {
		let d = "";
		let open = false;
		dates.forEach((date) => {
			const value = lookup[i].get(date);
			if (value == null) {
				open = false;
				return;
			}
			d += `${open ? "L" : "M"}${x(dayNumber(date)).toFixed(1)},${y(value).toFixed(1)}`;
			open = true;
		});
		return d;
	};

	const onMove = (event) => {
		const box = event.currentTarget.getBoundingClientRect();
		const px = event.clientX - box.left - margin.left;
		let best = 0;
		let bestDistance = Infinity;
		dates.forEach((date, index) => {
			const distance = Math.abs(x(dayNumber(date)) - px);
			if (distance < bestDistance) {
				bestDistance = distance;
				best = index;
			}
		});
		setHover({ date: dates[best], px: x(dayNumber(dates[best])) + margin.left, py: event.clientY - box.top });
	};

	const shadeX = shadeFrom ? x(dayNumber(shadeFrom)) : null;

	return (
		<div ref={ref} className="bi-plot">
			<svg width={width} height={height} role="img" aria-label={series.map((s) => s.label).join(", ")} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
				<g transform={`translate(${margin.left},${margin.top})`}>
					{shadeX != null && shadeX < innerW && (
						<g>
							<rect x={Math.max(0, shadeX)} y={0} width={innerW - Math.max(0, shadeX)} height={innerH} className="bi-shade" />
							<text x={Math.max(0, shadeX) + 6} y={12} className="bi-axis-label">{shadeLabel} →</text>
						</g>
					)}
					{ticks.map((tick) => (
						<g key={tick}>
							<line x1={0} x2={innerW} y1={y(tick)} y2={y(tick)} className="bi-grid" />
							<text x={-8} y={y(tick)} dy="0.32em" textAnchor="end" className="bi-axis-label">{formatY(tick)}</text>
						</g>
					))}
					{xTicks.map((date) => <text key={date} x={x(dayNumber(date))} y={innerH + 18} textAnchor="middle" className="bi-axis-label">{tickLabel(date)}</text>)}
					{series.map((s, i) => (
						<path key={s.key} d={path(s, i)} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" strokeDasharray={s.dashed ? "6 4" : undefined} />
					))}
					{hover && (
						<g>
							<line x1={hover.px - margin.left} x2={hover.px - margin.left} y1={0} y2={innerH} className="bi-crosshair" />
							{series.map((s, i) => {
								const value = lookup[i].get(hover.date);
								return value == null ? null : <circle key={s.key} cx={hover.px - margin.left} cy={y(value)} r={4.5} fill={s.color} stroke="#f1edf4" strokeWidth={2} />;
							})}
						</g>
					)}
				</g>
			</svg>
			{hover && (
				<Tooltip x={hover.px} y={hover.py} width={width}>
					<strong>{fmtDate(hover.date)}</strong>
					{series.map((s, i) => {
						const value = lookup[i].get(hover.date);
						return value == null ? null : <span key={s.key}><i style={{ background: s.color }} />{s.label}<b>{formatY === fmtCompact ? fmtInt(value) : formatY(value)}</b></span>;
					})}
				</Tooltip>
			)}
		</div>
	);
}

function barPath(x0, x1, y0, thickness, horizontal) {
	// 4px rounded data-end, square at the baseline.
	const r = Math.min(4, Math.abs(x1 - x0) / 2, thickness / 2);
	if (horizontal) {
		const w = Math.max(0, x1 - x0);
		return `M${x0},${y0}h${w - r}a${r},${r} 0 0 1 ${r},${r}v${thickness - 2 * r}a${r},${r} 0 0 1 ${-r},${r}h${-(w - r)}z`;
	}
	const h = Math.max(0, x0 - x1); // x0 = baseline y, x1 = top y
	return `M${y0},${x0}v${-(h - r)}a${r},${r} 0 0 1 ${r},${-r}h${thickness - 2 * r}a${r},${r} 0 0 1 ${r},${r}v${h - r}z`;
}

function HBarChart({ items, formatValue = fmtInt, labelWidth = 170 }) {
	const [ref, width] = useWidth();
	const [hover, setHover] = useState(null);
	const row = 30;
	const thickness = 16;
	const valueSpace = 76;
	const innerW = Math.max(40, width - labelWidth - valueSpace);
	const max = Math.max(...items.map((item) => Math.abs(item.value)), 0) || 1;
	const height = items.length * row + 6;
	return (
		<div ref={ref} className="bi-plot">
			<svg width={width} height={height} role="img" aria-label="Bar chart">
				{items.map((item, index) => {
					const top = index * row + (row - thickness) / 2;
					const w = (Math.max(0, item.value) / max) * innerW;
					return (
						<g key={item.label} onPointerEnter={(event) => setHover({ item, py: top, px: labelWidth + w })} onPointerLeave={() => setHover(null)}>
							<rect x={0} y={index * row} width={width} height={row} fill="transparent" />
							<text x={labelWidth - 10} y={top + thickness / 2} dy="0.32em" textAnchor="end" className="bi-bar-label">{item.label}</text>
							<line x1={labelWidth} x2={labelWidth} y1={index * row + 4} y2={index * row + row - 4} className="bi-grid" />
							<path d={barPath(labelWidth, labelWidth + w, top, thickness, true)} fill={item.color ?? COLOR.model} opacity={hover && hover.item !== item ? 0.55 : 1} />
							<text x={labelWidth + w + 6} y={top + thickness / 2} dy="0.32em" className="bi-bar-value">{formatValue(item.value)}</text>
						</g>
					);
				})}
			</svg>
			{hover?.item.tooltip && <Tooltip x={hover.px} y={hover.py} width={width}>{hover.item.tooltip}</Tooltip>}
		</div>
	);
}

function ColumnChart({ categories, series, height = 220, formatY = fmtCompact }) {
	const [ref, width] = useWidth();
	const [hover, setHover] = useState(null);
	const margin = { top: 12, right: 8, bottom: 26, left: 52 };
	const innerW = width - margin.left - margin.right;
	const innerH = height - margin.top - margin.bottom;
	const values = series.flatMap((s) => s.values).filter((v) => v != null);
	const ticks = niceTicks(0, Math.max(...values, 0));
	const y = linear(0, ticks[ticks.length - 1], innerH, 0);
	const band = innerW / Math.max(1, categories.length);
	const thickness = Math.min(24, (band * 0.7 - 2 * (series.length - 1)) / series.length);
	const groupWidth = thickness * series.length + 2 * (series.length - 1);
	const labelEvery = Math.ceil(categories.length / Math.max(1, Math.floor(innerW / 34)));
	return (
		<div ref={ref} className="bi-plot">
			<svg width={width} height={height} role="img" aria-label="Column chart">
				<g transform={`translate(${margin.left},${margin.top})`}>
					{ticks.map((tick) => (
						<g key={tick}>
							<line x1={0} x2={innerW} y1={y(tick)} y2={y(tick)} className="bi-grid" />
							<text x={-8} y={y(tick)} dy="0.32em" textAnchor="end" className="bi-axis-label">{formatY(tick)}</text>
						</g>
					))}
					{categories.map((category, ci) => {
						const left = ci * band + (band - groupWidth) / 2;
						return (
							<g key={category} onPointerEnter={() => setHover({ ci, px: margin.left + ci * band + band / 2 })} onPointerLeave={() => setHover(null)}>
								<rect x={ci * band} y={0} width={band} height={innerH} fill={hover?.ci === ci ? "rgba(48,43,57,.05)" : "transparent"} />
								{series.map((s, si) => {
									const value = s.values[ci];
									if (value == null) return null;
									return <path key={s.key} d={barPath(innerH, y(value), left + si * (thickness + 2), thickness, false)} fill={s.color} />;
								})}
								{ci % labelEvery === 0 && <text x={ci * band + band / 2} y={innerH + 17} textAnchor="middle" className="bi-axis-label">{category}</text>}
							</g>
						);
					})}
				</g>
			</svg>
			{hover && (
				<Tooltip x={hover.px} y={margin.top + 10} width={width}>
					<strong>{categories[hover.ci]}</strong>
					{series.map((s) => <span key={s.key}><i style={{ background: s.color }} />{s.label}<b>{s.values[hover.ci] == null ? "—" : (formatY === fmtCompact ? fmtInt(s.values[hover.ci]) : formatY(s.values[hover.ci]))}</b></span>)}
				</Tooltip>
			)}
		</div>
	);
}

function Histogram({ histogram, color = COLOR.model, height = 200, formatX = fmtCompact, valueLabel = "customers" }) {
	const [ref, width] = useWidth();
	const [hover, setHover] = useState(null);
	if (!histogram?.counts?.length) return <div className="review-empty"><strong>Histogram unavailable.</strong></div>;
	const margin = { top: 10, right: 8, bottom: 26, left: 44 };
	const innerW = width - margin.left - margin.right;
	const innerH = height - margin.top - margin.bottom;
	const { counts, edges } = histogram;
	const ticks = niceTicks(0, Math.max(...counts));
	const y = linear(0, ticks[ticks.length - 1], innerH, 0);
	const band = innerW / counts.length;
	const shown = (value) => (histogram.log1p ? Math.expm1(value) : value);
	const xLabels = [0, Math.floor(counts.length / 2), counts.length];
	return (
		<div ref={ref} className="bi-plot">
			<svg width={width} height={height} role="img" aria-label="Histogram">
				<g transform={`translate(${margin.left},${margin.top})`}>
					{ticks.map((tick) => (
						<g key={tick}>
							<line x1={0} x2={innerW} y1={y(tick)} y2={y(tick)} className="bi-grid" />
							<text x={-8} y={y(tick)} dy="0.32em" textAnchor="end" className="bi-axis-label">{fmtCompact(tick)}</text>
						</g>
					))}
					{counts.map((count, index) => (
						<g key={index} onPointerEnter={() => setHover({ index, px: margin.left + index * band + band / 2 })} onPointerLeave={() => setHover(null)}>
							<rect x={index * band} y={0} width={band} height={innerH} fill="transparent" />
							<path d={barPath(innerH, y(count), index * band + 1, Math.max(1, band - 2), false)} fill={color} opacity={hover && hover.index !== index ? 0.6 : 1} />
						</g>
					))}
					{xLabels.map((i) => <text key={i} x={i * band} y={innerH + 17} textAnchor={i === 0 ? "start" : i === counts.length ? "end" : "middle"} className="bi-axis-label">{formatX(shown(edges[i]))}</text>)}
				</g>
			</svg>
			{hover && (
				<Tooltip x={hover.px} y={margin.top + 10} width={width}>
					<strong>{formatX(shown(edges[hover.index]))} – {formatX(shown(edges[hover.index + 1]))}</strong>
					<span>{fmtInt(counts[hover.index])} {valueLabel}</span>
				</Tooltip>
			)}
		</div>
	);
}

/* ---------- pages ---------- */

const isoMinusDays = (iso, days) => new Date(Date.parse(`${iso}T00:00:00Z`) - days * 86400000).toISOString().slice(0, 10);

function OverviewPage({ onNavigate }) {
	const [period, setPeriod] = useState({ start: "", end: "" });
	const [forecastDays, setForecastDays] = useState(14);
	const query = new URLSearchParams({ forecast_days: String(forecastDays), ...(period.start && { start: period.start }), ...(period.end && { end: period.end }) });
	const overview = useJson(`${API}/overview?${query}`);

	return (
		<Status resource={overview} label="overview">
			{(data) => {
				const sales = data.sales ?? {};
				const segments = data.segmentation ?? {};
				const range = sales.history_range;
				const rf = sales.test_metrics?.random_forest;
				const naive = sales.test_metrics?.seasonal_naive;
				return (
					<>
						<Section
							eyebrow="A / Business intelligence overview"
							title="Headline figures"
							description="All values come from the saved artifacts of the Module 5 pipelines. Change the period to recompute total sales."
							actions={range && (
								<form className="bi-controls" onSubmit={(event) => event.preventDefault()}>
									<label>From<input type="date" min={range.start} max={period.end || range.end} value={period.start || sales.period?.start || ""} onChange={(event) => setPeriod((p) => ({ ...p, start: event.target.value }))} /></label>
									<label>To<input type="date" min={period.start || range.start} max={range.end} value={period.end || sales.period?.end || ""} onChange={(event) => setPeriod((p) => ({ ...p, end: event.target.value }))} /></label>
									<label>Forecast<select value={forecastDays} onChange={(event) => setForecastDays(Number(event.target.value))}>{[7, 14, 21, 28].map((d) => <option key={d} value={d}>{d} days</option>)}</select></label>
									<button type="button" className="bi-link-button" onClick={() => { setPeriod({ start: "", end: "" }); setForecastDays(14); }}>Reset</button>
								</form>
							)}
						>
							<div className="bi-tiles">
								{sales.unavailable ? <div className="review-error">{sales.unavailable}</div> : (
									<>
										<Tile label="Total sales in period" value={fmtCompact(sales.total_sales)} detail={`${fmtDate(sales.period.start)} → ${fmtDate(sales.period.end)} · ${sales.period.days} days · units sold`} help="Sum of daily unit sales across all 54 stores and 33 product families." />
										<Tile label={`Forecast, next ${sales.forecast.days} days`} value={fmtCompact(sales.forecast.total)} detail={`Random Forest, recursive from ${fmtDate(sales.forecast.origin)}`} help="Sum of recursive Random Forest predictions after the last observed day. Predicted, not actual." />
										<Tile label="Forecast error (test WAPE)" value={fmtPct(rf?.wape, 2)} detail={`Seasonal naive baseline ${fmtPct(naive?.wape, 2)}`} help={METRIC_HELP.wape} />
									</>
								)}
								{segments.unavailable ? <div className="review-error">{segments.unavailable}</div> : (
									<>
										<Tile label="Eligible customers" value={fmtInt(segments.eligible_customers)} detail={`RFM reference date ${fmtDate(segments.reference_date)}`} help="Customers with a CustomerID, at least one valid purchase, and positive net spending." />
										<Tile label="Identified segments" value={segments.segments} detail={`Silhouette ${fmtNum(segments.silhouette_after, 3)} after preprocessing`} help={METRIC_HELP.silhouette} />
									</>
								)}
							</div>
						</Section>
						<div className="bi-grid-2">
							<Section eyebrow="Data quality" title="Dataset checks">
								{data.data_quality ? Object.entries(data.data_quality).map(([key, value]) => (
									<div key={key} className="bi-checklist">
										<h4>{titleCase(key)} <Badge tone={value.status}>{value.status}</Badge></h4>
										<ul>{value.checks.map((check) => <li key={check.check}><Badge tone={check.result}>{titleCase(check.check)}</Badge><span>{check.detail}</span></li>)}</ul>
									</div>
								)) : <div className="review-empty"><strong>No data-quality report.</strong><span>Run the pipelines to generate it.</span></div>}
							</Section>
							<Section eyebrow="Model training" title="Training status">
								<TrainingList models={data.training_status} />
								<div className="bi-nav-links">
									<button type="button" className="bi-link-button" onClick={() => onNavigate("sales")}>Open sales forecasting →</button>
									<button type="button" className="bi-link-button" onClick={() => onNavigate("segments")}>Open customer segments →</button>
								</div>
							</Section>
						</div>
						{!segments.unavailable && segments.segment_sizes && (
							<Section eyebrow="Segments" title="Customers per segment">
								<HBarChart items={Object.entries(segments.segment_sizes).map(([label, value], index) => ({ label, value, color: CLUSTER_COLORS[index], tooltip: `${label}: ${fmtInt(value)} customers` }))} />
							</Section>
						)}
					</>
				);
			}}
		</Status>
	);
}

function TrainingList({ models }) {
	return (
		<ul className="bi-training">
			{Object.entries(models).map(([key, model]) => (
				<li key={key}>
					<div>
						<strong>{titleCase(key)}</strong>
						<span>{model.model ?? "—"}{model.trained_at ? ` · trained ${fmtStamp(model.trained_at)}` : ""}{model.runtime_seconds ? ` · ${model.runtime_seconds}s` : ""}</span>
					</div>
					<Badge tone={model.ready ? "pass" : "fail"}>{model.ready ? "Ready" : "Missing artifacts"}</Badge>
				</li>
			))}
		</ul>
	);
}

function MetricComparison({ metrics, improvementVsNaive, labels = { seasonal_naive: "Seasonal naive (t − 7)", random_forest: "Random Forest" } }) {
	return (
		<div className="bi-metric-grid">
			{["mae", "rmse", "wape"].map((key) => {
				const before = metrics.seasonal_naive?.[key];
				const after = metrics.random_forest?.[key];
				const change = improvementVsNaive?.[key];
				const format = key === "wape" ? (v) => fmtPct(v, 2) : fmtInt;
				return (
					<div key={key} className="bi-metric">
						<span className="bi-tile__label">{key.toUpperCase()}<Info text={METRIC_HELP[key]} /></span>
						<div className="bi-metric__pair">
							<div><small><i style={{ background: COLOR.baseline }} />{labels.seasonal_naive}</small><b>{format(before)}</b></div>
							<div><small><i style={{ background: COLOR.model }} />{labels.random_forest}</small><b>{format(after)}</b></div>
						</div>
						<span className={`bi-metric__delta${change?.absolute_reduction > 0 ? " is-better" : " is-worse"}`}>
							{change?.absolute_reduction == null ? "Change unavailable" : `${change.absolute_reduction > 0 ? "▼" : "▲"} ${key === "wape" ? `${fmtNum(Math.abs(change.absolute_reduction), 2)} pts` : fmtInt(Math.abs(change.absolute_reduction))} (${fmtPct(Math.abs(change.percent_reduction))}) ${change.absolute_reduction > 0 ? "lower error" : "higher error"}`}
						</span>
					</div>
				);
			})}
		</div>
	);
}

function SalesPage() {
	const options = useJson(`${API}/sales/options`);
	const evaluation = useJson(`${API}/sales/evaluation`);
	const [form, setForm] = useState({ model: "basic", horizon: 14, historyDays: 90, origin: "", store: "", family: "" });
	const [request, setRequest] = useState({ horizon: 14, history_days: 90 });
	const forecast = useJson(`${API}/sales/forecast`, { method: "POST", body: request });
	const [historyRange, setHistoryRange] = useState({ start: "2016-08-16", end: "2017-08-15" });
	const history = useJson(`${API}/sales/history?start=${historyRange.start}&end=${historyRange.end}`);
	const [period, setPeriod] = useState("test");

	const advanced = form.model === "advanced";
	const maxHorizon = advanced ? 16 : 28;
	const submit = (event) => {
		event.preventDefault();
		const horizon = Math.min(form.horizon, maxHorizon);
		setRequest(advanced
			? { model: "advanced", horizon, history_days: form.historyDays, ...(form.store && { store_nbr: Number(form.store) }), ...(form.family && { family: form.family }) }
			: { model: "basic", horizon, history_days: form.historyDays, ...(form.origin && { origin: form.origin }) });
	};
	const advancedReady = options.data?.advanced_available;

	return (
		<>
			<Section eyebrow="B / Sales forecasting" title="Forecast future sales" description="Basic model: total daily sales across all stores, Random Forest with recursive multi-step forecasting. Advanced model: store × product-family forecasts for the 16 days after the data ends (direct strategy).">
				<form className="bi-controls bi-controls--panel" onSubmit={submit}>
					<label>Model
						<select value={form.model} onChange={(event) => setForm((f) => ({ ...f, model: event.target.value }))}>
							<option value="basic">Basic · daily total (Random Forest)</option>
							<option value="advanced" disabled={!advancedReady}>Advanced · store × family{advancedReady ? "" : " (not trained)"}</option>
						</select>
					</label>
					<label>Horizon
						<select value={Math.min(form.horizon, maxHorizon)} onChange={(event) => setForm((f) => ({ ...f, horizon: Number(event.target.value) }))}>
							{[7, 14, 16, 21, 28].filter((d) => d <= maxHorizon).map((d) => <option key={d} value={d}>{d} days</option>)}
						</select>
					</label>
					{advanced ? (
						<>
							<label>Store
								<select value={form.store} onChange={(event) => setForm((f) => ({ ...f, store: event.target.value }))}>
									<option value="">All stores</option>
									{options.data?.stores.map((s) => <option key={s} value={s}>Store {s}</option>)}
								</select>
							</label>
							<label>Product family
								<select value={form.family} onChange={(event) => setForm((f) => ({ ...f, family: event.target.value }))}>
									<option value="">All families</option>
									{options.data?.families.map((f) => <option key={f} value={f}>{titleCase(f.toLowerCase())}</option>)}
								</select>
							</label>
						</>
					) : (
						<>
							<label title="Leave empty to forecast after the last observed day (15 Aug 2017). Pick an earlier date to backtest against actual sales.">Forecast from
								<input type="date" min="2013-01-30" max="2017-08-15" value={form.origin} onChange={(event) => setForm((f) => ({ ...f, origin: event.target.value }))} />
							</label>
							<label>Context
								<select value={form.historyDays} onChange={(event) => setForm((f) => ({ ...f, historyDays: Number(event.target.value) }))}>
									{[30, 90, 180, 365].map((d) => <option key={d} value={d}>{d} days</option>)}
								</select>
							</label>
						</>
					)}
					<button type="submit" className="review-primary-action bi-submit" disabled={forecast.status === "loading"}>{forecast.status === "loading" ? "Forecasting…" : "Run forecast"}</button>
				</form>
				<Status resource={forecast} label="forecast">
					{(data) => {
						const historyPoints = data.history.map((p) => ({ date: p.date, value: p.actual }));
						const forecastPoints = data.points.map((p) => ({ date: p.date, value: p.forecast }));
						const actualFuture = data.points.filter((p) => p.actual != null).map((p) => ({ date: p.date, value: p.actual }));
						const lastHistory = historyPoints[historyPoints.length - 1];
						const series = [
							...(historyPoints.length ? [{ key: "actual", label: "Actual sales", color: COLOR.ink, points: [...historyPoints, ...actualFuture] }] : []),
							{ key: "forecast", label: data.model === "advanced" ? "Forecast (advanced)" : "Forecast (Random Forest)", color: data.model === "advanced" ? COLOR.advanced : COLOR.model, dashed: true, points: lastHistory ? [lastHistory, ...forecastPoints] : forecastPoints },
						];
						const total = data.points.reduce((sum, p) => sum + p.forecast, 0);
						const withActual = data.points.filter((p) => p.actual != null);
						const backtestWape = withActual.length ? withActual.reduce((s, p) => s + Math.abs(p.actual - p.forecast), 0) / withActual.reduce((s, p) => s + Math.abs(p.actual), 0) * 100 : null;
						return (
							<>
								<div className="bi-tiles bi-tiles--compact">
									<Tile label="Forecast total" value={fmtCompact(total)} detail={`${data.horizon} days after ${fmtDate(data.origin)}`} />
									<Tile label="Average per day" value={fmtCompact(total / data.points.length)} detail="Predicted units" />
									{backtestWape != null && <Tile label="Backtest WAPE" value={fmtPct(backtestWape, 2)} detail={`${withActual.length} days with known actuals`} help={METRIC_HELP.wape} />}
									{data.filters && <Tile label="Filter" value={data.filters.store_nbr ? `Store ${data.filters.store_nbr}` : "All stores"} detail={data.filters.family ?? "All families"} />}
								</div>
								{data.in_sample_warning && <p className="bi-warning" role="note">{data.in_sample_warning}</p>}
								<ChartFrame
									title={data.model === "advanced" ? "Advanced forecast (sum of selected store × family series)" : "Actual history and forecast"}
									legend={series.map((s) => ({ label: s.label, color: s.color, dashed: s.dashed }))}
									note={data.method}
									table={() => <DataTable caption="Forecast" columns={[{ key: "date", label: "Date", render: (r) => fmtDate(r.date) }, { key: "forecast", label: "Forecast", numeric: true, render: (r) => fmtInt(r.forecast) }, { key: "actual", label: "Actual", numeric: true, render: (r) => fmtInt(r.actual) }]} rows={data.points} />}
								>
									<LineChart series={series} shadeFrom={forecastPoints[0]?.date} />
								</ChartFrame>
							</>
						);
					}}
				</Status>
			</Section>

			<Section
				eyebrow="Historical sales"
				title="Daily sales history"
				description="Total daily unit sales from train.csv after cleaning. 25 December closures are shown as zero."
				actions={(
					<form className="bi-controls" onSubmit={(event) => event.preventDefault()}>
						<label>From<input type="date" min="2013-01-01" max={historyRange.end} value={historyRange.start} onChange={(event) => event.target.value && setHistoryRange((r) => ({ ...r, start: event.target.value }))} /></label>
						<label>To<input type="date" min={historyRange.start} max="2017-08-15" value={historyRange.end} onChange={(event) => event.target.value && setHistoryRange((r) => ({ ...r, end: event.target.value }))} /></label>
						<select aria-label="Quick range" value="" onChange={(event) => event.target.value && setHistoryRange({ start: isoMinusDays("2017-08-15", Number(event.target.value) - 1), end: "2017-08-15" })}>
							<option value="">Quick range…</option>
							<option value="90">Last 90 days</option>
							<option value="365">Last year</option>
							<option value="1688">All history</option>
						</select>
					</form>
				)}
			>
				<Status resource={history} label="history" empty={(d) => !d.points.length}>
					{(data) => (
						<ChartFrame title="Total daily sales" table={() => <DataTable caption="History" columns={[{ key: "date", label: "Date", render: (r) => fmtDate(r.date) }, { key: "sales", label: "Sales", numeric: true, render: (r) => fmtInt(r.sales) }, { key: "is_national_holiday", label: "Holiday", render: (r) => (r.is_national_holiday ? "Yes" : "") }]} rows={data.points} />}>
							<LineChart series={[{ key: "sales", label: "Daily sales", color: COLOR.ink, points: data.points.map((p) => ({ date: p.date, value: p.sales })) }]} height={230} includeZero />
						</ChartFrame>
					)}
				</Status>
			</Section>

			<Status resource={evaluation} label="evaluation">
				{(data) => <SalesEvaluation data={data} period={period} setPeriod={setPeriod} />}
			</Status>
		</>
	);
}

function SalesEvaluation({ data, period, setPeriod }) {
	const basic = data.basic;
	const meta = data.metadata;
	const section = period === "multistep" ? basic.multistep_test : basic[period];
	const metrics = section.metrics;
	const points = section.series;
	const series = [
		{ key: "actual", label: "Actual", color: COLOR.ink, points: points.map((p) => ({ date: p.date, value: p.actual })) },
		{ key: "naive", label: "Seasonal naive (baseline)", color: COLOR.baseline, points: points.map((p) => ({ date: p.date, value: p.seasonal_naive })) },
		{ key: "rf", label: "Random Forest", color: COLOR.model, points: points.map((p) => ({ date: p.date, value: p.random_forest })) },
	];
	const breakdown = basic[period === "multistep" ? "test" : period].error_breakdown;
	const residuals = basic[period === "multistep" ? "test" : period].residuals;
	const periodInfo = period === "multistep" ? basic.test.period : section.period;
	const fitPeriod = period === "multistep" ? basic.test.fit_period : section.fit_period;
	const importances = basic.feature_importance.features.slice(0, 12);

	return (
		<>
			<Section
				eyebrow="Before / after training"
				title="Baseline vs Random Forest"
				description={basic.protocol}
				actions={(
					<div className="bi-segmented" role="tablist" aria-label="Evaluation period">
						{[["validation", "Validation"], ["test", "Test"], ["multistep", "Test · 16-day recursive"]].map(([key, label]) => (
							<button key={key} type="button" role="tab" aria-selected={period === key} onClick={() => setPeriod(key)}>{label}</button>
						))}
					</div>
				)}
			>
				<p className="bi-period">
					Scored on <b>{fmtDate(periodInfo.start)} → {fmtDate(periodInfo.end)}</b> ({fmtInt(metrics.random_forest.n_observations)} days) · model fitted on {fmtDate(fitPeriod.start)} → {fmtDate(fitPeriod.end)}
					{period !== "multistep" && <> · historical-mean baseline WAPE {fmtPct(metrics.historical_mean.wape, 2)}</>}
				</p>
				<MetricComparison metrics={metrics} improvementVsNaive={section.improvement_vs_seasonal_naive} />
				<ChartFrame
					title="Actual vs predicted daily sales"
					legend={series.map((s) => ({ label: s.label, color: s.color }))}
					table={() => <DataTable caption="Actual vs predicted" columns={[{ key: "date", label: "Date", render: (r) => fmtDate(r.date) }, { key: "actual", label: "Actual", numeric: true, render: (r) => fmtInt(r.actual) }, { key: "seasonal_naive", label: "Seasonal naive", numeric: true, render: (r) => fmtInt(r.seasonal_naive) }, { key: "random_forest", label: "Random Forest", numeric: true, render: (r) => fmtInt(r.random_forest) }]} rows={points} />}
				>
					<LineChart series={series} />
				</ChartFrame>
			</Section>

			<div className="bi-grid-2">
				<Section eyebrow="Residual analysis" title="Residual distribution" description={`Actual − predicted on the ${period === "validation" ? "validation" : "test"} period (one-step-ahead). Centred near zero means little systematic bias.`}>
					{["random_forest", "seasonal_naive"].map((key) => (
						<ChartFrame key={key} title={`${key === "random_forest" ? "Random Forest" : "Seasonal naive"} · mean ${fmtInt(residuals[key].mean)}, std ${fmtInt(residuals[key].std)}`}>
							<Histogram histogram={residuals[key]} color={key === "random_forest" ? COLOR.model : COLOR.baseline} height={150} valueLabel="days" />
						</ChartFrame>
					))}
				</Section>
				<Section eyebrow="Error breakdown" title="Mean absolute error by weekday and month">
					{[["by_weekday", "By weekday"], ["by_month", "By month"]].map(([key, label]) => {
						const categories = breakdown.random_forest[key].map((row) => row.group);
						const s = [
							{ key: "naive", label: "Seasonal naive", color: COLOR.baseline, values: breakdown.seasonal_naive[key].map((r) => r.mae) },
							{ key: "rf", label: "Random Forest", color: COLOR.model, values: breakdown.random_forest[key].map((r) => r.mae) },
						];
						return (
							<ChartFrame key={key} title={label} legend={s.map((x) => ({ label: x.label, color: x.color, box: true }))} table={() => <DataTable columns={[{ key: "group", label: "Group" }, { key: "naive", label: "Naive MAE", numeric: true, render: (r) => fmtInt(r.naive) }, { key: "rf", label: "RF MAE", numeric: true, render: (r) => fmtInt(r.rf) }, { key: "n", label: "Days", numeric: true }]} rows={categories.map((group, i) => ({ id: group, group, naive: s[0].values[i], rf: s[1].values[i], n: breakdown.random_forest[key][i].n }))} />}>
								<ColumnChart categories={categories} series={s} height={170} />
							</ChartFrame>
						);
					})}
				</Section>
			</div>

			<div className="bi-grid-2">
				<Section eyebrow="Explainability" title="Feature importance" description="Permutation importance on the validation period: how much MAE increases when a feature is shuffled.">
					<HBarChart items={importances.map((row) => ({ label: row.feature, value: row.permutation_mae_increase, color: COLOR.model, tooltip: `${row.feature}: +${fmtInt(row.permutation_mae_increase)} MAE (±${fmtInt(row.permutation_std)}); impurity ${fmtNum(row.impurity_importance, 3)}` }))} labelWidth={140} />
				</Section>
				<Section eyebrow="Metadata" title="Validation period and model">
					<dl className="bi-facts">
						<div><dt>Target</dt><dd>{basic.target}</dd></div>
						{meta && Object.entries(meta.periods).map(([name, p]) => <div key={name}><dt>{titleCase(name)} period</dt><dd>{fmtDate(p.start)} → {fmtDate(p.end)}</dd></div>)}
						{meta && <div><dt>Hyperparameters</dt><dd className="bi-mono">{Object.entries(meta.hyperparameters).map(([k, v]) => `${k}=${v ?? "None"}`).join(" · ")}</dd></div>}
						{meta && <div><dt>Tuning</dt><dd>{meta.tuning.selection_metric}, {meta.tuning.folds.length} folds, {meta.tuning.candidates.length} candidates</dd></div>}
						{meta && <div><dt>Trained</dt><dd>{fmtStamp(meta.trained_at)} · seed {meta.random_seed} · scikit-learn {meta.environment["scikit-learn"]}</dd></div>}
						<div><dt>Baselines</dt><dd>{Object.values(basic.baselines).join("; ")}</dd></div>
					</dl>
				</Section>
			</div>

			<Section eyebrow="Optional advanced model" title="Store × family model vs basic model" description={data.advanced ? data.advanced.strategy : "The advanced model has not been trained."}>
				{data.advanced ? (
					<>
						<DataTable
							caption="Advanced comparison"
							columns={[{ key: "model", label: "Model (daily totals, same 16-day test blocks)" }, { key: "mae", label: "MAE", numeric: true, render: (r) => fmtInt(r.mae) }, { key: "rmse", label: "RMSE", numeric: true, render: (r) => fmtInt(r.rmse) }, { key: "wape", label: "WAPE", numeric: true, render: (r) => fmtPct(r.wape, 2) }]}
							rows={Object.entries(data.advanced.test_daily_total_comparison.metrics).map(([model, m]) => ({ id: model, model: { advanced: "Advanced store × family (HistGradientBoosting)", random_forest: "Basic Random Forest (recursive)", seasonal_naive: "Seasonal naive (repeat last week)" }[model] ?? model, ...m }))}
						/>
						<p className="bi-chart__note">Series level (store × family × day): advanced WAPE {fmtPct(data.advanced.test_series_level_metrics.advanced.wape, 2)} vs per-series seasonal naive {fmtPct(data.advanced.test_series_level_metrics.seasonal_naive_per_series.wape, 2)} over {fmtInt(data.advanced.test_series_level_metrics.advanced.n_observations)} rows.</p>
					</>
				) : <div className="review-empty"><strong>Not available.</strong><span>Run the sales pipeline without --skip-advanced.</span></div>}
			</Section>
		</>
	);
}

function SegmentsPage() {
	const clusters = useJson(`${API}/segmentation/clusters`);
	const [feature, setFeature] = useState("monetary");
	const [scale, setScale] = useState("log1p");
	const [filters, setFilters] = useState({ search: "", segment: "", sort: "monetary", order: "desc", page: 1, pageSize: 25 });
	const [searchInput, setSearchInput] = useState("");
	const query = new URLSearchParams({ page: String(filters.page), page_size: String(filters.pageSize), sort: filters.sort, order: filters.order, ...(filters.search && { search: filters.search }), ...(filters.segment && { segment: filters.segment }) });
	const customers = useJson(`${API}/segmentation/customers?${query}`);

	useEffect(() => {
		const id = window.setTimeout(() => setFilters((f) => (f.search === searchInput ? f : { ...f, search: searchInput, page: 1 })), 300);
		return () => window.clearTimeout(id);
	}, [searchInput]);

	const setSort = (key) => setFilters((f) => ({ ...f, sort: key, order: f.sort === key && f.order === "desc" ? "asc" : "desc", page: 1 }));
	const sortHeader = (key, label) => (
		<button type="button" className="bi-sort" onClick={() => setSort(key)} aria-label={`Sort by ${label}`}>
			{label}{filters.sort === key ? (filters.order === "desc" ? " ↓" : " ↑") : ""}
		</button>
	);

	return (
		<Status resource={clusters} label="segments">
			{(data) => {
				const profiles = [...data.clusters].sort((a, b) => b.monetary_median - a.monetary_median);
				const colorOf = Object.fromEntries(data.clusters.map((c) => [c.cluster, CLUSTER_COLORS[c.cluster % CLUSTER_COLORS.length]]));
				const metricBars = (key, label, format) => (
					<ChartFrame key={key} title={label}>
						<HBarChart items={profiles.map((p) => ({ label: p.segment_label, value: p[`${key}_median`], color: colorOf[p.cluster], tooltip: `${p.segment_label}: median ${format(p[`${key}_median`])}, mean ${format(p[`${key}_mean`])}` }))} formatValue={format} labelWidth={190} />
					</ChartFrame>
				);
				return (
					<>
						<Section eyebrow="C / Customer segmentation" title={`${data.k} customer segments`} description={`K-means on log1p-transformed, standardized Recency, Frequency and Monetary for ${fmtInt(data.clusters.reduce((s, c) => s + c.customers, 0))} customers. Reference date ${fmtDate(data.reference_date)}. Labels come from configurable rules on each cluster's median RFM values, not from cluster numbers.`}>
							<div className="bi-grid-2 bi-grid-2--flush">
								<ChartFrame title="Cluster distribution" table={() => <DataTable columns={[{ key: "segment_label", label: "Segment" }, { key: "cluster", label: "Cluster", numeric: true }, { key: "customers", label: "Customers", numeric: true, render: (r) => fmtInt(r.customers) }, { key: "share_pct", label: "Share", numeric: true, render: (r) => fmtPct(r.share_pct) }, { key: "revenue_share_pct", label: "Revenue share", numeric: true, render: (r) => fmtPct(r.revenue_share_pct) }]} rows={profiles.map((p) => ({ ...p, id: p.cluster }))} />}>
									<HBarChart items={profiles.map((p) => ({ label: p.segment_label, value: p.customers, color: colorOf[p.cluster], tooltip: `Cluster ${p.cluster}: ${fmtInt(p.customers)} customers (${fmtPct(p.share_pct)}), ${fmtPct(p.revenue_share_pct)} of net revenue` }))} formatValue={(v) => `${fmtInt(v)} · ${fmtPct((v / profiles.reduce((s, p) => s + p.customers, 0)) * 100)}`} labelWidth={190} />
								</ChartFrame>
								<ChartFrame title="Share of net revenue">
									<HBarChart items={profiles.map((p) => ({ label: p.segment_label, value: p.revenue_share_pct, color: colorOf[p.cluster], tooltip: `${p.segment_label}: ${fmtPct(p.revenue_share_pct)} of revenue from ${fmtPct(p.share_pct)} of customers` }))} formatValue={(v) => fmtPct(v)} labelWidth={190} />
								</ChartFrame>
							</div>
						</Section>

						<Section eyebrow="Profiles" title="Cluster profile comparison" description="Median per cluster (means in tooltips and the table).">
							<div className="bi-grid-3">
								{metricBars("recency_days", "Recency · days since last purchase (lower = more recent)", (v) => `${fmtInt(v)} d`)}
								{metricBars("frequency", "Frequency · purchase invoices", (v) => fmtNum(v, v % 1 ? 1 : 0))}
								{metricBars("monetary", "Monetary · net spend (GBP)", fmtGbp)}
							</div>
							<DataTable
								caption="Cluster profiles"
								columns={[
									{ key: "segment_label", label: "Segment", render: (r) => <span className="bi-swatch-label"><i style={{ background: colorOf[r.cluster] }} />{r.segment_label}</span> },
									{ key: "customers", label: "Customers", numeric: true, render: (r) => `${fmtInt(r.customers)} (${fmtPct(r.share_pct)})` },
									{ key: "r", label: "Recency median / mean", numeric: true, render: (r) => `${fmtInt(r.recency_days_median)} / ${fmtInt(r.recency_days_mean)}` },
									{ key: "f", label: "Frequency median / mean", numeric: true, render: (r) => `${fmtNum(r.frequency_median, 0)} / ${fmtNum(r.frequency_mean, 1)}` },
									{ key: "m", label: "Monetary median / mean", numeric: true, render: (r) => `${fmtGbp(r.monetary_median)} / ${fmtGbp(r.monetary_mean)}` },
									{ key: "aov", label: "Avg order value", numeric: true, render: (r) => fmtGbp(r.avg_order_value_median) },
									{ key: "months", label: "Active months", numeric: true, render: (r) => fmtNum(r.active_months_median, 0) },
								]}
								rows={profiles.map((p) => ({ ...p, id: p.cluster }))}
							/>
						</Section>

						<Section eyebrow="Segment details" title="What each segment means and what to do">
							<div className="bi-segment-cards">
								{profiles.map((p) => (
									<article key={p.cluster} className="bi-segment-card" style={{ "--seg": colorOf[p.cluster] }}>
										<header><span aria-hidden="true" /><h4>{p.segment_label}</h4><small>Cluster {p.cluster}</small></header>
										<p>{fmtInt(p.customers)} customers ({fmtPct(p.share_pct)}) bought a median of <b>{fmtNum(p.frequency_median, 0)}</b> times, spent <b>{fmtGbp(p.monetary_median)}</b>, and last purchased <b>{fmtInt(p.recency_days_median)} days</b> before the reference date. They generate {fmtPct(p.revenue_share_pct)} of net revenue.</p>
										<p className="bi-segment-card__action"><b>Recommended action:</b> {p.recommended_action}</p>
										<p className="bi-segment-card__rule">Rule scores (population percentile of the cluster median): recency {fmtNum(p.rule_scores.recency_pct, 2)}, frequency {fmtNum(p.rule_scores.frequency_pct, 2)}, monetary {fmtNum(p.rule_scores.monetary_pct, 2)}</p>
									</article>
								))}
							</div>
							{data.label_notes.length > 0 && <ul className="bi-notes">{data.label_notes.map((n) => <li key={n.label}>{n.label}: {n.observation}</li>)}</ul>}
						</Section>

						<Section
							eyebrow="Distributions"
							title="RFM distributions (eligible customers)"
							actions={(
								<div className="bi-controls">
									<div className="bi-segmented" role="tablist" aria-label="Feature">
										{[["recency_days", "Recency"], ["frequency", "Frequency"], ["monetary", "Monetary"]].map(([key, label]) => <button key={key} type="button" role="tab" aria-selected={feature === key} onClick={() => setFeature(key)}>{label}</button>)}
									</div>
									<label>Scale<select value={scale} onChange={(event) => setScale(event.target.value)}><option value="log1p">log1p (as modelled)</option><option value="raw">Raw</option></select></label>
								</div>
							)}
						>
							<Histogram histogram={data.distributions[feature][scale]} formatX={feature === "monetary" ? fmtGbp : (v) => fmtCompact(v)} height={210} />
						</Section>

						<Section eyebrow="Customers" title="Customer table" description="Pseudonymous customer IDs with aggregated metrics only. No names, addresses or transaction lines are exposed.">
							<form className="bi-controls bi-controls--panel" onSubmit={(event) => event.preventDefault()}>
								<label>Search ID<input type="search" inputMode="numeric" value={searchInput} placeholder="e.g. 1234" onChange={(event) => setSearchInput(event.target.value.replace(/\D/g, ""))} /></label>
								<label>Segment
									<select value={filters.segment} onChange={(event) => setFilters((f) => ({ ...f, segment: event.target.value, page: 1 }))}>
										<option value="">All segments</option>
										{profiles.map((p) => <option key={p.cluster} value={p.segment_label}>{p.segment_label}</option>)}
									</select>
								</label>
								<label>Rows<select value={filters.pageSize} onChange={(event) => setFilters((f) => ({ ...f, pageSize: Number(event.target.value), page: 1 }))}>{[10, 25, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
							</form>
							<Status resource={customers} label="customers" empty={Object.assign((d) => d.total === 0, { message: "No customer matches this search and segment." })}>
								{(page) => (
									<>
										<DataTable
											caption="Customers"
											maxHeight="28rem"
											columns={[
												{ key: "customer_id", label: sortHeader("customer_id", "Customer") },
												{ key: "segment_label", label: "Segment", render: (r) => <span className="bi-swatch-label"><i style={{ background: colorOf[r.cluster] }} />{r.segment_label}</span> },
												{ key: "recency_days", label: sortHeader("recency_days", "Recency (d)"), numeric: true, render: (r) => fmtInt(r.recency_days) },
												{ key: "frequency", label: sortHeader("frequency", "Frequency"), numeric: true },
												{ key: "monetary", label: sortHeader("monetary", "Monetary"), numeric: true, render: (r) => fmtGbp(r.monetary) },
												{ key: "avg_order_value", label: sortHeader("avg_order_value", "Avg order"), numeric: true, render: (r) => fmtGbp(r.avg_order_value) },
												{ key: "unique_products", label: sortHeader("unique_products", "Products"), numeric: true },
												{ key: "active_months", label: sortHeader("active_months", "Months"), numeric: true },
											]}
											rows={page.customers.map((c) => ({ ...c, id: c.customer_id }))}
										/>
										<div className="bi-pager">
											<span>{fmtInt(page.total)} customers · page {page.page} of {page.pages}</span>
											<div>
												<button type="button" disabled={page.page <= 1} onClick={() => setFilters((f) => ({ ...f, page: 1 }))}>« First</button>
												<button type="button" disabled={page.page <= 1} onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}>‹ Prev</button>
												<button type="button" disabled={page.page >= page.pages} onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}>Next ›</button>
												<button type="button" disabled={page.page >= page.pages} onClick={() => setFilters((f) => ({ ...f, page: page.pages }))}>Last »</button>
											</div>
										</div>
									</>
								)}
							</Status>
						</Section>
						<SegmentScorer colorOf={colorOf} />
					</>
				);
			}}
		</Status>
	);
}

function SegmentScorer({ colorOf }) {
	const [values, setValues] = useState({ recency_days: 30, frequency: 4, monetary: 1200 });
	const [body, setBody] = useState(null);
	const result = useJson(`${API}/segmentation/assign`, { method: "POST", body, enabled: Boolean(body) });
	return (
		<Section eyebrow="Try the model" title="Assign a segment to an RFM profile" description="Scores a hypothetical customer with the saved log1p settings, scaler and K-means model.">
			<form className="bi-controls bi-controls--panel" onSubmit={(event) => { event.preventDefault(); setBody({ ...values }); }}>
				<label>Recency (days)<input type="number" min="0" max="5000" value={values.recency_days} onChange={(event) => setValues((v) => ({ ...v, recency_days: Number(event.target.value) }))} required /></label>
				<label>Frequency (invoices)<input type="number" min="1" max="10000" value={values.frequency} onChange={(event) => setValues((v) => ({ ...v, frequency: Number(event.target.value) }))} required /></label>
				<label>Monetary (GBP)<input type="number" min="0" step="0.01" value={values.monetary} onChange={(event) => setValues((v) => ({ ...v, monetary: Number(event.target.value) }))} required /></label>
				<button type="submit" className="review-primary-action bi-submit" disabled={result.status === "loading"}>{result.status === "loading" ? "Scoring…" : "Assign segment"}</button>
			</form>
			{body && (
				<Status resource={result} label="segment">
					{(data) => <p className="bi-result"><span className="bi-swatch-label"><i style={{ background: colorOf[data.cluster] }} /><b>{data.segment_label}</b></span> · cluster {data.cluster}</p>}
				</Status>
			)}
		</Section>
	);
}

function DataPage() {
	const quality = useJson(`${API}/data-quality`);
	const status = useJson(`${API}/training-status`);
	const segEval = useJson(`${API}/segmentation/evaluation`);
	const salesEval = useJson(`${API}/sales/evaluation`);
	const [dataset, setDataset] = useState("sales_forecasting");

	const stepColumns = [
		{ key: "step", label: "Operation", render: (r) => titleCase(r.step) },
		{ key: "rows_before", label: "Rows before", numeric: true, render: (r) => fmtInt(r.rows_before) },
		{ key: "rows_after", label: "Rows after", numeric: true, render: (r) => fmtInt(r.rows_after) },
		{ key: "rows_removed", label: "Removed / added", numeric: true, render: (r) => (r.rows_removed === 0 ? "0" : r.rows_removed > 0 ? `−${fmtInt(r.rows_removed)}` : `+${fmtInt(-r.rows_removed)}`) },
		{ key: "reason", label: "Reason / policy", render: (r) => <span className="bi-reason">{r.reason}{r.policy ? ` Policy: ${r.policy}` : ""}</span> },
	];

	return (
		<>
			<Status resource={quality} label="data reports">
				{(data) => {
					const dq = data.data_quality_report?.[dataset];
					const cleaning = data.cleaning_report?.[dataset];
					const transform = data.transformation_report?.[dataset];
					const manifest = data.dataset_manifest;
					return (
						<>
							<Section
								eyebrow="D / Data preparation"
								title="Raw datasets"
								description={manifest?.policy}
								actions={(
									<div className="bi-segmented" role="tablist" aria-label="Dataset">
										{[["sales_forecasting", "Store Sales"], ["customer_segmentation", "Online Retail"]].map(([key, label]) => <button key={key} type="button" role="tab" aria-selected={dataset === key} onClick={() => setDataset(key)}>{label}</button>)}
									</div>
								)}
							>
								{manifest ? (
									<DataTable
										caption="Dataset manifest"
										columns={[{ key: "file_name", label: "File" }, { key: "row_count", label: "Rows", numeric: true, render: (r) => fmtInt(r.row_count) }, { key: "column_names", label: "Columns", render: (r) => <span className="bi-mono bi-small">{r.column_names.join(", ")}</span> }, { key: "sha256", label: "SHA-256", render: (r) => <span className="bi-mono bi-small">{r.sha256.slice(0, 12)}…</span> }]}
										rows={(manifest.datasets.find((d) => (dataset === "sales_forecasting" ? d.source_url.includes("kaggle") : d.source_url.includes("uci")))?.files ?? []).map((f) => ({ ...f, id: f.file_name }))}
									/>
								) : <div className="review-empty"><strong>No manifest.</strong><span>Run `python -m src.manifest`.</span></div>}
								{manifest && (() => {
									const d = manifest.datasets.find((item) => (dataset === "sales_forecasting" ? item.source_url.includes("kaggle") : item.source_url.includes("uci")));
									return d ? <p className="bi-chart__note">{d.title} · source {d.source_url} · {d.license} · download date: {d.download_date}</p> : null;
								})()}
								{manifest?.missing_files?.length > 0 && <div className="review-error">Missing: {manifest.missing_files.map((m) => `${m.file} (${m.how_to_obtain})`).join("; ")}</div>}
							</Section>

							{dq && (
								<Section eyebrow="Quality" title="Before and after cleaning">
									<DataTable
										caption="Before after"
										columns={[{ key: "measure", label: "Measure" }, { key: "before", label: "Raw", numeric: true, render: (r) => fmtInt(r.before) }, { key: "after", label: "Cleaned", numeric: true, render: (r) => fmtInt(r.after) }]}
										rows={[
											{ id: "rows", measure: "Rows", before: dq.before.rows, after: dq.after.rows },
											{ id: "missing", measure: "Missing values (all columns)", before: dq.before.missing_values, after: dq.after.missing_values },
											{ id: "dupes", measure: "Exact duplicate rows", before: dq.before.duplicate_rows, after: dq.after.duplicate_rows },
										]}
									/>
									<ul className="bi-checklist bi-checklist--inline">{dq.checks.map((c) => <li key={c.check}><Badge tone={c.result}>{titleCase(c.check)}</Badge><span>{c.detail}</span></li>)}</ul>
									{dataset === "customer_segmentation" && cleaning?.missing_values_after && (
										<p className="bi-chart__note">Missing after cleaning: {Object.entries(cleaning.missing_values_after).filter(([, v]) => v.missing).map(([k, v]) => `${k} ${fmtInt(v.missing)} (${fmtPct(v.missing_pct)})`).join(" · ") || "none"}. Missing CustomerID lines are kept for revenue but excluded from segmentation; missing descriptions are not treated as invalid.</p>
									)}
								</Section>
							)}

							{cleaning && (
								<Section eyebrow="Cleaning" title="Rows removed or modified at each step">
									<DataTable caption="Cleaning steps" columns={stepColumns} rows={cleaning.steps.map((s) => ({ ...s, id: s.step }))} maxHeight="30rem" />
									{cleaning.record_type_counts && (
										<ChartFrame title="Retail lines by record type (after removing exact duplicates)">
											<HBarChart items={Object.entries(cleaning.record_type_counts).map(([label, value]) => ({ label: titleCase(label), value, color: label === "purchase" ? COLOR.model : COLOR.baseline, tooltip: cleaning.record_types?.[label] }))} />
										</ChartFrame>
									)}
									{cleaning.zero_sales_analysis && <p className="bi-chart__note">{cleaning.zero_sales_analysis.interpretation}</p>}
									{cleaning.revenue_policy && <p className="bi-chart__note"><b>Revenue policy.</b> {cleaning.revenue_policy}</p>}
								</Section>
							)}

							{transform && (
								<Section eyebrow="Transformation" title="Feature engineering steps">
									{transform.leakage_controls && <ul className="bi-notes">{transform.leakage_controls.map((item) => <li key={item}>{item}</li>)}</ul>}
									{transform.operations && (
										<DataTable caption="Operations" columns={[{ key: "operation", label: "Operation" }, { key: "detail", label: "Result / decision", render: (r) => <span className="bi-reason">{[typeof r.result === "string" ? r.result : r.result ? JSON.stringify(r.result) : "", r.features ? `features: ${r.features.join(", ")}` : "", r.fitted_on ? `fitted on ${r.fitted_on}` : "", r.decision ?? ""].filter(Boolean).join(" · ")}</span> }]} rows={transform.operations.map((o) => ({ ...o, id: o.operation }))} />
									)}
									<DataTable
										caption="Feature dictionary"
										maxHeight="22rem"
										columns={transform.feature_dictionary[0]?.purpose
											? [{ key: "feature", label: "Feature", render: (r) => <span className="bi-mono">{r.feature}</span> }, { key: "dtype", label: "Type" }, { key: "transformation", label: "Transformation" }, { key: "purpose", label: "Purpose" }]
											: [{ key: "feature", label: "Feature", render: (r) => <span className="bi-mono">{r.feature}</span> }, { key: "unit", label: "Unit" }, { key: "definition", label: "Definition" }]}
										rows={transform.feature_dictionary.map((f) => ({ ...f, id: f.feature }))}
									/>
								</Section>
							)}
						</>
					);
				}}
			</Status>

			<div className="bi-grid-2">
				<Section eyebrow="Before / after" title="Sales: baseline vs trained model (test)">
					<Status resource={salesEval} label="sales evaluation">
						{(data) => <MetricComparison metrics={data.basic.test.metrics} improvementVsNaive={data.basic.test.improvement_vs_seasonal_naive} />}
					</Status>
				</Section>
				<Section eyebrow="Before / after" title="Segmentation: raw vs preprocessed features">
					<Status resource={segEval} label="segmentation evaluation">
						{({ evaluation }) => {
							const c = evaluation.comparison;
							return (
								<>
									<DataTable
										caption="Segmentation comparison"
										columns={[{ key: "measure", label: `Measure (K = ${c.k}, ${fmtInt(c.customer_population)} customers)` }, { key: "before", label: "Raw features", numeric: true }, { key: "after", label: "log1p + scaled", numeric: true }]}
										rows={[
											{ id: "s", measure: "Silhouette", before: fmtNum(c.before_preprocessing.silhouette, 3), after: fmtNum(c.after_preprocessing.silhouette, 3) },
											{ id: "x", measure: "Silhouette of these labels in the other space", before: fmtNum(c.before_preprocessing.silhouette_of_these_labels_in_processed_space, 3), after: fmtNum(c.after_preprocessing.silhouette_of_these_labels_in_raw_space, 3) },
											{ id: "i", measure: "Inertia (own feature space)", before: fmtCompact(c.before_preprocessing.inertia), after: fmtNum(c.after_preprocessing.inertia, 0) },
											{ id: "z", measure: "Cluster sizes", before: c.before_preprocessing.cluster_sizes.join(" / "), after: c.after_preprocessing.cluster_sizes.join(" / ") },
										]}
									/>
									<p className="bi-chart__note">{c.interpretation}</p>
									<p className="bi-chart__note">Stability: seed ARI {fmtNum(evaluation.stability.seed_ari_mean, 3)}, subsample ARI {fmtNum(evaluation.stability.subsample_ari_mean, 3)} (1 = identical partitions). {evaluation.note}</p>
								</>
							);
						}}
					</Status>
				</Section>
			</div>

			<Status resource={segEval} label="K search">
				{({ evaluation }) => {
					const raw = evaluation.k_search.raw_features.filter((r) => r.valid);
					const processed = evaluation.k_search.processed_features.filter((r) => r.valid);
					const ks = processed.map((r) => `K=${r.k}`);
					const silhouette = [
						{ key: "raw", label: "Raw features", color: COLOR.baseline, values: raw.map((r) => r.silhouette) },
						{ key: "processed", label: "log1p + scaled", color: COLOR.model, values: processed.map((r) => r.silhouette) },
					];
					return (
						<div className="bi-grid-2">
							<Section eyebrow="Model selection" title="Silhouette by K" description={evaluation.k_search.selection.rule}>
								<ChartFrame title={`Selected K = ${evaluation.k_search.selection.selected_k}`} legend={silhouette.map((s) => ({ label: s.label, color: s.color, box: true }))} table={() => <DataTable columns={[{ key: "k", label: "K" }, { key: "raw", label: "Raw silhouette", numeric: true }, { key: "processed", label: "Processed silhouette", numeric: true }, { key: "share", label: "Smallest cluster (processed)", numeric: true }]} rows={processed.map((r, i) => ({ id: r.k, k: r.k, raw: fmtNum(raw[i]?.silhouette, 3), processed: fmtNum(r.silhouette, 3), share: fmtPct(r.min_cluster_share * 100) }))} />}>
									<ColumnChart categories={ks} series={silhouette} formatY={(v) => fmtNum(v, 2)} height={200} />
								</ChartFrame>
							</Section>
							<Section eyebrow="Model selection" title="Elbow curve (processed features)" description={METRIC_HELP.inertia}>
								<ChartFrame title="Inertia by K" table={() => <DataTable columns={[{ key: "k", label: "K" }, { key: "inertia", label: "Inertia", numeric: true }]} rows={processed.map((r) => ({ id: r.k, k: r.k, inertia: fmtNum(r.inertia, 0) }))} />}>
									<ColumnChart categories={ks} series={[{ key: "inertia", label: "Inertia", color: COLOR.model, values: processed.map((r) => r.inertia) }]} height={200} />
								</ChartFrame>
							</Section>
						</div>
					);
				}}
			</Status>

			<Section eyebrow="Training history" title="Model and dataset versions">
				<Status resource={status} label="training status">
					{(data) => (
						<>
							<TrainingList models={data.models} />
							<DataTable
								caption="Versions"
								columns={[{ key: "model", label: "Artifact set" }, { key: "dataset", label: "Dataset version (file hash)", render: (r) => <span className="bi-mono bi-small">{r.dataset}</span> }, { key: "env", label: "Environment", render: (r) => <span className="bi-mono bi-small">{r.env}</span> }, { key: "command", label: "Reproduce with", render: (r) => <code className="bi-small">{r.command}</code> }]}
								rows={Object.entries(data.models).map(([key, m]) => ({ id: key, model: titleCase(key), dataset: m.dataset ? Object.entries(m.dataset.files ?? {}).map(([f, h]) => `${f}:${h}`).join(" ") : "—", env: m.environment ? `py ${m.environment.python} · sklearn ${m.environment["scikit-learn"]} · pandas ${m.environment.pandas}` : "—", command: m.command }))}
							/>
							<p className="bi-chart__note">{data.note}</p>
						</>
					)}
				</Status>
				<Status resource={quality} label="reports">
					{(data) => <p className="bi-chart__note">Written reports in module5_business_intelligence/reports: {data.written_reports.join(", ") || "none"}.</p>}
				</Status>
			</Section>
		</>
	);
}

/* ---------- workspace ---------- */

export default function BusinessIntelligenceWorkspace({ onClose }) {
	const [tab, setTab] = useState("overview");
	const health = useJson(`${API}/health`);
	const dialogRef = useRef(null);
	const scrollRef = useRef(null);

	useEffect(() => {
		const onKeyDown = (event) => event.key === "Escape" && onClose();
		dialogRef.current?.focus();
		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [onClose]);

	const navigate = (id) => {
		setTab(id);
		scrollRef.current?.scrollTo({ top: 0 });
	};

	const statusLabel = health.status === "ready"
		? (health.data.ready ? "Random Forest + K-means · ready" : "Models missing · run pipelines")
		: health.status === "error" ? "BI API offline" : "Checking BI API…";

	return (
		<div className="dialog-backdrop dialog-backdrop--project" onMouseDown={(event) => {
			if (event.target === event.currentTarget) onClose();
		}}>
			<section ref={dialogRef} className="review-workspace bi-workspace" role="dialog" aria-modal="true" aria-labelledby="bi-workspace-title" tabIndex={-1}>
				<header className="review-workspace__header">
					<div><p className="eyebrow">Cerebro / Module 5 · Business intelligence</p><h2 id="bi-workspace-title">Business Intelligence Workspace</h2></div>
					<div className="review-workspace__actions">
						<span className={`review-workspace__status${health.status === "error" || (health.data && !health.data.ready) ? " bi-status--offline" : ""}`}>{statusLabel}</span>
						<button className="project-dialog__close" aria-label="Close business intelligence workspace" onClick={onClose}>×</button>
					</div>
				</header>
				<div className="review-workspace__scroll" ref={scrollRef}>
					<nav className="bi-tabs" role="tablist" aria-label="Module 5 pages">
						{TABS.map((item, index) => (
							<button key={item.id} type="button" role="tab" aria-selected={tab === item.id} onClick={() => navigate(item.id)}>
								<span>{String(index + 1).padStart(2, "0")}</span>{item.label}
							</button>
						))}
					</nav>
					{health.status === "error" && (
						<div className="bi-page"><div className="review-error" role="alert">{health.error} Start it with <code>..\rag_service\.venv\Scripts\python.exe -m uvicorn api:app --port 8002</code> inside module5_business_intelligence/. <button type="button" className="bi-link-button" onClick={health.reload}>Retry</button></div></div>
					)}
					{health.status !== "error" && (
						<div className="bi-page" role="tabpanel">
							{tab === "overview" && <OverviewPage onNavigate={navigate} />}
							{tab === "sales" && <SalesPage />}
							{tab === "segments" && <SegmentsPage />}
							{tab === "data" && <DataPage />}
						</div>
					)}
				</div>
			</section>
		</div>
	);
}
