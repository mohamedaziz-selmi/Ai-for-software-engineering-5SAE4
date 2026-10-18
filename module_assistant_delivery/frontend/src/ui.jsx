// Small shared pieces, following the template's BI workspace components (Section, badges, states).

export function Section({ eyebrow, title, description, actions, children }) {
	return (
		<section className="ad-section">
			<div className="ad-section__head">
				<div className="review-section-heading">
					{eyebrow && <p className="eyebrow">{eyebrow}</p>}
					<h3>{title}</h3>
					{description && <p>{description}</p>}
				</div>
				{actions && <div>{actions}</div>}
			</div>
			{children}
		</section>
	);
}

export function Badge({ tone = "neutral", children, title }) {
	return <span className={`ad-badge ad-badge--${tone}`} title={title}>{children}</span>;
}

export function Loading({ children }) {
	return <div className="ad-state" role="status"><span className="ad-spinner" aria-hidden="true" />{children}</div>;
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
		/* storage unavailable: the selection is simply not remembered */
	}
}
