import { useEffect, useRef, useState } from "react";
import { AnswerCard } from "./Answer.jsx";
import { api } from "./api.js";
import { Section } from "./ui.jsx";

const SUGGESTIONS = [
	"What are the non-negotiable requirements?",
	"The client asks for a dark mode. Is that in scope?",
	"How is the payment split across milestones?",
	"What is the hosting budget for the second year?",
	"Quelle est la durée de la garantie après la réception finale ?",
];

function Documents({ user, projectId, refreshKey, onChanged }) {
	const [docs, setDocs] = useState([]);
	const [error, setError] = useState("");
	const [busy, setBusy] = useState(false);
	const fileRef = useRef(null);

	useEffect(() => {
		const controller = new AbortController();
		api(`/documents?project_id=${encodeURIComponent(projectId)}`, { user, signal: controller.signal })
			.then((d) => { setDocs(d.documents); setError(""); })
			.catch((e) => e.name !== "AbortError" && setError(e.message));
		return () => controller.abort();
	}, [user, projectId, refreshKey]);

	async function onUpload(event) {
		event.preventDefault();
		const file = fileRef.current?.files?.[0];
		if (!file) return;
		const form = new FormData();
		form.append("project_id", projectId);
		form.append("doc_type", event.target.doc_type.value);
		form.append("file", file);
		setBusy(true);
		setError("");
		try {
			await api("/documents", { user, method: "POST", form });
			fileRef.current.value = "";
			onChanged();
		} catch (e) {
			setError(e.message);
		} finally {
			setBusy(false);
		}
	}

	return (
		<Section eyebrow="Agreed documents" title="Project documents" description="The assistant answers only from the active version of these documents.">
			{docs.length === 0 && !error && <p className="ad-muted">No documents yet.</p>}
			<ul className="ad-list">
				{docs.map((d) => (
					<li key={d.id} className={d.status === "superseded" ? "is-old" : ""}>
						<strong>{d.title}</strong>
						<small>v{d.version} · {d.file_kind} · {d.chunk_count} passages{d.status === "superseded" ? " · superseded" : ""}</small>
					</li>
				))}
			</ul>
			<form className="ad-form ad-controls" onSubmit={onUpload}>
				<label>Add or update a document (MD, TXT, PDF, DOCX)<input ref={fileRef} type="file" accept=".md,.markdown,.txt,.pdf,.docx" required /></label>
				<label>Type
					<select name="doc_type" defaultValue="cahier_des_charges">
						<option value="cahier_des_charges">Cahier des charges</option>
						<option value="contract">Contract</option>
						<option value="spec">Specification</option>
						<option value="other">Other</option>
					</select>
				</label>
				<button type="submit" className="review-primary-action" disabled={busy}>{busy ? "Indexing…" : "Upload"}</button>
			</form>
			{error && <div className="review-error" role="alert">{error}</div>}
		</Section>
	);
}

function History({ user, projectId, refreshKey, onOpen }) {
	const [items, setItems] = useState([]);
	useEffect(() => {
		api(`/conversations?project_id=${encodeURIComponent(projectId)}`, { user }).then((d) => setItems(d.conversations)).catch(() => setItems([]));
	}, [user, projectId, refreshKey]);
	if (!items.length) return null;
	return (
		<Section eyebrow="History" title="Earlier conversations">
			<ul className="ad-list">
				{items.slice(0, 8).map((c) => (
					<li key={c.id}>
						<button type="button" className="ad-link-button" onClick={() => onOpen(c.id)}>{c.first_question || "(empty)"}</button>
						<small>{c.messages} messages · {c.created_at.slice(0, 16).replace("T", " ")}</small>
					</li>
				))}
			</ul>
		</Section>
	);
}

export default function Assistant({ user, projectId, onActivity }) {
	const [turns, setTurns] = useState([]);
	const [conversationId, setConversationId] = useState(null);
	const [draft, setDraft] = useState("");
	const [docsKey, setDocsKey] = useState(0);
	const [historyKey, setHistoryKey] = useState(0);
	const endRef = useRef(null);

	useEffect(() => { setTurns([]); setConversationId(null); }, [user, projectId]);
	useEffect(() => { endRef.current?.scrollIntoView({ block: "nearest" }); }, [turns]);

	const pending = turns.some((t) => !t.result && !t.error);

	async function send(text) {
		const message = text.trim();
		if (!message || pending) return;
		const id = Date.now();
		setTurns((t) => [...t, { id, question: message }]);
		setDraft("");
		try {
			const result = await api("/chat", { user, method: "POST", json: { project_id: projectId, message, conversation_id: conversationId } });
			setConversationId(result.conversation_id);
			setTurns((t) => t.map((x) => (x.id === id ? { ...x, result } : x)));
			setHistoryKey((k) => k + 1);
		} catch (e) {
			setTurns((t) => t.map((x) => (x.id === id ? { ...x, error: e.message } : x)));
		}
		onActivity();
	}

	async function openConversation(id) {
		try {
			const d = await api(`/conversations/${id}`, { user });
			const loaded = [];
			for (const m of d.messages) {
				if (m.role === "user") loaded.push({ id: m.id, question: m.text });
				else if (loaded.length) {
					loaded[loaded.length - 1].result = {
						status: m.status, grounded: Boolean(m.grounded), answer: m.text, citations: m.citations || [], scope_verdict: m.scope_verdict,
						served_by: m.served_by, model: m.model, prompt_version: m.prompt_version, retrieval: m.retrieval || [],
						dropped_citations: m.verification || [], latency_ms: 0,
					};
				}
			}
			setTurns(loaded);
			setConversationId(id);
		} catch {
			/* the list refreshes on the next question */
		}
	}

	return (
		<div className="ad-split">
			<div className="ad-split__side">
				<Documents user={user} projectId={projectId} refreshKey={docsKey} onChanged={() => { setDocsKey((k) => k + 1); onActivity(); }} />
				<History user={user} projectId={projectId} refreshKey={historyKey} onOpen={openConversation} />
			</div>
			<div className="ad-split__main">
				<Section eyebrow="Ask the agreed documents" title="Project assistant" description="Answers cite the clause they come from. When the documents do not say, the assistant says so instead of guessing.">
					<div className="ad-thread" role="log" aria-live="polite">
						{!turns.length && (
							<div className="review-empty">
								<strong>Ask about requirements, scope, milestones or contract terms.</strong>
								<div className="ad-chips">
									{SUGGESTIONS.map((s) => <button key={s} type="button" className="ad-chip" onClick={() => send(s)}>{s}</button>)}
								</div>
							</div>
						)}
						{turns.map((t) => (
							<div key={t.id} className="ad-thread">
								<p className="ad-question">{t.question}</p>
								<AnswerCard turn={t} />
							</div>
						))}
						<div ref={endRef} />
					</div>
					<form className="ad-composer" onSubmit={(e) => { e.preventDefault(); send(draft); }}>
						<label className="eyebrow" htmlFor="ad-message" hidden>Your question</label>
						<textarea id="ad-message" rows={2} value={draft} maxLength={2000} placeholder="Ask a question about this project…"
							onChange={(e) => setDraft(e.target.value)}
							onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(draft); } }} />
						<button type="submit" className="review-primary-action" disabled={!draft.trim() || pending}>Ask</button>
					</form>
					<p className="ad-disclaimer">Advisory only. Not legal advice; the document text prevails.</p>
				</Section>
			</div>
		</div>
	);
}
