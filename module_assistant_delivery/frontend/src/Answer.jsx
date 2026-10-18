import { Badge, Loading } from "./ui.jsx";

// One assistant answer: status, scope verdict, verified sources and provenance. Model text is rendered
// as plain text (never HTML).
const STATUS = {
	answered: { label: "Answered from the documents", tone: "pass", card: "" },
	not_found: { label: "Not found in the project documents", tone: "neutral", card: "ad-answer--muted" },
	not_found_after_verification: { label: "Withheld: citations failed verification", tone: "warn", card: "ad-answer--warn" },
	no_documents: { label: "No documents in this project yet", tone: "neutral", card: "ad-answer--muted" },
};
const SCOPE = { in_scope: ["In scope", "pass"], out_of_scope: ["Out of scope", "fail"], ambiguous: ["Ambiguous", "warn"] };

function Sources({ citations }) {
	if (!citations.length) return null;
	return (
		<div className="ad-sources">
			<p className="eyebrow">Sources · quotes checked against the document</p>
			<ul className="evidence-list">
				{citations.map((c) => (
					<li key={`${c.chunk_id}-${c.quote}`}>
						<details>
							<summary>
								<span>{c.label}</span>
								<strong>{c.section}</strong>
								<span>{c.page ? `p. ${c.page} · ` : ""}lines {c.line_start}–{c.line_end} · v{c.document_version}</span>
							</summary>
							<blockquote>{c.quote}</blockquote>
							<span>{c.document_title}</span>
						</details>
					</li>
				))}
			</ul>
		</div>
	);
}

export function AnswerCard({ turn }) {
	if (turn.error) return <div className="review-error" role="alert">{turn.error}</div>;
	if (!turn.result) return <div className="ad-answer ad-answer--muted"><Loading>Reading the project documents…</Loading></div>;
	const r = turn.result;
	const status = STATUS[r.status] ?? { label: r.status, tone: "neutral", card: "" };
	return (
		<article className={`ad-answer ${status.card}`}>
			<div className="ad-answer__head">
				<Badge tone={status.tone}>{status.label}</Badge>
				{r.scope_verdict && <Badge tone={SCOPE[r.scope_verdict][1]}>{SCOPE[r.scope_verdict][0]}</Badge>}
				{r.served_by === "backup" && <Badge tone="warn">Answered by fallback model</Badge>}
			</div>
			<p className="ad-answer__text">{r.answer}</p>
			<Sources citations={r.citations || []} />
			{r.dropped_citations?.length > 0 && (
				<p className="ad-answer__note">{r.dropped_citations.length} citation(s) removed: the quote was not found in the cited passage.</p>
			)}
			<div className="ad-answer__meta">
				{r.model ? `${r.served_by} · ${r.model}${r.latency_ms ? ` · ${(r.latency_ms / 1000).toFixed(1)} s` : ""} · ${r.prompt_version}` : r.prompt_version}
				{r.retrieval?.length > 0 && (
					<details>
						<summary>Searched passages ({r.retrieval.length})</summary>
						<ul>{r.retrieval.map((x) => <li key={x.chunk_id}>{x.label} · {x.section} · {x.score.toFixed(3)}</li>)}</ul>
					</details>
				)}
			</div>
		</article>
	);
}
