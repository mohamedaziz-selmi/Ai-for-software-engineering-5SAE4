import { useEffect, useState } from "react";

// Small shared pieces: section heading, tags, form field, pending and thinking states, expanders, preferences.

export function Section({ title, description, actions, children }) {
	return (
		<section className="ad-section">
			<div className="ad-section__head">
				<div>
					<h2>{title}</h2>
					{description && <p>{description}</p>}
				</div>
				{actions}
			</div>
			{children}
		</section>
	);
}

export function Tag({ tone = "neutral", children, title }) {
	return <span className={`ad-tag ad-tag--${tone}`} title={title}>{children}</span>;
}

export const cap = (text) => (text ? text.charAt(0).toUpperCase() + text.slice(1).replace("_", " ") : text);

export function Field({ label, children }) {
	return <label className="ad-field"><span>{label}</span>{children}</label>;
}

export function Pending({ children }) {
	return (
		<div className="ad-pending" role="status">
			<span>{children}</span>
			<div className="ad-skeleton" aria-hidden="true"><span /><span /><span /></div>
		</div>
	);
}

// The "model is working" state: an animated spark, a shimmering label and the real elapsed time. `detail` says what
// the work consists of; `hint` appears only after `hintAfter` seconds. Nothing here claims a step it cannot observe.
export function Thinking({ label = "Thinking", detail, hint, hintAfter = 8, children }) {
	const [seconds, setSeconds] = useState(0);
	useEffect(() => {
		const started = Date.now();
		const timer = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 250);
		return () => clearInterval(timer);
	}, []);
	return (
		<div className="ad-thinking" role="status" aria-live="polite">
			<div className="ad-thinking__row">
				<span className="ad-spark" aria-hidden="true"><i /><i /><i /><i /></span>
				<span className="ad-thinking__label">{label}</span>
				<span className="ad-thinking__time" aria-label={`${seconds} seconds`}>{seconds}s</span>
			</div>
			{detail && <p className="ad-thinking__detail">{detail}</p>}
			{children}
			{hint && seconds >= hintAfter && <p className="ad-thinking__hint">{hint}</p>}
		</div>
	);
}

// Smooth open/close of a block of any height (grid rows 0fr -> 1fr). Closed content is inert: not focusable.
export function Expand({ open, children }) {
	return (
		<div className="ad-expand" data-open={open} inert={open ? undefined : ""}>
			<div className="ad-expand__inner">{children}</div>
		</div>
	);
}

export const prefersReducedMotion = () => {
	try {
		return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
	} catch {
		return false;
	}
};

// Runs a state change inside a View Transition when the browser supports it and motion is allowed.
export function withTransition(update) {
	if (!document.startViewTransition || prefersReducedMotion()) {
		update();
		return;
	}
	document.startViewTransition(update);
}

export function readStored(key) {
	try {
		return window.localStorage.getItem(key);
	} catch {
		return null;
	}
}

export function writeStored(key, value) {
	try {
		window.localStorage.setItem(key, value);
	} catch {
		/* storage unavailable: the choice is simply not remembered */
	}
}
