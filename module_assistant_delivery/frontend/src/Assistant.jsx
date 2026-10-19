import { useEffect, useRef, useState } from "react";
import { AnswerCard } from "./Answer.jsx";
import { api } from "./api.js";
import ModelPicker from "./ModelPicker.jsx";
import { Field, Section, Tag, prefersReducedMotion, readStored, writeStored } from "./ui.jsx";

// Each side asks what it needs: the freelancer what to build and how it is accepted, the client what was bought and
// what they must do. One question per list has no answer in the documents, to show the assistant does not invent one.
const SUGGESTIONS = {
	freelancer: [
		"What are the non-negotiable requirements?",
		"What must each milestone deliver, and when?",
		"The client asks for a dark mode. Is that in scope?",
		"How many revision rounds are included per milestone?",
		"What is the hourly rate for extra work?",
		"Quelle est la durée de la garantie après la réception finale ?",
	],
	client: [
		"What is in scope, and what is not?",
		"How is the payment split across milestones?",
		"How do I request a feature that is not in the scope?",
		"What happens if I want to end the contract early?",
		"What is the hosting budget for the second year?",
		"Combien de jours ai-je pour valider un jalon ?",
	],
};

function Documents({ user, projectId, refreshKey, onChanged }) {
	const [docs, setDocs] = useState([]);
	const [error, setError] = useState("");
	const [busy, setBusy] = useState(false);
	const [confirming, setConfirming] = useState(null);
	const fileRef = useRef(null);

	// Removing a wrong upload stops answers from it at once; an older version of the same file becomes active again.
	async function remove(doc) {
		setConfirming(null);
		try {
			await api(`/documents/${doc.id}`, { user, method: "DELETE" });
			onChanged();
		} catch (e) {
			setError(e.message);
		}
	}

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
		<Section title="Project documents" description="Answers come only from the active version of these documents.">
			{docs.length === 0 && !error && <p className="ad-muted">No documents yet.</p>}
			<ul className="ad-list">
				{docs.map((d) => (
					<li key={d.id} className={d.status === "superseded" ? "is-old" : ""}>
						<strong>{d.title}</strong>
						<span className="ad-row">
							<small>v{d.version}, {d.file_kind}, {d.chunk_count} passages</small>
							{d.status === "superseded" && <Tag>Superseded</Tag>}
							{confirming === d.id ? (
								<span className="ad-confirm" role="group" aria-label={`Remove ${d.title}`}>
									<span>Remove v{d.version}?</span>
									<button type="button" className="ad-link ad-link--danger" onClick={() => remove(d)}>Remove</button>
									<button type="button" className="ad-link" onClick={() => setConfirming(null)}>Keep</button>
								</span>
							) : (
								<button type="button" className="ad-link ad-link--quiet" onClick={() => setConfirming(d.id)}>Remove</button>
							)}
						</span>
					</li>
				))}
			</ul>
			<form className="ad-form" onSubmit={onUpload}>
				<Field label="Add or update a document (MD, TXT, PDF, DOCX)">
					<input ref={fileRef} type="file" accept=".md,.markdown,.txt,.pdf,.docx" required />
				</Field>
				<div className="ad-form__row">
					<Field label="Type">
						<select name="doc_type" defaultValue="cahier_des_charges">
							<option value="cahier_des_charges">Cahier des charges</option>
							<option value="contract">Contract</option>
							<option value="spec">Specification</option>
							<option value="other">Other</option>
						</select>
					</Field>
					<button type="submit" className="ad-btn" disabled={busy}>{busy ? "Indexing…" : "Upload"}</button>
				</div>
			</form>
			{error && <div className="ad-alert" role="alert">{error}</div>}
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
		<Section title="Earlier conversations">
			<ul className="ad-list">
				{items.slice(0, 8).map((c) => (
					<li key={c.id}>
						<button type="button" className="ad-link" onClick={() => onOpen(c.id)}>{c.first_question || "(empty)"}</button>
						<small>{c.messages} messages, {c.created_at.slice(0, 16).replace("T", " ")}</small>
					</li>
				))}
			</ul>
		</Section>
	);
}

export default function Assistant({ user, projectId, role, models, backupStatus, onActivity }) {
	const [turns, setTurns] = useState([]);
	const [conversationId, setConversationId] = useState(null);
	const [draft, setDraft] = useState("");
	const [docsKey, setDocsKey] = useState(0);
	const [historyKey, setHistoryKey] = useState(0);
	const [model, setModel] = useState(() => (readStored("assistant.model") === "raft" ? "raft" : "base"));
	const [drill, setDrill] = useState(false);
	const endRef = useRef(null);

	useEffect(() => { setTurns([]); setConversationId(null); }, [user, projectId]);
	useEffect(() => { if (turns.length) endRef.current?.scrollIntoView({ block: "nearest", behavior: prefersReducedMotion() ? "auto" : "smooth" }); }, [turns]);
	useEffect(() => { writeStored("assistant.model", model); }, [model]);

	// RAFT not configured or not installed: the base model answers.
	const raftMissing = models && (!models.raft || models.raft.status === "model_missing");
	const chosen = model === "raft" && raftMissing ? "base" : model;
	const pending = turns.some((t) => !t.result && !t.error);

	async function send(text) {
		const message = text.trim();
		if (!message || pending) return;
		const id = Date.now();
		setTurns((t) => [...t, { id, question: message }]);
		setDraft("");
		try {
			const result = await api("/chat", {
				user, method: "POST",
				json: { project_id: projectId, message, conversation_id: conversationId, model: chosen, simulate_failure: drill },
			});
			setConversationId(result.conversation_id);
			setTurns((t) => t.map((x) => (x.id === id ? { ...x, result } : x)));
			setHistoryKey((k) => k + 1);
		} catch (e) {
			setTurns((t) => t.map((x) => (x.id === id ? { ...x, error: e.message } : x)));
		}
		onActivity();
	}

	function newConversation() {
		setTurns([]);
		setConversationId(null);
		document.getElementById("ad-message")?.focus();
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
		<div className="ad-chat-layout">
			<div className="ad-chat">
				{turns.length > 0 && (
					<div className="ad-chat__bar">
						<span>{turns.length} {turns.length === 1 ? "question" : "questions"} in this conversation</span>
						<button type="button" className="ad-btn ad-btn--sm" onClick={newConversation} disabled={pending}>New conversation</button>
					</div>
				)}
				<div className="ad-log" role="log" aria-live="polite">
					{!turns.length && (
						<div className="ad-intro">
							<h2>Ask the <em>agreed documents</em>.</h2>
							<p>Every answer quotes the clause it comes from. When the documents do not say, the assistant says so.</p>
							<div className="ad-suggest">
								{(SUGGESTIONS[role] ?? SUGGESTIONS.freelancer).map((s) => <button key={s} type="button" onClick={() => send(s)}>{s}</button>)}
							</div>
						</div>
					)}
					{turns.map((t) => (
						<article key={t.id} className="ad-turn">
							<p className="ad-question">{t.question}</p>
							<AnswerCard turn={t} />
						</article>
					))}
					<div ref={endRef} />
				</div>
				<form className="ad-composer" onSubmit={(e) => { e.preventDefault(); send(draft); }}>
					<div className="ad-composer__box">
						<label className="ad-sr" htmlFor="ad-message">Your question</label>
						<textarea id="ad-message" rows={2} value={draft} maxLength={2000} placeholder="Ask about requirements, scope, milestones or contract terms…"
							onChange={(e) => setDraft(e.target.value)}
							onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(draft); } }} />
						<div className="ad-composer__bar">
							<ModelPicker value={chosen} onChange={setModel} models={models} drill={drill} onDrill={setDrill} backupStatus={backupStatus} />
							{drill && <button type="button" className="ad-flag" onClick={() => setDrill(false)} title="Turn the failure drill off">Failure drill on</button>}
							<span className="ad-composer__hint">Enter to send, Shift+Enter for a new line</span>
							<button type="submit" className="ad-btn ad-btn--primary" disabled={!draft.trim() || pending}>Ask</button>
						</div>
					</div>
					<p className="ad-disclaimer">Advisory only, not legal advice. The document text prevails.</p>
				</form>
			</div>
			<aside className="ad-aside" aria-label="Project documents and history">
				<Documents user={user} projectId={projectId} refreshKey={docsKey} onChanged={() => { setDocsKey((k) => k + 1); onActivity(); }} />
				<History user={user} projectId={projectId} refreshKey={historyKey} onOpen={openConversation} />
			</aside>
		</div>
	);
}
