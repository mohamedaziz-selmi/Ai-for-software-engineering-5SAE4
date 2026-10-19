import { useEffect, useId, useRef, useState } from "react";

// Model menu in the composer, like a chat app's. One model runs at a time: the private Ollama keeps a single
// model in memory (OLLAMA_MAX_LOADED_MODELS=1), so choosing one unloads the other. Figures: eval/results/assistant_final-*.md.
export const MODELS = {
	base: { name: "Base + RAG", tag: "Default", detail: "Qwen2.5-7B-Instruct with retrieval. Final test: 23 of 24 answers correct." },
	raft: { name: "RAFT fine-tuned", tag: "Backup", detail: "The same model after RAFT training on 1,977 examples. Final test: 19 of 24." },
};
const STATUS = { up: "installed", model_missing: "not installed", down: "Ollama offline" };

export default function ModelPicker({ value, onChange, models, drill, onDrill, backupStatus }) {
	const [open, setOpen] = useState(false);
	const ref = useRef(null);
	const menuId = useId();

	useEffect(() => {
		if (!open) return undefined;
		const onPointer = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
		const onKey = (e) => {
			if (e.key !== "Escape") return;
			setOpen(false);
			ref.current?.querySelector(".ad-model-btn")?.focus();
		};
		document.addEventListener("pointerdown", onPointer);
		document.addEventListener("keydown", onKey);
		return () => { document.removeEventListener("pointerdown", onPointer); document.removeEventListener("keydown", onKey); };
	}, [open]);

	const backupsOff = backupStatus === "disabled";
	return (
		<div className="ad-model" ref={ref}>
			<button type="button" className="ad-model-btn" aria-expanded={open} aria-controls={menuId} onClick={() => setOpen((o) => !o)}>
				<span className="ad-sr">Model:</span><b>{MODELS[value].name}</b>
			</button>
			{open && (
				<div className="ad-model-menu" id={menuId} role="group" aria-label="Assistant model">
					<fieldset>
						<legend>Answer with</legend>
						{Object.entries(MODELS).map(([id, m]) => {
							const info = models?.[id];
							const unavailable = id !== "base" && (!info || info.status === "model_missing");
							return (
								<label key={id} className="ad-model-opt">
									<input type="radio" name="ad-model" value={id} checked={value === id} disabled={unavailable}
										onChange={() => { onChange(id); setOpen(false); }} />
									<b>{m.name} <span className="ad-tag">{m.tag}</span></b>
									<span className="ad-model-opt__dot" aria-hidden="true" />
									<p>{m.detail}</p>
									<small>{info ? `${info.tag}, ${STATUS[info.status] ?? info.status}` : "not configured"}</small>
								</label>
							);
						})}
					</fieldset>
					<label className="ad-drill">
						<b>Failure drill</b>
						<input id="ad-drill" className="ad-switch" type="checkbox" role="switch" checked={drill} disabled={backupsOff}
							onChange={(e) => onDrill(e.target.checked)} />
						<p>{backupsOff
							? "Backups are off (ASSISTANT_BACKUP_ENABLED=false), so nothing would take over."
							: "Skip the chosen model on the next questions, as if it had crashed, to show the other model taking over."}</p>
					</label>
					<p className="ad-model-menu__note">Only the chosen model is loaded. The first answer after a switch is slower while it loads.</p>
				</div>
			)}
		</div>
	);
}
