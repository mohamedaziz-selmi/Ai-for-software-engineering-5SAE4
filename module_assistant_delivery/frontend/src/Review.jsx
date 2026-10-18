import { useCallback, useEffect, useRef, useState } from "react";
import { AnswerCard } from "./Answer.jsx";
import { api } from "./api.js";
import { Badge, Loading, Section } from "./ui.jsx";

const SEVERITIES = ["blocker", "major", "minor", "info"];
const SEVERITY_TONE = { blocker: "fail", major: "warn", minor: "neutral", info: "neutral" };
const VERDICT = { conforms: ["Conforms", "pass"], partial: ["Partial", "warn"], violates: ["Violates", "fail"], cannot_determine: ["Cannot determine", "neutral"] };
const PRIORITY_TONE = { must: "fail", should: "warn", could: "neutral" };

function Requirements({ user, projectId }) {
	const [items, setItems] = useState([]);
	const [error, setError] = useState("");
	const load = useCallback(() => {
		api(`/requirements?project_id=${encodeURIComponent(projectId)}`, { user }).then((d) => setItems(d.requirements)).catch((e) => setError(e.message));
	}, [user, projectId]);
	useEffect(load, [load]);
	async function extract() {
		try {
			setItems((await api(`/requirements/extract?project_id=${encodeURIComponent(projectId)}`, { user, method: "POST" })).requirements);
		} catch (e) {
			setError(e.message);
		}
	}
	return (
		<Section eyebrow="Checked by the review" title="Requirements" description="Read from the REQ- and NN- clauses of the agreed documents. Non-negotiables count as MUST."
			actions={<button type="button" className="ad-small-action" onClick={extract}>Extract from documents</button>}>
			{items.length === 0 ? <p className="ad-muted">None yet.</p> : (
				<ul className="ad-list ad-requirements">
					{items.map((r) => (
						<li key={r.id}>
							<span className="ad-row"><Badge tone={PRIORITY_TONE[r.priority]}>{r.priority}</Badge><strong>{r.code}</strong></span>
							<span className="ad-muted">{r.text}</span>
						</li>
					))}
				</ul>
			)}
			{error && <div className="review-error" role="alert">{error}</div>}
		</Section>
	);
}

function Submit({ user, project, onSubmitted }) {
	const [busy, setBusy] = useState(false);
	const [error, setError] = useState("");
	const filesRef = useRef(null);
	if (project.my_role !== "freelancer") return null;
	async function onSubmit(event) {
		event.preventDefault();
		const files = [...(filesRef.current?.files ?? [])];
		if (!files.length) return;
		const form = new FormData();
		form.append("project_id", project.id);
		form.append("milestone_id", event.target.milestone.value);
		form.append("note", event.target.note.value);
		for (const f of files) form.append("files", f, f.webkitRelativePath ? f.webkitRelativePath.split("/").slice(1).join("/") : f.name);
		setBusy(true);
		setError("");
		try {
			await api("/deliverables", { user, method: "POST", form });
			filesRef.current.value = "";
			onSubmitted();
		} catch (e) {
			setError(e.message);
		} finally {
			setBusy(false);
		}
	}
	return (
		<Section eyebrow="Freelancer" title="Submit a deliverable" description="Text and source files only (max 50 files, 200 KB each). Code is never executed.">
			<form className="ad-form ad-controls" onSubmit={onSubmit}>
				<label>Milestone<select name="milestone">{project.milestones.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
				<label>Folder<input ref={filesRef} type="file" webkitdirectory="" multiple required /></label>
				<label>Note (optional)<input name="note" type="text" maxLength={1000} /></label>
				<button type="submit" className="review-primary-action" disabled={busy}>{busy ? "Uploading…" : "Submit"}</button>
			</form>
			{error && <div className="review-error" role="alert">{error}</div>}
		</Section>
	);
}

function Finding({ f, user, canDecide, onDecided }) {
	const [comment, setComment] = useState(f.client_comment || "");
	const [error, setError] = useState("");
	const [explain, setExplain] = useState(null);
	async function decide(decision) {
		try {
			await api(`/findings/${f.id}`, { user, method: "PATCH", json: { client_decision: decision, client_comment: comment } });
			onDecided();
		} catch (e) {
			setError(e.message);
		}
	}
	async function onExplain() {
		setExplain({ id: f.id });
		try {
			setExplain({ id: f.id, result: await api(`/findings/${f.id}/explain`, { user, method: "POST" }) });
		} catch (e) {
			setExplain({ id: f.id, error: e.message });
		}
	}
	return (
		<li className={`ad-finding ad-finding--${f.severity}`}>
			<header>
				<Badge tone={SEVERITY_TONE[f.severity]}>{f.severity}</Badge>
				<strong>{f.requirement_code}</strong>
				<span className="ad-mono">{f.file_path} · lines {f.line_start}–{f.line_end}</span>
				<Badge tone={f.client_decision === "accepted" ? "pass" : f.client_decision === "dismissed" ? "neutral" : "ink"}>{f.client_decision}</Badge>
			</header>
			<p>{f.explanation}</p>
			{f.suggested_fix && <p><strong>Suggested fix:</strong> {f.suggested_fix}</p>}
			<pre className="ad-evidence"><code>{f.evidence_quote}</code></pre>
			<span className="ad-muted">Evidence verified at this location · model confidence {Math.round((f.confidence ?? 0) * 100)}%</span>
			<div className="ad-row">
				<button type="button" className="ad-link-button" onClick={onExplain} disabled={explain && !explain.result && !explain.error}>Explain this finding</button>
			</div>
			{explain && <AnswerCard turn={explain} />}
			{canDecide && (
				<div className="ad-decide">
					<input placeholder="Comment (optional)" value={comment} maxLength={2000} onChange={(e) => setComment(e.target.value)} aria-label="Comment" />
					<button type="button" className="ad-small-action" onClick={() => decide("accepted")}>Accept finding</button>
					<button type="button" className="ad-small-action" onClick={() => decide("dismissed")}>Dismiss</button>
				</div>
			)}
			{error && <div className="review-error" role="alert">{error}</div>}
		</li>
	);
}

function Report({ user, reviewId, isClient }) {
	const [review, setReview] = useState(null);
	const [error, setError] = useState("");
	const [severity, setSeverity] = useState("all");
	const [tick, setTick] = useState(0);
	useEffect(() => {
		let timer;
		const controller = new AbortController();
		api(`/reviews/${reviewId}`, { user, signal: controller.signal })
			.then((r) => {
				setReview(r);
				if (r.status === "pending" || r.status === "running") timer = setTimeout(() => setTick((t) => t + 1), 2500);
			})
			.catch((e) => e.name !== "AbortError" && setError(e.message));
		return () => { controller.abort(); clearTimeout(timer); };
	}, [user, reviewId, tick]);
	if (error) return <div className="review-error" role="alert">{error}</div>;
	if (!review) return <Loading>Loading review…</Loading>;
	if (review.status === "pending" || review.status === "running") {
		return <Loading>Review {review.status}: {review.requirement_results.length} requirement(s) judged so far…</Loading>;
	}
	const s = review.summary || {};
	const findings = review.findings.filter((f) => severity === "all" || f.severity === severity);
	const dropped = Object.values(s.dropped_unverified_findings || {}).reduce((a, b) => a + b, 0);
	return (
		<>
			<Section eyebrow={`${review.served_by} · ${review.model} · ${review.prompt_version}`} title="Conformance report">
				<p className="ad-notice">{review.advisory_notice}</p>
				{review.status === "failed" && <div className="review-error" role="alert">The review could not run ({review.error || "model unavailable"}). Try again when the local model is up.</div>}
				<div className="ad-tiles">
					{SEVERITIES.map((k) => <div key={k} className={`ad-tile ad-tile--${k}`}><span>{k}</span><b>{s.findings_by_severity?.[k] ?? 0}</b></div>)}
				</div>
				<div className="ad-table-wrap">
					<table className="ad-table">
						<thead><tr><th>Requirement</th><th>Priority</th><th>Verdict</th><th>Note</th></tr></thead>
						<tbody>
							{review.requirement_results.map((r) => (
								<tr key={r.requirement_id}>
									<td><strong>{r.code}</strong> <span className="ad-muted">{r.text}</span></td>
									<td><Badge tone={PRIORITY_TONE[r.priority]}>{r.priority}</Badge></td>
									<td>{r.status === "review_failed" ? <Badge tone="fail">Review failed</Badge> : <Badge tone={VERDICT[r.verdict][1]}>{VERDICT[r.verdict][0]}</Badge>}</td>
									<td className="ad-muted">{r.status !== "review_failed" ? r.note : ""}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
				{dropped > 0 && <p className="ad-muted">{dropped} finding(s) removed because their evidence was not found at the stated location.</p>}
			</Section>
			<Section eyebrow="Advisory" title={`Findings (${review.findings.length})`}
				actions={<label className="ad-controls">Severity<select value={severity} onChange={(e) => setSeverity(e.target.value)}><option value="all">All</option>{SEVERITIES.map((k) => <option key={k} value={k}>{k}</option>)}</select></label>}>
				<ul className="ad-list">
					{findings.map((f) => <Finding key={f.id} f={f} user={user} canDecide={isClient} onDecided={() => setTick((t) => t + 1)} />)}
				</ul>
			</Section>
		</>
	);
}

export default function Review({ user, project, reviewHealth }) {
	const [deliverables, setDeliverables] = useState([]);
	const [reviewId, setReviewId] = useState(null);
	const [refresh, setRefresh] = useState(0);
	const [error, setError] = useState("");
	useEffect(() => {
		api(`/deliverables?project_id=${encodeURIComponent(project.id)}`, { user }).then((d) => setDeliverables(d.deliverables)).catch((e) => setError(e.message));
	}, [user, project.id, refresh]);
	useEffect(() => setReviewId(null), [project.id]);
	async function start(id) {
		try {
			setReviewId((await api(`/deliverables/${id}/review`, { user, method: "POST" })).review_id);
			setRefresh((r) => r + 1);
		} catch (e) {
			setError(e.message);
		}
	}
	return (
		<div className="ad-split">
			<div className="ad-split__side">
				{reviewHealth?.status === "degraded" && (
					<div className="review-error" role="alert" style={{ marginTop: "1rem" }}>
						<strong>Delivery review unavailable.</strong> {reviewHealth.note}
					</div>
				)}
				<Submit user={user} project={project} onSubmitted={() => setRefresh((r) => r + 1)} />
				<Section eyebrow="Versions" title="Deliverables">
					{deliverables.length === 0 && <p className="ad-muted">No deliverable submitted yet.</p>}
					<ul className="ad-list">
						{deliverables.map((d) => (
							<li key={d.id}>
								<strong>{d.milestone_id} · v{d.version}</strong>
								<small>{d.file_count} files · {d.submitted_at.slice(0, 16).replace("T", " ")}</small>
								<span className="ad-row">
									<button type="button" className="ad-link-button" onClick={() => start(d.id)}>Run review</button>
									{d.latest_review_id && <button type="button" className="ad-link-button" onClick={() => setReviewId(d.latest_review_id)}>Open last review</button>}
								</span>
							</li>
						))}
					</ul>
					{error && <div className="review-error" role="alert">{error}</div>}
				</Section>
				<Requirements user={user} projectId={project.id} />
			</div>
			<div className="ad-split__main">
				{reviewId ? <Report key={reviewId} user={user} reviewId={reviewId} isClient={project.my_role === "client"} /> : (
					<Section eyebrow="Delivery review" title="Conformance report">
						<div className="review-empty"><strong>No review open.</strong><span>Submit a deliverable, then run a review. Findings are advisory: the client decides.</span></div>
					</Section>
				)}
			</div>
		</div>
	);
}
