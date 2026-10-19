import { useCallback, useEffect, useRef, useState } from "react";
import { AnswerCard } from "./Answer.jsx";
import { api } from "./api.js";
import { Field, Pending, Section, Tag, Thinking, cap } from "./ui.jsx";

const SEVERITIES = ["blocker", "major", "minor", "info"];
const SEVERITY_TONE = { blocker: "fail", major: "warn", minor: "neutral", info: "neutral" };
const VERDICT = { conforms: ["Conforms", "pass"], partial: ["Partial", "warn"], violates: ["Violates", "fail"], cannot_determine: ["Cannot determine", "neutral"] };
const PRIORITY_TONE = { must: "fail", should: "warn", could: "neutral" };
const DECISION = { pending: ["Awaiting the client", "neutral"], accepted: ["Accepted by the client", "pass"], changes_requested: ["Changes requested", "warn"] };

// The client's decision on the whole delivery; the review only advises it.
function DeliveryDecision({ deliverable, user, isClient, onDecided }) {
	const [comment, setComment] = useState(deliverable.client_comment || "");
	const [error, setError] = useState("");
	const [label, tone] = DECISION[deliverable.client_decision || "pending"];
	async function decide(decision) {
		try {
			await api(`/deliverables/${deliverable.id}/decision`, { user, method: "PATCH", json: { decision, comment } });
			onDecided();
		} catch (e) {
			setError(e.message);
		}
	}
	return (
		<Section title="Delivery decision" description={isClient ? "Your decision on this version. The findings above only advise it." : "The client decides on each delivered version."}>
			<div className="ad-decision">
				<Tag tone={tone}>{label}</Tag>
				{deliverable.decided_at && <small>{deliverable.decided_at.slice(0, 16).replace("T", " ")}</small>}
			</div>
			{!isClient && deliverable.client_comment && <p className="ad-notice">{deliverable.client_comment}</p>}
			{isClient && (
				<div className="ad-decide">
					<input className="ad-input" placeholder="Comment for the freelancer (optional)" value={comment} maxLength={2000}
						onChange={(e) => setComment(e.target.value)} aria-label="Comment for the freelancer" />
					<button type="button" className="ad-btn ad-btn--primary ad-btn--sm" onClick={() => decide("accepted")}>Accept delivery</button>
					<button type="button" className="ad-btn ad-btn--sm" onClick={() => decide("changes_requested")}>Request changes</button>
				</div>
			)}
			{error && <div className="ad-alert" role="alert">{error}</div>}
		</Section>
	);
}

function Requirement({ r, user, onSaved }) {
	const [editing, setEditing] = useState(false);
	const [error, setError] = useState("");
	async function save(event) {
		event.preventDefault();
		const f = event.target;
		try {
			await api(`/requirements/${r.id}`, { user, method: "PUT", json: { text: f.text.value, priority: f.priority.value } });
			setEditing(false);
			onSaved();
		} catch (e) {
			setError(e.message);
		}
	}
	return (
		<li>
			<span className="ad-row">
				<Tag tone={PRIORITY_TONE[r.priority]}>{cap(r.priority)}</Tag><strong>{r.code}</strong>
				{r.edited_by_user ? <Tag title="Edited by a project member; extraction keeps this text">Edited</Tag> : null}
				{!editing && <button type="button" className="ad-link ad-link--quiet" onClick={() => setEditing(true)}>Edit</button>}
			</span>
			{editing ? (
				<form className="ad-form ad-inline-form" onSubmit={save}>
					<Field label="Requirement"><textarea name="text" defaultValue={r.text} rows={3} required minLength={3} maxLength={2000} /></Field>
					<div className="ad-form__row">
						<Field label="Priority">
							<select name="priority" defaultValue={r.priority}><option value="must">Must</option><option value="should">Should</option><option value="could">Could</option></select>
						</Field>
						<div className="ad-row">
							<button type="submit" className="ad-btn ad-btn--primary ad-btn--sm">Save</button>
							<button type="button" className="ad-btn ad-btn--sm" onClick={() => setEditing(false)}>Cancel</button>
						</div>
					</div>
				</form>
			) : <span className="ad-muted">{r.text}</span>}
			{error && <div className="ad-alert" role="alert">{error}</div>}
		</li>
	);
}

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
		<Section title="Requirements" description="Read from the REQ- and NN- clauses of the agreed documents. Non-negotiables count as MUST. An edit is kept when you extract again."
			actions={<button type="button" className="ad-btn ad-btn--sm" onClick={extract}>Extract from documents</button>}>
			{items.length === 0 ? <p className="ad-muted">None yet.</p> : (
				<ul className="ad-list">
					{items.map((r) => <Requirement key={r.id} r={r} user={user} onSaved={load} />)}
				</ul>
			)}
			{error && <div className="ad-alert" role="alert">{error}</div>}
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
		<Section title="Submit a deliverable" description="Text and source files only (max 50 files, 200 KB each). Code is never executed.">
			<form className="ad-form" onSubmit={onSubmit}>
				<Field label="Milestone"><select name="milestone">{project.milestones.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select></Field>
				<Field label="Folder"><input ref={filesRef} type="file" webkitdirectory="" multiple required /></Field>
				<Field label="Note (optional)"><input name="note" type="text" maxLength={1000} /></Field>
				<button type="submit" className="ad-btn ad-btn--primary" disabled={busy}>{busy ? "Uploading…" : "Submit"}</button>
			</form>
			{error && <div className="ad-alert" role="alert">{error}</div>}
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
				<Tag tone={SEVERITY_TONE[f.severity]}>{cap(f.severity)}</Tag>
				<strong>{f.requirement_code}</strong>
				<span className="ad-mono">{f.file_path}, lines {f.line_start}-{f.line_end}</span>
				<Tag tone={f.client_decision === "accepted" ? "pass" : f.client_decision === "dismissed" ? "neutral" : "ink"}>{cap(f.client_decision)}</Tag>
			</header>
			<p>{f.explanation}</p>
			{f.suggested_fix && <p><strong>Suggested fix:</strong> {f.suggested_fix}</p>}
			<pre className="ad-evidence"><code>{f.evidence_quote}</code></pre>
			<span className="ad-muted">Evidence verified at this location. Model confidence {Math.round((f.confidence ?? 0) * 100)}%.</span>
			<div className="ad-row">
				<button type="button" className="ad-link" onClick={onExplain} disabled={explain && !explain.result && !explain.error}>Explain this finding</button>
			</div>
			{explain && <AnswerCard turn={explain} />}
			{canDecide && (
				<div className="ad-decide">
					<input className="ad-input" placeholder="Comment (optional)" value={comment} maxLength={2000} onChange={(e) => setComment(e.target.value)} aria-label="Comment" />
					<button type="button" className="ad-btn ad-btn--sm" onClick={() => decide("accepted")}>Accept finding</button>
					<button type="button" className="ad-btn ad-btn--sm" onClick={() => decide("dismissed")}>Dismiss</button>
				</div>
			)}
			{error && <div className="ad-alert" role="alert">{error}</div>}
		</li>
	);
}

function Report({ user, reviewId, isClient, deliverables, onDecided }) {
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
	if (error) return <div className="ad-alert" role="alert">{error}</div>;
	if (!review) return <Pending>Loading the review…</Pending>;
	if (review.status === "pending" || review.status === "running") {
		const { done = review.requirement_results.length, total = 0 } = review.progress || {};
		const pct = total ? Math.round((100 * done) / total) : 0;
		return (
			<Section title="Review in progress">
				<Thinking label={review.status === "pending" ? "Starting the review…" : `Judging requirement ${Math.min(done + 1, total || done + 1)} of ${total || "?"}`}
					detail="Each requirement is checked against the deliverable, and every quoted line is verified in code. This takes about 2 to 3 minutes.">
					<div className="ad-progress ad-progress--live" role="progressbar" aria-valuemin={0} aria-valuemax={total || undefined} aria-valuenow={done} aria-label="Requirements judged">
						<div className="ad-progress__bar" style={{ width: `${pct}%` }} />
					</div>
					<span className="ad-thinking__count">{done} of {total || "?"} done</span>
				</Thinking>
			</Section>
		);
	}
	const s = review.summary || {};
	const deliverable = deliverables.find((d) => d.id === review.deliverable_id);
	const findings = review.findings.filter((f) => severity === "all" || f.severity === severity);
	const dropped = Object.values(s.dropped_unverified_findings || {}).reduce((a, b) => a + b, 0);
	return (
		<>
			<Section title="Conformance report" description={`Judged by ${review.model} (${review.served_by}), prompt ${review.prompt_version}.`}>
				<p className="ad-notice">{review.advisory_notice}</p>
				{review.status === "failed" && <div className="ad-alert" role="alert">The review could not run ({review.error || "model unavailable"}). Try again in a moment.</div>}
				<div className="ad-tiles">
					{SEVERITIES.map((k) => <div key={k} className={`ad-tile ad-tile--${k}`}><span>{k}</span><b>{s.findings_by_severity?.[k] ?? 0}</b></div>)}
				</div>
				<div className="ad-table-wrap">
					<table className="ad-table">
						<thead><tr><th>Requirement</th><th>Priority</th><th>Verdict</th><th>Note</th></tr></thead>
						<tbody>
							{review.requirement_results.map((r) => (
								<tr key={r.requirement_id}>
									<td><strong>{r.code}</strong>{r.text}</td>
									<td><Tag tone={PRIORITY_TONE[r.priority]}>{cap(r.priority)}</Tag></td>
									<td>{r.status === "review_failed" ? <Tag tone="fail">Review failed</Tag> : <Tag tone={VERDICT[r.verdict][1]}>{VERDICT[r.verdict][0]}</Tag>}</td>
									<td className="ad-table__text">{r.status !== "review_failed" ? r.note : ""}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
				{dropped > 0 && <p className="ad-muted">{dropped} finding(s) removed because their evidence was not found at the stated location.</p>}
			</Section>
			<Section title={`Findings (${review.findings.length})`}
				actions={<Field label="Severity"><select value={severity} onChange={(e) => setSeverity(e.target.value)}><option value="all">All</option>{SEVERITIES.map((k) => <option key={k} value={k}>{k}</option>)}</select></Field>}>
				<ul className="ad-findings">
					{findings.map((f) => <Finding key={f.id} f={f} user={user} canDecide={isClient} onDecided={() => setTick((t) => t + 1)} />)}
				</ul>
			</Section>
			{deliverable && <DeliveryDecision key={deliverable.client_decision} deliverable={deliverable} user={user} isClient={isClient} onDecided={onDecided} />}
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
					<div className="ad-alert" role="alert"><strong>Delivery review unavailable.</strong> {reviewHealth.note}</div>
				)}
				<Submit user={user} project={project} onSubmitted={() => setRefresh((r) => r + 1)} />
				<Section title="Deliverables">
					{deliverables.length === 0 && <p className="ad-muted">No deliverable submitted yet.</p>}
					<ul className="ad-list">
						{deliverables.map((d) => (
							<li key={d.id}>
								<span className="ad-row"><strong>{d.milestone_id}, version {d.version}</strong><Tag tone={DECISION[d.client_decision || "pending"][1]}>{DECISION[d.client_decision || "pending"][0]}</Tag></span>
								<small>{d.file_count} files, submitted {d.submitted_at.slice(0, 16).replace("T", " ")}</small>
								<span className="ad-row">
									<button type="button" className="ad-link" onClick={() => start(d.id)}>Run review</button>
									{d.latest_review_id && <button type="button" className="ad-link" onClick={() => setReviewId(d.latest_review_id)}>Open last review</button>}
								</span>
							</li>
						))}
					</ul>
					{error && <div className="ad-alert" role="alert">{error}</div>}
				</Section>
				<Requirements user={user} projectId={project.id} />
			</div>
			<div className="ad-split__main">
				{reviewId ? <Report key={reviewId} user={user} reviewId={reviewId} isClient={project.my_role === "client"} deliverables={deliverables} onDecided={() => setRefresh((r) => r + 1)} /> : (
					<Section title="Conformance report">
						<div className="ad-empty"><strong>No review open.</strong><span>Submit a deliverable, then run a review. Findings are advisory: the client decides.</span></div>
					</Section>
				)}
			</div>
		</div>
	);
}
