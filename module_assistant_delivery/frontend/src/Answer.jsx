import { Tag, Thinking } from "./ui.jsx";

// One assistant answer: status, scope verdict, verified quotes and which model answered. Model text is
// rendered as plain text (never HTML).
const STATUS = {
	answered: { label: "Answered from the documents", tone: "pass", card: "" },
	not_found: { label: "Not in the project documents", tone: "neutral", card: "ad-answer--muted" },
	not_found_after_verification: { label: "Withheld: citations failed verification", tone: "warn", card: "ad-answer--muted" },
	no_documents: { label: "No documents in this project yet", tone: "neutral", card: "ad-answer--muted" },
};
const SCOPE = { in_scope: ["In scope", "pass"], out_of_scope: ["Out of scope", "fail"], ambiguous: ["Ambiguous", "warn"] };
const REASON = {
	simulated_failure: "skipped by the failure drill", unavailable: "unreachable", timeout: "timed out", bad_response: "invalid output",
	rate_limited: "rate limited", auth: "key rejected", model_missing: "not installed",
};

// Which model a stored attempt refers to: the RAFT model's Ollama tag contains "raft"; "backup" is the hosted fallback.
function modelName(servedBy, model) {
	if (servedBy === "backup") return "Hosted fallback";
	return /raft/i.test(model || "") ? "RAFT fine-tuned" : "Base + RAG";
}

function sectionPath(c) {
	const path = c.section || "";
	return path.startsWith(c.document_title) ? path.slice(c.document_title.length).replace(/^\s*>\s*/, "") : path;
}

function Sources({ citations }) {
	if (!citations.length) return null;
	return (
		<div className="ad-sources">
			<h3>Sources <span>quotes verified against the document</span></h3>
			{citations.map((c) => (
				<figure key={`${c.chunk_id}-${c.quote}`} className="ad-source">
					<figcaption>
						<b>{c.label}</b>
						<strong>{sectionPath(c) || c.document_title}</strong>
						<span>{c.page ? `page ${c.page}, ` : ""}lines {c.line_start}-{c.line_end}, v{c.document_version}</span>
					</figcaption>
					<blockquote><mark>{c.quote}</mark></blockquote>
					<small>{c.document_title}</small>
				</figure>
			))}
		</div>
	);
}

function Route({ r }) {
	if (!r.model) return null;
	const steps = [
		...(r.attempts || []).map((a) => ({ name: modelName(a.served_by, a.model), note: REASON[a.error] ?? a.error, failed: true })),
		{ name: modelName(r.served_by, r.model), note: r.latency_ms ? `answered in ${(r.latency_ms / 1000).toFixed(1)} s` : "answered" },
	];
	return (
		<ol className="ad-route" aria-label="Which model answered">
			{steps.map((s, i) => <li key={i} className={s.failed ? "is-failed" : "is-served"}><span><b>{s.name}</b>{s.note}</span></li>)}
		</ol>
	);
}

export function AnswerCard({ turn }) {
	if (turn.error) return <div className="ad-alert" role="alert">{turn.error}</div>;
	if (!turn.result) {
		return (
			<div className="ad-answer">
				<Thinking label="Reading the project documents…" detail="Searching the agreed documents, writing an answer, then checking every quote against its clause."
					hint="Still working. The first answer after a model switch, or after a pause, is slower while the model loads." />
			</div>
		);
	}
	const r = turn.result;
	const status = STATUS[r.status] ?? { label: r.status, tone: "neutral", card: "" };
	return (
		<div className={`ad-answer ${status.card}`}>
			<div className="ad-answer__head">
				<Tag tone={status.tone}>{status.label}</Tag>
				{r.scope_verdict && <Tag tone={SCOPE[r.scope_verdict][1]}>{SCOPE[r.scope_verdict][0]}</Tag>}
				{r.served_by === "local_backup" && <Tag tone="warn">Backup model answered</Tag>}
				{r.served_by === "backup" && <Tag tone="warn">Hosted fallback answered</Tag>}
			</div>
			<p className="ad-answer__text ad-reveal">{r.answer}</p>
			<Sources citations={r.citations || []} />
			{r.dropped_citations?.length > 0 && (
				<p className="ad-answer__note">{r.dropped_citations.length} citation(s) removed: the quote was not found in the cited passage.</p>
			)}
			<footer className="ad-answer__meta">
				<Route r={r} />
				{r.retrieval?.length > 0 && (
					<details>
						<summary>Searched passages ({r.retrieval.length}), prompt {r.prompt_version}</summary>
						<ul>{r.retrieval.map((x) => <li key={x.chunk_id}><b>{x.label}</b> {x.score.toFixed(3)} {x.section}</li>)}</ul>
					</details>
				)}
			</footer>
		</div>
	);
}
