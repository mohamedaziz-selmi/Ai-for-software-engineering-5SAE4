import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { advisorExamples } from "./advisor-examples.js";
import { cancelResearch, fetchHealth, resetResearch, startResearch, useAdvisorRun } from "./advisor-run.js";
import { Markdown } from "./markdown.jsx";

const MIN_CHARACTERS = 10;
const MAX_CHARACTERS = 2000;

const TOOL_LABELS = {
	search_web: "Web",
	search_github_repositories: "GitHub",
	inspect_github_repository: "GitHub",
	search_huggingface_datasets: "Datasets",
};

const TOOL_HEADLINES = {
	search_web: "Searching the web",
	search_github_repositories: "Searching GitHub",
	inspect_github_repository: "Reading a GitHub repository",
	search_huggingface_datasets: "Searching Hugging Face datasets",
};

const TIPS = [
	"The advisor only researches. It never downloads, installs or runs anything on your computer.",
	"Every link in the guide was returned by a real search tool. Links the model made up are removed.",
	"The model runs locally through Ollama. Only short search queries go to the web, GitHub and Hugging Face.",
	"Evidence is judged by code, not by the model, so the agent cannot declare victory without sources.",
	"Datasets are checked for language, license and size before they are recommended.",
	"Sections A, C and G come straight from your request and the retrieved evidence. B, D, E and F are model advice.",
	"A small local model thinks carefully, so a single step can take a minute. The wait is normal.",
];

const ORIGIN_LABELS = {
	tool_evidence: "From tool evidence",
	derived_from_request: "Derived from your request",
	model_recommendation: "Model recommendation",
};

const KIND_LABELS = {
	dataset: "Dataset",
	repository: "Repository",
	repository_detail: "Repository · inspected",
	web_page: "Web page",
};

function Arrow() {
	return (
		<svg aria-hidden="true" className="arrow-icon arrow-icon--right" viewBox="0 0 24 24" fill="none">
			<path d="M4 12h15M13 5l7 7-7 7" stroke="currentColor" strokeWidth="1.6" />
		</svg>
	);
}

function formatClock(totalSeconds) {
	const seconds = Math.max(0, Math.floor(totalSeconds));
	return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function formatNumber(value) {
	return typeof value === "number" ? value.toLocaleString("en-US") : String(value);
}

function humanize(text) {
	const spaced = String(text ?? "").replace(/_/g, " ").trim();
	return spaced ? spaced[0].toUpperCase() + spaced.slice(1) : "Unknown";
}

// ----------------------------------------------------------------------------- progress

// What the live events say so far: which phase the agent is in, and how far along it is.
function summarizeProgress(events) {
	let toolsDone = 0;
	let sources = 0;
	let sectionsDone = 0;
	let activeTool = null;
	for (const event of events) {
		if (event.stage === "tools") {
			const running = event.message.match(/^running (\w+)/);
			if (running) activeTool = running[1];
			else if (/ finished in /.test(event.message)) {
				toolsDone += 1;
				activeTool = null;
			}
		} else if (event.stage === "evaluate") {
			const found = event.message.match(/^(\d+) source/);
			if (found) sources = Number(found[1]);
			activeTool = null;
		} else if (event.stage === "report" && /^section [A-Z] (written|NOT written)/.test(event.message)) {
			sectionsDone += 1;
		}
	}
	const last = events[events.length - 1];
	const phase = !last || last.stage === "plan" ? "plan" : last.stage === "report" ? "report" : "research";
	return { phase, toolsDone, sources, sectionsDone, activeTool, last };
}

// The bar moves with real events, and creeps slowly between them so a long model step never looks frozen.
function progressPercent(summary, secondsSinceEvent) {
	let base;
	let span;
	if (summary.phase === "plan") {
		base = 2;
		span = 6;
	} else if (summary.phase === "research") {
		base = 8 + Math.min(summary.toolsDone, 6) * 7;
		span = 7;
	} else {
		base = 56 + Math.min(summary.sectionsDone, 4) * 10;
		span = 10;
	}
	const creep = span * (1 - Math.exp(-secondsSinceEvent / 45)) * 0.9;
	return Math.min(98, base + creep);
}

const STEPS = [
	{ id: "plan", label: "Understand", detail: "Reading the request" },
	{ id: "research", label: "Research", detail: "Searching and checking evidence" },
	{ id: "report", label: "Write", detail: "Writing the guide" },
];

// ----------------------------------------------------------------------------- loading screen

function OrbitAnimation({ activeTool }) {
	const active = TOOL_LABELS[activeTool];
	return (
		<svg className="advisor-orbit" viewBox="0 0 240 240" role="img" aria-label="The advisor is researching">
			<defs>
				<radialGradient id="advisor-core" cx="50%" cy="40%" r="65%">
					<stop offset="0" stopColor="#f2edff" />
					<stop offset="1" stopColor="#8f7fc8" />
				</radialGradient>
			</defs>
			<g className="advisor-orbit__spin advisor-orbit__spin--slow">
				<circle className="advisor-orbit__ring advisor-orbit__ring--outer" cx="120" cy="120" r="106" />
			</g>
			<g className="advisor-orbit__spin advisor-orbit__spin--reverse">
				<circle className="advisor-orbit__ring advisor-orbit__ring--mid" cx="120" cy="120" r="80" />
			</g>
			<g className="advisor-orbit__spin advisor-orbit__spin--fast">
				<circle className="advisor-orbit__ring advisor-orbit__ring--inner" cx="120" cy="120" r="54" />
			</g>
			<g className="advisor-orbit__spin advisor-orbit__spin--slow">
				<g className={`advisor-orbit__satellite advisor-orbit__satellite--web${active === "Web" ? " is-active" : ""}`}>
					<circle cx="226" cy="120" r="8" />
				</g>
			</g>
			<g className="advisor-orbit__spin advisor-orbit__spin--reverse">
				<g className={`advisor-orbit__satellite advisor-orbit__satellite--github${active === "GitHub" ? " is-active" : ""}`}>
					<circle cx="40" cy="120" r="8" />
				</g>
			</g>
			<g className="advisor-orbit__spin advisor-orbit__spin--fast">
				<g className={`advisor-orbit__satellite advisor-orbit__satellite--datasets${active === "Datasets" ? " is-active" : ""}`}>
					<circle cx="120" cy="66" r="7" />
				</g>
			</g>
			<circle className="advisor-orbit__pulse" cx="120" cy="120" r="30" />
			<circle className="advisor-orbit__core" cx="120" cy="120" r="26" fill="url(#advisor-core)" />
			<path
				className="advisor-orbit__mark"
				d="M120 104c1.6 8.6 6.4 13.4 15 15-8.6 1.6-13.4 6.4-15 15-1.6-8.6-6.4-13.4-15-15 8.6-1.6 13.4-6.4 15-15Z"
			/>
		</svg>
	);
}

function RunningView({ run }) {
	const [now, setNow] = useState(() => Date.now());
	const [tipIndex, setTipIndex] = useState(() => Math.floor(Math.random() * TIPS.length));
	const lastEventAt = useRef(Date.now());
	const eventCount = run.events.length;

	useEffect(() => {
		const timer = window.setInterval(() => setNow(Date.now()), 1000);
		return () => window.clearInterval(timer);
	}, []);

	useEffect(() => {
		const timer = window.setInterval(() => setTipIndex((value) => (value + 1) % TIPS.length), 7000);
		return () => window.clearInterval(timer);
	}, []);

	useEffect(() => {
		lastEventAt.current = Date.now();
	}, [eventCount]);

	const summary = useMemo(() => summarizeProgress(run.events), [run.events]);
	const elapsed = (now - run.startedAt) / 1000;
	const percent = progressPercent(summary, (now - lastEventAt.current) / 1000);
	const stepIndex = STEPS.findIndex((step) => step.id === summary.phase);
	const recent = run.events.slice(-6).reverse();
	const headline = {
		plan: "Reading your request",
		research: TOOL_HEADLINES[summary.activeTool] ?? "Researching your project",
		report: `Writing the guide · section ${Math.min(summary.sectionsDone + 1, 4)} of 4`,
	}[summary.phase];

	return (
		<div className="advisor-running" role="status" aria-live="polite">
			<div className="advisor-running__stage">
				<OrbitAnimation activeTool={summary.activeTool} />
				<ul className="advisor-running__tools" aria-label="Research tools">
					{["Web", "GitHub", "Datasets"].map((label) => (
						<li
							key={label}
							className={TOOL_LABELS[summary.activeTool] === label ? "is-active" : ""}
						>
							{label}
						</li>
					))}
				</ul>
			</div>

			<div className="advisor-running__panel">
				<p className="eyebrow">Researching · {formatClock(elapsed)}</p>
				<h3 key={headline}>{headline}</h3>
				<p className="advisor-running__live">
					{summary.last ? summary.last.message : "Starting the research agent"}
					<span className="advisor-running__caret" aria-hidden="true" />
				</p>

				<div
					className="advisor-progress"
					role="progressbar"
					aria-valuemin={0}
					aria-valuemax={100}
					aria-valuenow={Math.round(percent)}
					aria-label="Research progress"
				>
					<span style={{ width: `${percent}%` }} />
				</div>

				<ol className="advisor-steps">
					{STEPS.map((step, index) => (
						<li
							key={step.id}
							className={index < stepIndex ? "is-done" : index === stepIndex ? "is-active" : ""}
						>
							<span className="advisor-steps__dot" aria-hidden="true">{index < stepIndex ? "✓" : index + 1}</span>
							<span>
								<strong>{step.label}</strong>
								<small>
									{step.id === "research" && (summary.toolsDone > 0 || summary.sources > 0)
										? `${summary.toolsDone} search${summary.toolsDone === 1 ? "" : "es"} · ${summary.sources} source${summary.sources === 1 ? "" : "s"}`
										: step.id === "report" && summary.phase === "report"
											? `${summary.sectionsDone} of 4 sections`
											: step.detail}
								</small>
							</span>
						</li>
					))}
				</ol>

				<ul className="advisor-feed" aria-label="Recent activity">
					{recent.map((event, index) => (
						<li key={run.events.length - index} className={index === 0 ? "is-new" : ""}>
							<span className="advisor-feed__stage">{event.stage}</span>
							<span className="advisor-feed__text">{event.message}</span>
							<span className="advisor-feed__time">{formatClock(event.elapsed_seconds)}</span>
						</li>
					))}
				</ul>

				<p className="advisor-tip" key={tipIndex}>
					<span aria-hidden="true">✳</span> {TIPS[tipIndex]}
				</p>

				<div className="advisor-running__actions">
					<span>Usually 1–3 minutes on a laptop GPU.</span>
					<button type="button" className="advisor-link-button" onClick={cancelResearch}>
						Stop waiting
					</button>
				</div>
			</div>
		</div>
	);
}

// ----------------------------------------------------------------------------- compose

function ComposeView({ run, health }) {
	const [text, setText] = useState(run.description);
	const textareaRef = useRef(null);
	const trimmed = text.trim();
	const tooShort = trimmed.length < MIN_CHARACTERS;
	const offline = health.state === "error" || (health.state === "ready" && !health.ready);
	const canSubmit = !tooShort && !offline;

	const submit = (event) => {
		event.preventDefault();
		if (canSubmit) void startResearch(trimmed);
	};

	const fillExample = (example) => {
		setText(example.brief);
		textareaRef.current?.focus();
	};

	return (
		<div className="advisor-compose">
			<form className="advisor-compose__form" onSubmit={submit}>
				<p className="eyebrow">01 / Describe the project</p>
				<h3>What does the client want you to build?</h3>
				<p className="advisor-muted">
					Write the job the way a client would. The advisor researches libraries, repositories, datasets and
					documentation, then returns a sourced implementation guide.
				</p>
				<label className="chat-tool__field chat-tool__field--wide">
					<span className="visually-hidden">Project description</span>
					<textarea
						ref={textareaRef}
						value={text}
						onChange={(event) => setText(event.target.value)}
						placeholder="e.g. A local bakery wants an online shop with a cart and card payments, built with Laravel…"
						rows={8}
						maxLength={MAX_CHARACTERS}
					/>
				</label>
				<div className="advisor-compose__meta">
					<span className={tooShort && trimmed.length > 0 ? "is-warning" : ""}>
						{trimmed.length > 0 && tooShort
							? `Add a little more detail (${MIN_CHARACTERS - trimmed.length} more characters)`
							: `${text.length} / ${MAX_CHARACTERS}`}
					</span>
					{text && (
						<button type="button" className="advisor-link-button" onClick={() => setText("")}>
							Clear
						</button>
					)}
				</div>
				<button className="chat-tool__submit advisor-compose__submit" type="submit" disabled={!canSubmit}>
					Research this project <Arrow />
				</button>
				{run.notice && <p className="advisor-note" role="status">{run.notice}</p>}
				{health.state === "ready" && health.problems.length > 0 && (
					<ul className="advisor-problems">
						{health.problems.map((problem) => <li key={problem}>{problem}</li>)}
					</ul>
				)}
				{health.state === "error" && (
					<p className="chat-tool__error" role="alert">{health.message}</p>
				)}
			</form>

			<aside className="advisor-examples" aria-label="Freelance example projects">
				<p className="eyebrow">02 / Or start from an example</p>
				<h3>Freelance briefs</h3>
				<ul>
					{advisorExamples.map((example) => (
						<li key={example.id}>
							<button
								type="button"
								className={`advisor-example${text === example.brief ? " is-selected" : ""}`}
								onClick={() => fillExample(example)}
							>
								<span className="advisor-example__top">
									<strong>{example.title}</strong>
									<span>{example.budget} · {example.duration}</span>
								</span>
								<span className="advisor-example__client">{example.client}</span>
								<span className="advisor-example__stack">
									{example.stack.map((item) => <span key={item}>{item}</span>)}
								</span>
							</button>
						</li>
					))}
				</ul>
			</aside>
		</div>
	);
}

// ----------------------------------------------------------------------------- result

function metadataChips(source) {
	const data = source.metadata ?? {};
	const chips = [];
	if (typeof data.stars === "number") chips.push(`★ ${formatNumber(data.stars)}`);
	if (typeof data.downloads === "number") chips.push(`${formatNumber(data.downloads)} downloads`);
	if (typeof data.likes === "number") chips.push(`${formatNumber(data.likes)} likes`);
	if (data.language) chips.push(data.language);
	if (data.license && data.license !== "not stated") chips.push(data.license);
	if (data.size_category) chips.push(data.size_category);
	if (Array.isArray(data.languages) && data.languages.length) chips.push(data.languages.join(", "));
	if (data.last_push) chips.push(`pushed ${data.last_push}`);
	else if (data.last_modified) chips.push(`updated ${data.last_modified}`);
	if (data.domain) chips.push(data.domain);
	return chips;
}

function SourceCard({ source, focused }) {
	const chips = metadataChips(source);
	const warnings = [
		...(source.flags ?? []),
		...(source.metadata?.possibly_stale ? ["possibly stale"] : []),
		...(source.metadata?.license === "not stated" ? ["license not stated"] : []),
	];
	return (
		<article id={`advisor-source-${source.id}`} className={`advisor-source${focused ? " is-focused" : ""}`}>
			<header>
				<span className="advisor-source__id">{source.id}</span>
				<span className="advisor-source__kind">{KIND_LABELS[source.kind] ?? source.kind}</span>
			</header>
			<h4>
				<a href={source.url} target="_blank" rel="noreferrer noopener">{source.title || source.url}</a>
			</h4>
			{source.summary && <p>{source.summary.length > 220 ? `${source.summary.slice(0, 220).trimEnd()}…` : source.summary}</p>}
			{(chips.length > 0 || warnings.length > 0) && (
				<ul className="advisor-chips">
					{chips.map((chip) => <li key={chip}>{chip}</li>)}
					{warnings.map((warning) => <li key={warning} className="is-warning">{warning}</li>)}
				</ul>
			)}
		</article>
	);
}

function ActivityTab({ result }) {
	return (
		<div className="advisor-activity">
			{result.evaluation && (
				<section>
					<h4>Evidence coverage</h4>
					<p className="advisor-muted">
						Computed by code from the retrieved sources, not by the model.
						{result.evaluation.sufficient ? " Coverage was judged sufficient." : " Some areas stayed open."}
					</p>
					<ul className="advisor-coverage">
						{result.evaluation.items.map((item) => (
							<li key={item.area}>
								<span className={`advisor-status advisor-status--${item.status}`}>{humanize(item.status)}</span>
								<div>
									<strong>{item.label}</strong>
									<small>{item.detail}</small>
								</div>
							</li>
						))}
					</ul>
				</section>
			)}
			<section>
				<h4>Tool calls</h4>
				<ol className="advisor-timeline">
					{result.tool_history.map((entry) => (
						<li key={entry.step} className={`is-${entry.status}`}>
							<div className="advisor-timeline__head">
								<strong>{entry.tool.replace(/_/g, " ")}</strong>
								<span>
									{entry.status === "skipped" ? "skipped" : `${entry.duration_seconds.toFixed(1)} s`}
									{entry.status === "ok" ? ` · ${entry.result_count} result${entry.result_count === 1 ? "" : "s"}` : ""}
								</span>
							</div>
							<code>{Object.values(entry.arguments).join(" · ") || "no arguments"}</code>
							{entry.error && <small className="is-warning">{entry.error.message}</small>}
							{entry.notes.map((note) => <small key={note}>{note}</small>)}
						</li>
					))}
				</ol>
			</section>
		</div>
	);
}

function ResultView({ run, onReset }) {
	const { result } = run;
	const [tab, setTab] = useState("guide");
	const [focusedSource, setFocusedSource] = useState("");
	const [copied, setCopied] = useState(false);
	const tabsRef = useRef(null);
	const { report, stats } = result;

	useEffect(() => {
		if (tab !== "sources" || !focusedSource) return;
		document.getElementById(`advisor-source-${focusedSource}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
	}, [tab, focusedSource]);

	const jumpToSource = useCallback((id) => {
		setFocusedSource(id);
		setTab("sources");
	}, []);

	const changeTab = (id) => {
		setTab(id);
		setFocusedSource("");
		tabsRef.current?.scrollIntoView({ block: "start" });
	};

	const jumpToSection = (id) => {
		document.getElementById(`advisor-section-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
	};

	const copyGuide = async () => {
		try {
			await navigator.clipboard.writeText(report.markdown);
			setCopied(true);
			window.setTimeout(() => setCopied(false), 1800);
		} catch {
			// the clipboard is blocked; the Download button still works
		}
	};

	const downloadGuide = () => {
		const slug = (result.plan?.objective ?? result.project_description)
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, "-")
			.replace(/^-+|-+$/g, "")
			.slice(0, 48);
		const url = URL.createObjectURL(new Blob([report.markdown], { type: "text/markdown;charset=utf-8" }));
		const link = document.createElement("a");
		link.href = url;
		link.download = `implementation-guide-${slug || "project"}.md`;
		link.click();
		window.setTimeout(() => URL.revokeObjectURL(url), 1000);
	};

	const validation = report.validation ?? {};
	const checks = [
		{ label: "invented links removed", count: validation.removed_urls?.length ?? 0 },
		{ label: "unknown citations removed", count: validation.removed_citations?.length ?? 0 },
		{ label: "claims to verify by hand", count: validation.unverified_claims?.length ?? 0 },
		{ label: "sections not written", count: validation.sections_not_generated?.length ?? 0 },
	];

	return (
		<div className="advisor-result">
			<div className="advisor-result__summary">
				<div>
					<p className="eyebrow">Implementation guide</p>
					<h3>{result.plan?.objective ?? report.title}</h3>
				</div>
				<div className="advisor-result__actions">
					<button type="button" onClick={copyGuide}>{copied ? "Copied" : "Copy Markdown"}</button>
					<button type="button" onClick={downloadGuide}>Download .md</button>
					<button type="button" className="is-primary" onClick={onReset}>New research</button>
				</div>
			</div>

			<ul className="advisor-stats" aria-label="Run statistics">
				<li><strong>{formatClock(stats.elapsed_seconds)}</strong><span>elapsed</span></li>
				<li><strong>{result.sources.length}</strong><span>sources</span></li>
				<li><strong>{stats.tool_calls_executed}</strong><span>tool calls</span></li>
				<li><strong>{stats.agent_turns}</strong><span>agent turns</span></li>
				<li><strong>{stats.model}</strong><span>{humanize(result.stop_reason).toLowerCase()}</span></li>
			</ul>

			<div className="advisor-tabs" role="tablist" aria-label="Result sections" ref={tabsRef}>
				{[
					["guide", "Guide"],
					["sources", `Sources (${result.sources.length})`],
					["activity", "How it was researched"],
				].map(([id, label]) => (
					<button
						key={id}
						type="button"
						role="tab"
						aria-selected={tab === id}
						className={tab === id ? "is-active" : ""}
						onClick={() => changeTab(id)}
					>
						{label}
					</button>
				))}
			</div>

			{tab === "guide" && (
				<div className="advisor-guide">
					<nav className="advisor-sectionnav" aria-label="Jump to section">
						{report.sections.map((section) => (
							<button key={section.id} type="button" title={section.title} onClick={() => jumpToSection(section.id)}>
								<strong>{section.id}</strong>
								<span>{section.title}</span>
							</button>
						))}
					</nav>
					{report.sections.map((section) => (
						<section key={section.id} id={`advisor-section-${section.id}`} className="advisor-section">
							<header>
								<span className="advisor-section__letter">{section.id}</span>
								<h4>{section.title}</h4>
								<span className={`advisor-origin advisor-origin--${section.origin}`}>{ORIGIN_LABELS[section.origin]}</span>
							</header>
							<Markdown text={section.content} onCite={jumpToSource} />
						</section>
					))}
					<section className="advisor-trust">
						<h4>Checks and limitations</h4>
						<ul className="advisor-chips">
							{checks.map((check) => (
								<li key={check.label} className={check.count > 0 ? "is-warning" : "is-ok"}>
									{check.count} {check.label}
								</li>
							))}
						</ul>
						{validation.unverified_claims?.length > 0 && (
							<ul className="advisor-trust__list">
								{validation.unverified_claims.map((claim) => <li key={claim}>{claim}</li>)}
							</ul>
						)}
						{report.limitations.length > 0 ? (
							<ul className="advisor-trust__list">
								{report.limitations.map((item) => <li key={item}>{item}</li>)}
							</ul>
						) : (
							<p className="advisor-muted">No limitations were recorded for this run.</p>
						)}
					</section>
				</div>
			)}

			{tab === "sources" && (
				<div className="advisor-sources">
					{result.sources.length === 0 && <p className="advisor-muted">No sources were retrieved for this run.</p>}
					{result.sources.map((source) => (
						<SourceCard key={source.id} source={source} focused={source.id === focusedSource} />
					))}
				</div>
			)}

			{tab === "activity" && <ActivityTab result={result} />}
		</div>
	);
}

// ----------------------------------------------------------------------------- error

function ErrorView({ run }) {
	const busy = run.error?.status === 429;
	return (
		<div className="advisor-error" role="alert">
			<span className="advisor-error__mark" aria-hidden="true">!</span>
			<h3>{busy ? "The advisor is busy" : "The research did not finish"}</h3>
			<p>{run.error?.message}</p>
			<div className="advisor-error__actions">
				<button type="button" className="chat-tool__submit" onClick={() => void startResearch(run.description)}>
					Try again <Arrow />
				</button>
				<button type="button" className="advisor-link-button" onClick={resetResearch}>
					Edit the request
				</button>
			</div>
		</div>
	);
}

// ----------------------------------------------------------------------------- floating pill

// Shown on the gallery while a run continues in the background (or has just finished) with the dialog closed.
export function AdvisorPill({ run, onOpen }) {
	const [now, setNow] = useState(() => Date.now());
	const running = run.phase === "running";

	useEffect(() => {
		if (!running) return undefined;
		const timer = window.setInterval(() => setNow(Date.now()), 1000);
		return () => window.clearInterval(timer);
	}, [running]);

	return (
		<button type="button" className={`advisor-pill${running ? "" : " advisor-pill--done"}`} onClick={onOpen}>
			<span className="advisor-pill__dot" aria-hidden="true" />
			{running ? "Advisor is researching" : "Your guide is ready"}
			{running && <span className="advisor-pill__time">{formatClock((now - run.startedAt) / 1000)}</span>}
		</button>
	);
}

// ----------------------------------------------------------------------------- dialog

export default function AdvisorDialog({ onClose }) {
	const run = useAdvisorRun();
	const [expanded, setExpanded] = useState(false);
	const [health, setHealth] = useState({ state: "loading", ready: false, model: "", problems: [], message: "" });
	const dialogRef = useRef(null);

	useEffect(() => {
		const previousOverflow = document.body.style.overflow;
		document.body.style.overflow = "hidden";
		dialogRef.current?.focus();

		const onKeyDown = (event) => {
			if (event.key === "Escape") onClose();
		};
		window.addEventListener("keydown", onKeyDown);
		return () => {
			document.body.style.overflow = previousOverflow;
			window.removeEventListener("keydown", onKeyDown);
		};
	}, [onClose]);

	const checkHealth = useCallback(async (signal) => {
		setHealth((current) => ({ ...current, state: "loading" }));
		try {
			const data = await fetchHealth(signal);
			setHealth({
				state: "ready",
				ready: Boolean(data.ollama?.reachable && data.ollama?.model_installed),
				model: data.ollama?.model ?? "",
				problems: data.problems ?? [],
				message: "",
			});
		} catch (error) {
			if (error.name === "AbortError") return;
			setHealth({
				state: "error",
				ready: false,
				model: "",
				problems: [],
				message: "Could not reach the advisor API. Start it with `uv run uvicorn app.main:app` in the agentic-freelance-advisor folder.",
			});
		}
	}, []);

	// The health check is slow while the model is generating, so it only runs when no research is in progress.
	const idle = run.phase === "idle" || run.phase === "error";
	useEffect(() => {
		if (!idle) return undefined;
		const controller = new AbortController();
		void checkHealth(controller.signal);
		return () => controller.abort();
	}, [idle, checkHealth]);

	let pill = { text: "Checking advisor…", tone: "loading" };
	if (run.phase === "running") pill = { text: "Researching…", tone: "ready" };
	else if (run.phase === "done") pill = { text: "Guide ready", tone: "ready" };
	else if (health.state === "ready" && health.ready) pill = { text: `Ollama · ${health.model}`, tone: "ready" };
	else if (health.state === "ready") pill = { text: "Ollama · Not ready", tone: "error" };
	else if (health.state === "error") pill = { text: "Advisor · Offline", tone: "error" };

	return (
		<div
			className="dialog-backdrop dialog-backdrop--project"
			onMouseDown={(event) => {
				if (event.target === event.currentTarget) onClose();
			}}
		>
			<section
				ref={dialogRef}
				className={`project-dialog project-dialog--advisor${expanded ? " project-dialog--expanded" : ""}`}
				role="dialog"
				aria-modal="true"
				aria-labelledby="advisor-dialog-title"
				tabIndex={-1}
			>
				<header className="chat-dialog__header">
					<div>
						<p className="eyebrow">Cerebro / Research agent</p>
						<h2 id="advisor-dialog-title">Freelance Advisor</h2>
					</div>
					<div className="chat-dialog__header-actions">
						<span className={`chat-dialog__connection chat-dialog__connection--${pill.tone}`}>{pill.text}</span>
						<button
							className="project-dialog__expand"
							aria-label={expanded ? "Restore advisor window size" : "Expand advisor window"}
							onClick={() => setExpanded((value) => !value)}
						>
							{expanded ? "↙" : "↗"}
						</button>
						<button className="project-dialog__close" aria-label="Close advisor" onClick={onClose}>
							×
						</button>
					</div>
				</header>
				<div className="advisor-body">
					{run.phase === "running" && <RunningView run={run} />}
					{run.phase === "done" && <ResultView run={run} onReset={resetResearch} />}
					{run.phase === "error" && <ErrorView run={run} />}
					{run.phase === "idle" && <ComposeView run={run} health={health} />}
				</div>
			</section>
		</div>
	);
}
