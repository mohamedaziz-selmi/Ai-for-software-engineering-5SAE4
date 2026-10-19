import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { api } from "./api.js";
import Assistant from "./Assistant.jsx";
import Help from "./Help.jsx";
import Review from "./Review.jsx";
import { Field, Tag, cap, readStored, withTransition, writeStored } from "./ui.jsx";
import "./assistant-workspace.css";

// The module's own interface, standalone at /assistant/. "Back to dashboard" returns to the Cerebro dashboard
// ("/" through the gateway); a host could still mount it and pass onClose.
const PAGES = [
	{ id: "assistant", label: "Assistant", hint: "Ask the agreed documents", title: "Project assistant" },
	{ id: "review", label: "Delivery review", hint: "Check a deliverable", title: "Delivery review" },
	{ id: "help", label: "Help", hint: "FAQ and support", title: "Help and support" },
];
const THEMES = { auto: "Auto theme", dark: "Dark", light: "Light" };
const MODEL_STATE = { up: "ready", model_missing: "not installed", down: "offline" };

function useTheme() {
	const [theme, setTheme] = useState(() => (readStored("assistant.theme") in THEMES ? readStored("assistant.theme") : "auto"));
	useEffect(() => { writeStored("assistant.theme", theme); }, [theme]);
	const order = Object.keys(THEMES);
	const next = () => withTransition(() => flushSync(() => setTheme((t) => order[(order.indexOf(t) + 1) % order.length])));
	return [theme, next];
}

export default function AssistantWorkspace({ onClose }) {
	const [health, setHealth] = useState({ status: "loading" });
	const [identities, setIdentities] = useState([]);
	const [notice, setNotice] = useState("");
	const [user, setUser] = useState(() => readStored("assistant.demoUser") || "");
	const [projects, setProjects] = useState([]);
	const [projectId, setProjectId] = useState("");
	const [tab, setTab] = useState("assistant");
	const [theme, nextTheme] = useTheme();
	const navRef = useRef(null);
	const [indicator, setIndicator] = useState(null);

	const loadHealth = useCallback(() => {
		api("/health").then((data) => setHealth({ status: "ready", data })).catch((e) => setHealth({ status: "error", error: e.message }));
	}, []);

	useEffect(() => {
		const timer = setInterval(loadHealth, 30000); // keep the status honest (e.g. model stopped for training)
		return () => clearInterval(timer);
	}, [loadHealth]);

	useEffect(() => {
		loadHealth();
		api("/demo/identities").then((d) => { setIdentities(d.identities); setNotice(d.notice); }).catch(() => {});
	}, [loadHealth]);

	useEffect(() => {
		if (!user) return;
		writeStored("assistant.demoUser", user);
		api("/projects", { user })
			.then((d) => { setProjects(d.projects); setProjectId((current) => d.projects.some((p) => p.id === current) ? current : d.projects[0]?.id ?? ""); })
			.catch(() => { setProjects([]); setProjectId(""); });
	}, [user]);

	// Page changes cross-fade (View Transitions where supported); the rail's indicator slides to the active page.
	const navigate = (id) => {
		if (id === tab) return;
		withTransition(() => flushSync(() => setTab(id)));
		window.scrollTo({ top: 0 });
	};
	useLayoutEffect(() => {
		const active = navRef.current?.querySelector('[aria-selected="true"]');
		if (active) setIndicator({ x: active.offsetLeft, y: active.offsetTop, w: active.offsetWidth, h: active.offsetHeight });
	}, [tab]);

	const h = health.data;
	const page = PAGES.find((p) => p.id === tab);
	const state = health.status === "error" || (h && h.assistant.local !== "up") ? "down" : h ? "up" : "checking";
	const statusLabel = health.status === "error" ? "Assistant API offline"
		: !h ? "Checking the assistant API…"
			: h.assistant.local === "up" ? "Local model ready" : `Local model ${MODEL_STATE[h.assistant.local] ?? h.assistant.local}`;
	const project = projects.find((p) => p.id === projectId);
	const role = identities.find((i) => i.id === user)?.role;
	const needsProject = tab !== "help";

	return (
		<div className="ad-app" data-theme={theme === "auto" ? undefined : theme}>
			<aside className="ad-rail">
				{onClose
					? <button type="button" className="ad-back ad-link" onClick={onClose}>Close</button>
					: <a className="ad-back" href="/">&larr; Cerebro dashboard</a>}
				<div className="ad-brand"><strong>AI Assistant</strong><span>and Delivery Review</span></div>
				<nav className="ad-nav" role="tablist" aria-orientation="vertical" aria-label="Module pages" ref={navRef}>
					{indicator && <span className="ad-nav__indicator" aria-hidden="true" style={{ transform: `translate(${indicator.x}px, ${indicator.y}px)`, width: indicator.w, height: indicator.h }} />}
					{PAGES.map((p) => (
						<button key={p.id} type="button" role="tab" id={`ad-tab-${p.id}`} aria-selected={tab === p.id} aria-controls="ad-page" onClick={() => navigate(p.id)}>
							<b>{p.label}</b><span>{p.hint}</span>
						</button>
					))}
				</nav>
				{h && (
					<section className="ad-system" aria-label="System status">
						<h2>System</h2>
						<dl>
							<dt>Base</dt><dd>{h.assistant.model}, {MODEL_STATE[h.assistant.local] ?? h.assistant.local}</dd>
							{h.assistant.models?.raft && <><dt>RAFT</dt><dd>{h.assistant.models.raft.tag}, {MODEL_STATE[h.assistant.models.raft.status] ?? h.assistant.models.raft.status}</dd></>}
							<dt>Review</dt><dd>{h.review.model ?? "unavailable"}, {h.review.status}</dd>
							<dt>Fallback</dt><dd>{h.backup.status.replace("_", " ")}</dd>
							<dt>Search</dt><dd>{h.embeddings.model.split("/").pop()}, {h.database.documents} docs, {h.database.vectors} vectors</dd>
						</dl>
						<p>{notice || "Demo identity selection, not authentication."}</p>
					</section>
				)}
			</aside>
			<div className="ad-stage">
				<header className="ad-top">
					<h1>{page.title}</h1>
					<div className="ad-context">
						<Field label="Demo identity (not a login)">
							<select value={user} onChange={(e) => setUser(e.target.value)}>
								<option value="" disabled>Choose…</option>
								{identities.map((i) => <option key={i.id} value={i.id}>{i.display_name}</option>)}
							</select>
						</Field>
						<Field label="Project">
							<select value={projectId} onChange={(e) => setProjectId(e.target.value)} disabled={!projects.length}>
								{!projects.length && <option value="">No project for this identity</option>}
								{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
							</select>
						</Field>
						{project && <Tag title="Your role on this project">{cap(project.my_role)}</Tag>}
					</div>
					<div className="ad-tools">
						<span className="ad-status" data-state={state} role="status">{statusLabel}</span>
						<button type="button" className="ad-btn ad-btn--sm" onClick={nextTheme} title="Change theme">{THEMES[theme]}</button>
					</div>
				</header>
				<main className="ad-page" id="ad-page" role="tabpanel" aria-labelledby={`ad-tab-${tab}`}>
					{health.status === "error" ? (
						<div className="ad-alert" role="alert">
							{health.error} Start it with <code>.\scripts\run_backend.ps1</code> inside module_assistant_delivery/ (API on port 8003).{" "}
							<button type="button" className="ad-link" onClick={loadHealth}>Retry</button>
						</div>
					) : needsProject && (!user || !project) ? (
						<div className="ad-empty">
							<strong>{user ? "This identity has no project." : "Choose a demo identity to start."}</strong>
							<span>Use the identity and project menus at the top.</span>
						</div>
					) : (
						<>
							{tab === "assistant" && (
								<Assistant key={`${user}-${projectId}`} user={user} projectId={projectId} role={project.my_role} models={h?.assistant.models}
									backupStatus={h?.backup.status} onActivity={loadHealth} />
							)}
							{tab === "review" && <Review key={`${user}-${projectId}`} user={user} project={project} reviewHealth={h?.review} />}
							{tab === "help" && <Help user={user} role={role} projectId={projectId} />}
						</>
					)}
				</main>
			</div>
		</div>
	);
}
