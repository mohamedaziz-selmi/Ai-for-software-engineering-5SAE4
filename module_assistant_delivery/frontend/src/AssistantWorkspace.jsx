import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import Assistant from "./Assistant.jsx";
import Help from "./Help.jsx";
import Review from "./Review.jsx";
import { readStored, writeStored } from "./ui.jsx";
import "./template-shell.css";
import "./assistant-workspace.css";

// Same structure as the template's Business Intelligence workspace (review-workspace shell, eyebrow
// path, status pill, numbered tabs). Standalone at /assistant/ the close button returns to the Cerebro
// dashboard ("/" through the gateway); a host can mount it in a dialog by passing onClose.
const TABS = [
	{ id: "assistant", label: "Project assistant" },
	{ id: "review", label: "Delivery review" },
	{ id: "help", label: "Help & support" },
];

export default function AssistantWorkspace({ onClose }) {
	const [health, setHealth] = useState({ status: "loading" });
	const [identities, setIdentities] = useState([]);
	const [notice, setNotice] = useState("");
	const [user, setUser] = useState(() => readStored("assistant.demoUser") || "");
	const [projects, setProjects] = useState([]);
	const [projectId, setProjectId] = useState("");
	const [tab, setTab] = useState("assistant");
	const scrollRef = useRef(null);

	const loadHealth = useCallback(() => {
		api("/health").then((data) => setHealth({ status: "ready", data })).catch((e) => setHealth({ status: "error", error: e.message }));
	}, []);

	useEffect(() => {
		const timer = setInterval(loadHealth, 30000); // keep the status pill honest (e.g. model stopped for training)
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

	const navigate = (id) => {
		setTab(id);
		scrollRef.current?.scrollTo({ top: 0 });
	};

	const h = health.data;
	const offline = health.status === "error" || (h && h.assistant.local !== "up");
	const statusLabel = health.status === "error" ? "Assistant API offline"
		: !h ? "Checking assistant API…"
			: h.assistant.local === "up" ? `${h.assistant.model} · local · ready`
				: `Local model ${h.assistant.local.replace("_", " ")}`;
	const project = projects.find((p) => p.id === projectId);
	const role = identities.find((i) => i.id === user)?.role;
	const needsProject = tab !== "help";

	return (
		<section className="review-workspace ad-workspace" aria-labelledby="ad-workspace-title">
			<header className="review-workspace__header">
				<div><p className="eyebrow">Cerebro / AI assistant · delivery review</p><h2 id="ad-workspace-title">Project Assistant Workspace</h2></div>
				<div className="review-workspace__actions">
					<span className={`review-workspace__status${offline ? " ad-status--offline" : ""}`}>{statusLabel}</span>
					{onClose
						? <button type="button" className="project-dialog__close" aria-label="Close assistant workspace" onClick={onClose}>×</button>
						: <a className="project-dialog__close" href="/" aria-label="Back to the Cerebro dashboard">×</a>}
				</div>
			</header>
			<div className="review-workspace__scroll" ref={scrollRef}>
				<nav className="ad-tabs" role="tablist" aria-label="Assistant workspace pages">
					{TABS.map((item, index) => (
						<button key={item.id} type="button" role="tab" aria-selected={tab === item.id} onClick={() => navigate(item.id)}>
							<span>{String(index + 1).padStart(2, "0")}</span>{item.label}
						</button>
					))}
				</nav>
				<div className="ad-context ad-controls">
					<label>Demo identity
						<select value={user} onChange={(e) => setUser(e.target.value)}>
							<option value="" disabled>Choose…</option>
							{identities.map((i) => <option key={i.id} value={i.id}>{i.display_name}</option>)}
						</select>
					</label>
					<label>Project
						<select value={projectId} onChange={(e) => setProjectId(e.target.value)} disabled={!projects.length}>
							{!projects.length && <option value="">No project for this identity</option>}
							{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
						</select>
					</label>
					<p className="ad-context__note">
						<strong>Not authentication.</strong> {notice || "Demo identity selection: any visitor can choose any identity."}
						{project ? ` Your role on this project: ${project.my_role}.` : ""}
					</p>
				</div>
				{health.status === "error" ? (
					<div className="ad-body"><div className="review-error" role="alert" style={{ marginTop: "1rem" }}>
						{health.error} Start it with <code>.\scripts\run_backend.ps1</code> inside module_assistant_delivery/ (API on port 8003). <button type="button" className="ad-link-button" onClick={loadHealth}>Retry</button>
					</div></div>
				) : (
					<div className="ad-body" role="tabpanel">
						{needsProject && (!user || !project) ? (
							<div className="review-empty" style={{ marginTop: "1rem" }}><strong>{user ? "This identity has no project." : "Choose a demo identity to start."}</strong><span>Pick an identity and a project in the bar above.</span></div>
						) : (
							<>
								{tab === "assistant" && <Assistant key={`${user}-${projectId}`} user={user} projectId={projectId} onActivity={loadHealth} />}
								{tab === "review" && <Review key={`${user}-${projectId}`} user={user} project={project} reviewHealth={h?.review} />}
								{tab === "help" && <Help user={user} role={role} projectId={projectId} />}
							</>
						)}
					</div>
				)}
				{h && (
					<footer className="ad-footer">
						Assistant {h.assistant.model} ({h.assistant.local}) · review {h.review.provider} ({h.review.status}) · fallback {h.backup.status} ·
						embeddings {h.embeddings.model} ({h.embeddings.status}) · {h.database.documents} documents, {h.database.vectors} vectors ·
						identity {h.identity.mode}, authentication {String(h.identity.authentication)}
					</footer>
				)}
			</div>
		</section>
	);
}
