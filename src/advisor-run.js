import { useSyncExternalStore } from "react";

// The research run lives here, outside React, so closing the dialog does not lose a run that takes minutes:
// the fetch keeps going and the dialog (or the floating pill) simply re-reads the state when it is shown again.

const API = "/advisor";
const SILENCE_LIMIT_MS = 90_000; // the server sends a keep-alive every 15 s, so this long a silence means a dead connection
const MAX_EVENTS = 300;
const STORAGE_KEY = "advisor:last-result";

const idleState = {
	phase: "idle", // idle | running | done | error
	description: "",
	events: [],
	result: null,
	error: null,
	notice: "",
	startedAt: 0,
	finishedAt: 0,
};

function restoreLastResult() {
	try {
		const saved = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "null");
		if (saved?.result?.report) {
			return { ...idleState, phase: "done", description: saved.description, result: saved.result };
		}
	} catch {
		// a private window or blocked storage: start empty
	}
	return idleState;
}

function saveLastResult(description, result) {
	try {
		window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ description, result }));
	} catch {
		// the report is still on screen; it just will not survive a reload
	}
}

function forgetLastResult() {
	try {
		window.sessionStorage.removeItem(STORAGE_KEY);
	} catch {
		// nothing to forget
	}
}

let state = restoreLastResult();
let controller = null;
let abortReason = "";
const listeners = new Set();

function update(patch) {
	state = { ...state, ...patch };
	listeners.forEach((listener) => listener());
}

const subscribe = (listener) => {
	listeners.add(listener);
	return () => listeners.delete(listener);
};
const getSnapshot = () => state;

export function useAdvisorRun() {
	return useSyncExternalStore(subscribe, getSnapshot);
}

export class AdvisorError extends Error {
	constructor(message, status = 0) {
		super(message);
		this.status = status;
	}
}

function describeDetail(detail) {
	if (typeof detail === "string") return detail;
	if (Array.isArray(detail)) {
		return detail.map((entry) => entry?.msg ?? JSON.stringify(entry)).join(" ");
	}
	return "";
}

async function httpError(response) {
	let detail = "";
	try {
		detail = describeDetail((await response.json()).detail);
	} catch {
		// the body was not JSON; the status text below is enough
	}
	if (response.status === 429) {
		return new AdvisorError(
			"The advisor is still finishing another research run. The local model handles one run at a time, so wait a minute or two and try again.",
			429,
		);
	}
	// The Vite dev proxy answers with an empty 500 (or 502/504) when nothing listens on the API port.
	if (response.status === 502 || response.status === 504 || (response.status >= 500 && !detail)) {
		return new AdvisorError(
			"The advisor API is not reachable. Start it with `uv run uvicorn app.main:app` in the agentic-freelance-advisor folder.",
			response.status,
		);
	}
	return new AdvisorError(detail || `The advisor returned HTTP ${response.status}.`, response.status);
}

function parseFrame(frame) {
	let event = "message";
	const data = [];
	for (const line of frame.split("\n")) {
		if (line.startsWith(":")) continue; // keep-alive comment
		if (line.startsWith("event:")) event = line.slice(6).trim();
		else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
	}
	if (data.length === 0) return null;
	try {
		return { event, data: JSON.parse(data.join("\n")) };
	} catch {
		return null;
	}
}

export async function fetchHealth(signal) {
	const response = await fetch(`${API}/health`, { signal });
	if (!response.ok) throw new Error(`The advisor API answered HTTP ${response.status}.`);
	return response.json();
}

export async function startResearch(description) {
	if (state.phase === "running") return;
	const mine = new AbortController();
	controller = mine;
	abortReason = "";
	update({ ...idleState, phase: "running", description, startedAt: Date.now() });

	let silenceTimer = 0;
	const armSilenceTimer = () => {
		window.clearTimeout(silenceTimer);
		silenceTimer = window.setTimeout(() => {
			abortReason = "silence";
			mine.abort();
		}, SILENCE_LIMIT_MS);
	};

	try {
		armSilenceTimer();
		const response = await fetch(`${API}/research/stream`, {
			method: "POST",
			headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
			body: JSON.stringify({ project_description: description }),
			signal: mine.signal,
		});
		if (!response.ok) throw await httpError(response);
		if (!response.body) throw new AdvisorError("This browser cannot read a streamed response.");

		const reader = response.body.getReader();
		const decoder = new TextDecoder();
		let buffer = "";
		let finished = false;
		for (;;) {
			const { value, done } = await reader.read();
			if (done) break;
			armSilenceTimer();
			buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, "\n");
			let boundary = buffer.indexOf("\n\n");
			while (boundary !== -1) {
				const frame = parseFrame(buffer.slice(0, boundary));
				buffer = buffer.slice(boundary + 2);
				boundary = buffer.indexOf("\n\n");
				if (!frame) continue;
				if (frame.event === "progress") {
					update({ events: [...state.events, frame.data].slice(-MAX_EVENTS) });
				} else if (frame.event === "result") {
					finished = true;
					saveLastResult(description, frame.data);
					update({ phase: "done", result: frame.data, finishedAt: Date.now() });
				} else if (frame.event === "error") {
					throw new AdvisorError(frame.data.detail ?? "The research run failed.", frame.data.status ?? 500);
				}
			}
		}
		if (!finished) throw new AdvisorError("The connection closed before the result arrived. Try again.");
	} catch (error) {
		if (mine.signal.aborted && abortReason === "cancelled") return; // cancelResearch() already set the state
		let message;
		if (mine.signal.aborted && abortReason === "silence") {
			message = "The advisor stopped sending updates for 90 seconds, so the connection was dropped. Check the API terminal and try again.";
		} else if (error instanceof AdvisorError) {
			message = error.message;
		} else {
			message = "Could not reach the advisor API. Start it with `uv run uvicorn app.main:app` in the agentic-freelance-advisor folder.";
		}
		update({ phase: "error", error: { message, status: error.status ?? 0 }, finishedAt: Date.now() });
	} finally {
		window.clearTimeout(silenceTimer);
		if (controller === mine) controller = null;
	}
}

export function cancelResearch() {
	if (state.phase !== "running") return;
	abortReason = "cancelled";
	controller?.abort();
	update({
		...idleState,
		description: state.description,
		notice:
			"You stopped waiting. The server may still be finishing its current model step, so a new run can be refused for a minute or two.",
	});
}

export function resetResearch() {
	if (state.phase === "running") return;
	forgetLastResult();
	update({ ...idleState, description: state.description });
}
