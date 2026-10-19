import React, { useCallback, useEffect, useRef, useState } from "react";
import TriangleScene from "./TriangleScene.jsx";
import BusinessIntelligenceWorkspace from "./BusinessIntelligence.jsx";
import brandLogo from "../logo.png";
import chatPreview from "./chat-preview.svg";
import biPreview from "./bi-preview.svg";
import assistantPreview from "../module_assistant_delivery/frontend/tile-preview.svg";
import advisorPreview from "./advisor-preview.svg";
import AdvisorDialog, { AdvisorPill } from "./AdvisorDialog.jsx";
import { useAdvisorRun } from "./advisor-run.js";
import marketplaceAiPreview from "./marketplace-ai-preview.svg";
import cerebroBusinessAiPreview from "./cerebro-business-ai-preview.svg";

const projects = [
	{
		id: "bee-tickets",
		name: "Bee Tickets",
		year: 2021,
		employer: "Once Upon A Time SA - Switzerland",
		description:
			"Collaborated with a team of over seven people to develop a new internal ticketing platform. Responsible for implementing the entire frontend and contributed to the design process on select occasions.",
		frontend: "Javascript + SCSS",
		backend: "Django + MySQL",
		images: [
			"/bee-tickets-1.ad6fd083.webp",
			"/bee-tickets-2.895fc78d.webp",
			"/bee-tickets-3.7cbb8265.webp",
			"/bee-tickets-4.5f2a4541.webp",
			"/bee-tickets-5.a5d83ced.webp",
			"/bee-tickets-6.d1faeea0.webp",
		],
	},
	{
		id: "maserati",
		name: "Maserati",
		year: 2022,
		employer: "Deloitte Digital - Italy",
		description:
			"Joined the project during the UAT phase as part of a 30+ person team. Initially focused on bug fixing and analytics integration. Post-launch, joined a team of five to develop the Owner Area section from scratch, managing analytics integration and later overseeing bug fixes.",
		frontend: "AEM + Javascript + jQuery + gsap",
		backend: "AEM + Java",
		recognition: "Awwwards Honorable Mention",
		images: ["/maserati-1.1be141a2.webp"],
	},
	{
		id: "autotorino",
		name: "Autotorino",
		year: 2023,
		employer: "Deloitte Digital - Italy",
		description:
			"Worked with a team of over 15 on the redesign and implementation of a car auction platform, handling both back-office and front-office components.",
		frontend: "Next.js + MUI",
		backend: "Nest.js + Socket.io + DocumentDB + Amazon Cognito",
		images: ["/autotorino-1.49de4d84.webp"],
	},
	{
		id: "po-ng",
		name: "PO-NG",
		year: 2024,
		employer: "Freelance - Italy",
		description:
			"Originally a small experiment to work on my canvas-related knowledge, ended up evolving into a complete game. This project pays tribute to one of the most iconic games in gaming history.",
		frontend: "HTML + SCSS + TypeScript",
		backend: "Node.js + Express.js + ws + MongoDB",
		link: "https://po-ng.netlify.app/",
		images: ["/po-ng-1.0f4aa322.webp"],
	},
];

const marketplaceAiProject = {
	id: "freelance-marketplace-ai",
	name: "Freelance Marketplace AI",
	year: 2026,
	employerLabel: "Project",
	employer: "AI features for a freelance marketplace",
	description:
		"Built reproducible machine-learning workflows for a freelance marketplace. The matching demo uses a lightweight local Qwen model through Ollama, with a TF-IDF baseline. Random Forest and XGBoost estimate project budgets from the supplied Upwork data. Matching metrics currently use category-based proxy labels and need human relevance judgments before production use.",
	frontendLabel: "Freelancer matching",
	frontend: "Qwen2.5 0.5B (Ollama) + TF-IDF",
	backendLabel: "Budget prediction",
	backend: "Random Forest + XGBoost",
	recognition: "Dataset-driven ML prototype",
	images: [marketplaceAiPreview],
};

const galleryProjects = [
	projects[0],
	projects[1],
	projects[2],
	{
		id: "business-intelligence",
		name: "Business Intelligence",
		images: [biPreview],
	},
	{
		id: "cerebro-chat",
		name: "Cerebro AI",
		images: [chatPreview],
	},
	{
		id: "assistant-delivery",
		name: "AI Assistant & Delivery Review",
		images: [assistantPreview],
		href: "/assistant/",
	},
	{
		id: "freelance-advisor",
		name: "Freelance Advisor",
		images: [advisorPreview],
	},
	marketplaceAiProject,
	// Cerebro Business AI (cerebro_business_ai/, its own microservice, started with its START.cmd): its screens through the gateway.
	{
		id: "cerebro-business-ai",
		name: "Cerebro Business AI",
		images: [cerebroBusinessAiPreview],
		href: "/business-ai/",
	},
	{ ...projects[0], id: "bee-tickets-copy-2" },
];

const sampleFreelancers = [
	{
		rank: 1,
		freelancer_id: "SAMPLE-01",
		category: "Data Analyst",
		excerpt: "Python, SQL, Tableau, business intelligence, analytics dashboards, and reporting.",
		search_text: "python sql tableau business intelligence analytics dashboard reporting data analysis",
	},
	{
		rank: 2,
		freelancer_id: "SAMPLE-02",
		category: "Machine Learning Engineer",
		excerpt: "Machine learning, Python, scikit-learn, data pipelines, model deployment, and APIs.",
		search_text: "machine learning python scikit-learn data pipelines model deployment api",
	},
	{
		rank: 3,
		freelancer_id: "SAMPLE-03",
		category: "Data Visualization Specialist",
		excerpt: "Power BI, Tableau, data visualization, SQL, KPI dashboards, and stakeholder reporting.",
		search_text: "power bi tableau data visualization sql kpi dashboard reporting",
	},
];

const sampleProjectBudget = {
	model: "Static sample",
	estimated_budget: 0,
	currency: "USD",
	note: "Example project input is loaded. Submit to run a model, or use the illustrative sample range below.",
	source: "sample",
};

function ArrowIcon({ direction = "right" }) {
	return (
		<svg
			aria-hidden="true"
			className={`arrow-icon arrow-icon--${direction}`}
			viewBox="0 0 24 24"
			fill="none"
		>
			<path d="M4 12h15M13 5l7 7-7 7" stroke="currentColor" strokeWidth="1.6" />
		</svg>
	);
}

function ThemeIcon({ dark }) {
	return dark ? (
		<svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
			<path
				d="M20.3 15.1A8.3 8.3 0 0 1 8.9 3.7 8.5 8.5 0 1 0 20.3 15Z"
				stroke="currentColor"
				strokeWidth="1.5"
			/>
		</svg>
	) : (
		<svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
			<circle cx="12" cy="12" r="3.7" stroke="currentColor" strokeWidth="1.5" />
			<path
				d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"
				stroke="currentColor"
				strokeWidth="1.5"
			/>
		</svg>
	);
}

function ProjectDialog({ project, onClose }) {
	const [imageIndex, setImageIndex] = useState(0);
	const [expanded, setExpanded] = useState(false);
	const dialogRef = useRef(null);
	const imageCount = project.images.length;

	const changeImage = useCallback(
		(delta) => {
			setImageIndex((current) => (current + delta + imageCount) % imageCount);
		},
		[imageCount],
	);

	useEffect(() => {
		const previousOverflow = document.body.style.overflow;
		document.body.style.overflow = "hidden";
		dialogRef.current?.focus();

		const onKeyDown = (event) => {
			if (event.key === "Escape") onClose();
			if (event.key === "ArrowRight") changeImage(1);
			if (event.key === "ArrowLeft") changeImage(-1);
		};
		window.addEventListener("keydown", onKeyDown);
		return () => {
			document.body.style.overflow = previousOverflow;
			window.removeEventListener("keydown", onKeyDown);
		};
	}, [changeImage, onClose]);

	return (
		<div className="dialog-backdrop dialog-backdrop--project" onMouseDown={(event) => {
			if (event.target === event.currentTarget) onClose();
		}}>
			<section
				ref={dialogRef}
				className={`project-dialog${expanded ? " project-dialog--expanded" : ""}`}
				role="dialog"
				aria-modal="true"
				aria-labelledby="project-dialog-title"
				tabIndex={-1}
			>
				<div className="project-dialog__visual">
					<div className="project-dialog__counter">
						<span>{String(imageIndex + 1).padStart(2, "0")}</span>
						<span>{String(imageCount).padStart(2, "0")}</span>
					</div>
					<img
						className="project-dialog__image"
						src={project.images[imageIndex]}
						alt={`${project.name} project preview ${imageIndex + 1}`}
					/>
					{imageCount > 1 && (
						<div className="project-dialog__image-controls">
							<button aria-label="Previous project image" onClick={() => changeImage(-1)}>
								<ArrowIcon direction="left" />
							</button>
							<button aria-label="Next project image" onClick={() => changeImage(1)}>
								<ArrowIcon />
							</button>
						</div>
					)}
					<button
						className="project-dialog__expand"
						aria-label={expanded ? "Restore project details size" : "Expand project details"}
						onClick={() => setExpanded((value) => !value)}
					>
						{expanded ? "↙" : "↗"}
					</button>
				</div>
				<div className="project-dialog__details">
					<div className="project-dialog__heading">
						<div>
							<p className="eyebrow">Selected project · {project.year}</p>
							<h2 id="project-dialog-title">{project.name}</h2>
						</div>
						<button className="project-dialog__close" aria-label="Close project details" onClick={onClose}>
							×
						</button>
					</div>
					<dl className="project-facts">
						<div>
							<dt>{project.employerLabel ?? "Employer"}</dt>
							<dd>{project.employer}</dd>
						</div>
						<div>
							<dt>Year</dt>
							<dd>{project.year}</dd>
						</div>
						<div className="project-facts__description">
							<dt>Description</dt>
							<dd>{project.description}</dd>
						</div>
						<div>
							<dt>{project.frontendLabel ?? "Frontend"}</dt>
							<dd>{project.frontend}</dd>
						</div>
						<div>
							<dt>{project.backendLabel ?? "Backend"}</dt>
							<dd>{project.backend}</dd>
						</div>
						{project.recognition && (
							<div>
								<dt>Recognition</dt>
								<dd>{project.recognition}</dd>
							</div>
						)}
					</dl>
					{project.link && project.id !== "po-ng" && (
						<a className="project-dialog__link" href={project.link} target="_blank" rel="noreferrer">
							Visit project <ArrowIcon />
						</a>
					)}
				</div>
			</section>
		</div>
	);
}

function MarketplaceAIDialog({ onClose }) {
	const [activeFeature, setActiveFeature] = useState("matching");
	const [apiStatus, setApiStatus] = useState("checking");
	const [ollamaStatus, setOllamaStatus] = useState("checking");
	const [matchModel, setMatchModel] = useState("ollama");
	const [matchBrief, setMatchBrief] = useState("Build a Python analytics dashboard using SQL data pipelines, Tableau visualizations, and clear business reporting.");
	const [matchResult, setMatchResult] = useState({
		model: "Static sample resumes · select Find freelancers to rank",
		source: "sample",
		candidates: sampleFreelancers.map(({ search_text, ...profile }) => profile),
	});
	const [matchError, setMatchError] = useState("");
	const [budgetModel, setBudgetModel] = useState("random_forest");
	const [budgetForm, setBudgetForm] = useState({
		title: "Analytics dashboard for an online store",
		description: "Build a Python and SQL dashboard for sales and customer engagement, with Tableau visualizations and clear business reporting.",
		category: "Data Analysis",
		skills: "Python, SQL, Tableau",
		experience_level: "Intermediate",
		payment_type: "Fixed-price",
	});
	const [budgetResult, setBudgetResult] = useState(sampleProjectBudget);
	const [budgetError, setBudgetError] = useState("");
	const [isRunning, setIsRunning] = useState(false);
	const dialogRef = useRef(null);
	const requestRef = useRef(null);

	useEffect(() => {
		const previousOverflow = document.body.style.overflow;
		document.body.style.overflow = "hidden";
		dialogRef.current?.focus();
		const controller = new AbortController();
		void fetch("/api/health", { signal: controller.signal })
			.then((response) => {
				if (!response.ok) throw new Error(`API returned HTTP ${response.status}.`);
				return response.json();
			})
			.then((result) => setApiStatus(result.status === "ready" ? "ready" : "missing"))
			.catch((error) => {
				if (error.name !== "AbortError") setApiStatus("offline");
			});
		void fetch("/ollama-match/api/tags", { signal: controller.signal })
			.then((response) => {
				if (!response.ok) throw new Error(`Ollama returned HTTP ${response.status}.`);
				return response.json();
			})
			.then((result) => {
				const hasSmallModel = Array.isArray(result.models)
					&& result.models.some((model) => model.name === "qwen2.5:0.5b");
				setOllamaStatus(hasSmallModel ? "ready" : "missing");
			})
			.catch((error) => {
				if (error.name !== "AbortError") setOllamaStatus("offline");
			});
		const onKeyDown = (event) => {
			if (event.key === "Escape") onClose();
		};
		window.addEventListener("keydown", onKeyDown);
		return () => {
			document.body.style.overflow = previousOverflow;
			window.removeEventListener("keydown", onKeyDown);
			controller.abort();
			requestRef.current?.abort();
		};
	}, [onClose]);

	const runRequest = async (endpoint, payload, onSuccess, onError, onOfflineDemo, timeoutMs = 10000) => {
		if (apiStatus !== "ready") {
			onOfflineDemo();
			onError(
				apiStatus === "checking"
					? "The model API is still checking. Showing the static sample; retry when the API is connected."
					: "The local model API is offline. Showing the static sample instead.",
			);
			return;
		}

		requestRef.current?.abort();
		const controller = new AbortController();
		requestRef.current = controller;
		const timeoutId = window.setTimeout(() => {
			controller.abort(new DOMException("Model request timed out.", "TimeoutError"));
		}, timeoutMs);
		setIsRunning(true);
		onError("");
		try {
			const response = await fetch(endpoint, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(payload),
				signal: controller.signal,
			});
			if (response.status >= 500 && !response.headers.get("content-type")?.includes("application/json")) {
				throw Object.assign(new Error(`Local model API returned HTTP ${response.status}.`), { useDemo: true });
			}
			if (response.status === 503) {
				const result = await response.json();
				throw Object.assign(
					new Error(typeof result.detail === "string" ? result.detail : "Model artifacts are unavailable."),
					{ useDemo: true },
				);
			}
			const result = await response.json();
			if (!response.ok) {
				throw new Error(typeof result.detail === "string" ? result.detail : `Model API returned HTTP ${response.status}.`);
			}
			onSuccess(result);
		} catch (error) {
			const didTimeout = error.name === "TimeoutError" || controller.signal.reason?.name === "TimeoutError";
			if (error.name !== "AbortError" || didTimeout) {
				if (didTimeout || error.useDemo || error instanceof TypeError) {
					setApiStatus(error.useDemo ? "missing" : "offline");
					onOfflineDemo();
					onError(
						didTimeout
							? "Model request timed out. Showing static sample data instead."
							: `${error.message || "Local model API is unavailable."} Showing static sample data instead.`,
					);
				} else {
					onError(error.message || "The model request failed.");
				}
			}
		} finally {
			window.clearTimeout(timeoutId);
			if (requestRef.current === controller) {
				requestRef.current = null;
				setIsRunning(false);
			}
		}
	};

	const submitMatch = (event) => {
		event.preventDefault();
		setMatchResult(null);
		const projectTerms = new Set((matchBrief.toLowerCase().match(/[a-z0-9+#.-]{2,}/g) || []));
		const sampleCandidates = sampleFreelancers
			.map(({ search_text, ...profile }) => ({
				...profile,
				overlap: (search_text.match(/[a-z0-9+#.-]{2,}/g) || [])
					.filter((term) => projectTerms.has(term)).length,
			}))
			.sort((first, second) => second.overlap - first.overlap || first.rank - second.rank)
			.map((profile, index) => ({ ...profile, rank: index + 1 }));
		if (matchModel === "tfidf") {
			setMatchError("");
			setMatchResult({
				model: "Keyword-overlap sample ranking",
				source: "sample",
				candidates: sampleCandidates,
			});
			return;
		}
		if (ollamaStatus !== "ready") {
			setMatchResult({
				model: "Offline sample ranking · shared-keyword overlap",
				source: "sample",
				candidates: sampleCandidates,
			});
			setMatchError(
				ollamaStatus === "checking"
					? "Ollama is still checking. Showing the sample ranking; retry once the local model is ready."
					: ollamaStatus === "missing"
						? "Qwen2.5 0.5B is not installed on the CPU Ollama service. Showing the sample ranking."
						: "CPU Ollama is offline. Showing the sample ranking instead.",
			);
			return;
		}

		requestRef.current?.abort();
		const controller = new AbortController();
		requestRef.current = controller;
		const timeoutId = window.setTimeout(() => {
			controller.abort(new DOMException("Local model request timed out.", "TimeoutError"));
		}, 60000);
		setIsRunning(true);
		setMatchError("");
		const profiles = sampleFreelancers.map(({ freelancer_id, category, excerpt }) => ({
			id: freelancer_id,
			category,
			summary: excerpt,
		}));
		const prompt = JSON.stringify({
			project: matchBrief,
			profiles,
		});
		void fetch("/ollama-match/api/chat", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				model: "qwen2.5:0.5b",
				messages: [
					{
						role: "system",
						content: "Rank the supplied freelancer profiles for the project. Return exactly one JSON key named ranked_ids whose value is an array of the supplied profile IDs, in best-to-worst order. Do not use IDs as object keys or add scores or explanations.",
					},
					{ role: "user", content: prompt },
				],
				format: {
					type: "object",
					properties: {
						ranked_ids: {
							type: "array",
							items: { type: "string", enum: profiles.map((profile) => profile.id) },
						},
					},
					required: ["ranked_ids"],
					additionalProperties: false,
				},
				stream: false,
				keep_alive: "10m",
				options: { num_ctx: 1024, num_predict: 48, temperature: 0 },
			}),
			signal: controller.signal,
		})
			.then(async (response) => {
				const result = await response.json();
				if (!response.ok) {
					throw new Error(typeof result.error === "string" ? result.error : `Ollama returned HTTP ${response.status}.`);
				}
				const ranking = JSON.parse(result.message?.content ?? "");
				if (!Array.isArray(ranking.ranked_ids)) {
					throw new Error("Qwen returned an invalid ranking.");
				}
				const byId = new Map(sampleFreelancers.map(({ freelancer_id, category, excerpt }) => [
					freelancer_id,
					{ freelancer_id, category, excerpt },
				]));
				const rankedIds = [...new Set(ranking.ranked_ids)]
					.filter((id) => byId.has(id));
				if (rankedIds.length !== sampleFreelancers.length) {
					throw new Error("Qwen did not return every sample profile exactly once.");
				}
				setMatchResult({
					model: "Qwen2.5 0.5B · Ollama CPU",
					source: "ollama",
					candidates: rankedIds.map((id, index) => ({ ...byId.get(id), rank: index + 1 })),
				});
			})
			.catch((error) => {
				if (error.name === "AbortError" && controller.signal.reason?.name !== "TimeoutError") return;
				const timedOut = controller.signal.reason?.name === "TimeoutError";
				if (error instanceof TypeError) setOllamaStatus("offline");
				setMatchResult({
					model: "Sample ranking · local model unavailable",
					source: "sample",
					candidates: sampleCandidates,
				});
				setMatchError(
					timedOut
						? "Qwen took too long to respond. Showing the quick sample ranking instead."
						: `${error.message || "Ollama matching failed."} Showing the quick sample ranking instead.`,
				);
			})
			.finally(() => {
				window.clearTimeout(timeoutId);
				if (requestRef.current === controller) {
					requestRef.current = null;
					setIsRunning(false);
				}
			});
	};

	const submitBudget = (event) => {
		event.preventDefault();
		setBudgetResult(null);
		void runRequest(
			"/api/budget",
			{ ...budgetForm, model: budgetModel },
			setBudgetResult,
			setBudgetError,
			() => setBudgetResult({
				...sampleProjectBudget,
				estimated_budget: 1200,
				note: "No model API is connected. The sample project is shown with a static $800–$1,500 reference range; this is not a model prediction.",
			}),
		);
	};

	const updateBudgetField = (event) => {
		const { name, value } = event.target;
		setBudgetForm((current) => ({ ...current, [name]: value }));
	};

	return (
		<div
			className="dialog-backdrop dialog-backdrop--marketplace"
			onMouseDown={(event) => {
				if (event.target === event.currentTarget) onClose();
			}}
		>
			<section
				ref={dialogRef}
				className="marketplace-lab"
				role="dialog"
				aria-modal="true"
				aria-labelledby="marketplace-lab-title"
				tabIndex={-1}
			>
				<header className="marketplace-lab__header">
					<div className="marketplace-lab__brand">
						<span className="marketplace-lab__mark" aria-hidden="true">M</span>
						<div>
							<p className="marketplace-lab__eyebrow">CEREBRO · MACHINE LEARNING LAB</p>
							<h2 id="marketplace-lab-title">Freelance Marketplace AI</h2>
						</div>
					</div>
					<div className="marketplace-lab__header-actions">
						<span className={`marketplace-lab__status marketplace-lab__status--${activeFeature === "matching" ? ollamaStatus : apiStatus}`}>
							<span aria-hidden="true" />
							{activeFeature === "matching"
								? ollamaStatus === "checking" ? "Checking Ollama" : ollamaStatus === "ready" ? "Qwen 0.5B · CPU" : ollamaStatus === "missing" ? "Model missing" : "Ollama offline"
								: apiStatus === "checking" ? "Checking ML API" : apiStatus === "ready" ? "ML API connected" : apiStatus === "missing" ? "Artifacts missing" : "ML API offline"}
						</span>
						<button className="project-dialog__close" aria-label="Close AI lab" onClick={onClose}>×</button>
					</div>
				</header>

				<div className="marketplace-lab__tabs" role="tablist" aria-label="Choose an AI feature">
					<button
						id="matching-tab"
						role="tab"
						aria-selected={activeFeature === "matching"}
						aria-controls="matching-panel"
						className={activeFeature === "matching" ? "is-active" : ""}
						onClick={() => setActiveFeature("matching")}
					>
						<span>01</span><strong>Freelancer matching</strong><small>Rank resumes for a project</small>
					</button>
					<button
						id="budget-tab"
						role="tab"
						aria-selected={activeFeature === "budget"}
						aria-controls="budget-panel"
						className={activeFeature === "budget" ? "is-active" : ""}
						onClick={() => setActiveFeature("budget")}
					>
						<span>02</span><strong>Budget prediction</strong><small>Estimate a project budget</small>
					</button>
				</div>

				<div className="marketplace-lab__content">
					{activeFeature === "matching" ? (
						<div id="matching-panel" role="tabpanel" aria-labelledby="matching-tab" className="marketplace-feature">
							<div className="marketplace-feature__intro">
								<p className="marketplace-lab__eyebrow">PROFILE RETRIEVAL · 2 APPROACHES</p>
								<h3>Find the right people for the brief.</h3>
								<p>Use a small local language model to rank sample profiles, or switch to instant keyword matching.</p>
								<div className="marketplace-model-picker" aria-label="Choose matching model">
									<button className={matchModel === "ollama" ? "is-selected" : ""} aria-pressed={matchModel === "ollama"} type="button" onClick={() => setMatchModel("ollama")}>
										<span>01</span><strong>Qwen2.5 0.5B</strong><small>Local Ollama · CPU</small>
									</button>
									<button className={matchModel === "tfidf" ? "is-selected" : ""} aria-pressed={matchModel === "tfidf"} type="button" onClick={() => setMatchModel("tfidf")}>
										<span>02</span><strong>Keyword overlap</strong><small>Instant sample baseline</small>
									</button>
								</div>
								<p className="marketplace-feature__explain">
									{matchModel === "ollama"
									? "Runs locally. First request loads the compact model; later requests should be faster."
										: "Ranks profiles by shared words and phrases. Useful as a transparent baseline."}
								</p>
							</div>
							<div className="marketplace-feature__workspace">
								<form className="marketplace-form" onSubmit={submitMatch}>
									<label>
										<span>Sample project brief · edit or select the text</span>
										<textarea
											value={matchBrief}
											onChange={(event) => setMatchBrief(event.target.value)}
											placeholder="e.g. Build a Python analytics dashboard with SQL data pipelines and clear reporting."
											rows={6}
											minLength={3}
											required
										/>
									</label>
									<div className="marketplace-form__footer">
										<span>3 sample profiles · ranked locally</span>
										<button type="submit" disabled={!matchBrief.trim() || isRunning}>
											{isRunning ? "Ranking…" : "Find freelancers"} <ArrowIcon />
										</button>
									</div>
								</form>
								{matchError && <p className="marketplace-lab__error" role="alert">{matchError}</p>}
								{matchResult ? (
									<div className="marketplace-results" aria-live="polite">
										<div className="marketplace-results__heading">
											<h4>Recommended profiles</h4><span>{matchResult.model}</span>
										</div>
										{matchResult.candidates.map((candidate) => (
											<article className="marketplace-candidate" key={candidate.freelancer_id}>
												<span className="marketplace-candidate__rank">{String(candidate.rank).padStart(2, "0")}</span>
												<div className="marketplace-candidate__details">
													<strong>{candidate.category}</strong>
													<p>{candidate.excerpt}</p>
													<small>{candidate.freelancer_id.startsWith("SAMPLE-") ? "Static sample profile" : `Profile #${candidate.freelancer_id}`}</small>
												</div>
												<span
													className={`marketplace-candidate__score${matchResult.source === "sample" ? " marketplace-candidate__score--sample" : ""}`}
													title={matchResult.source === "ollama"
														? "Position in the local Qwen ranking; not a confidence score"
														: "Static sample data; not a model confidence score"}
												>
																{matchResult.source === "ollama"
																	? "QWEN"
																	: candidate.overlap === undefined ? "SAMPLE" : `${candidate.overlap} words`}
												</span>
											</article>
										))}
									</div>
								) : (
									<div className="marketplace-empty">
										<span aria-hidden="true">↗</span>
										<strong>Your shortlist appears here</strong>
										<p>{activeFeature === "matching"
											? ollamaStatus === "ready" ? "Ollama is ready. Enter a brief and run local Qwen ranking." : "Start the CPU-only Ollama service and install Qwen2.5 0.5B. See the README commands."
											: apiStatus === "ready" ? "Enter a project brief and run the estimator." : "Start the local ML API and train the model artifacts. See the README commands."}</p>
									</div>
								)}
							</div>
						</div>
					) : (
						<div id="budget-panel" role="tabpanel" aria-labelledby="budget-tab" className="marketplace-feature">
							<div className="marketplace-feature__intro">
								<p className="marketplace-lab__eyebrow">PROJECT ESTIMATION · 2 MODELS</p>
								<h3>Explore a data-backed budget estimate.</h3>
								<p>Describe a listing and compare two regressors trained on historical project budgets.</p>
								<div className="marketplace-model-picker" aria-label="Choose budget model">
									<button className={budgetModel === "random_forest" ? "is-selected" : ""} aria-pressed={budgetModel === "random_forest"} type="button" onClick={() => setBudgetModel("random_forest")}>
										<span>01</span><strong>Random Forest</strong><small>Ensemble of decision trees</small>
									</button>
									<button className={budgetModel === "xgboost" ? "is-selected" : ""} aria-pressed={budgetModel === "xgboost"} type="button" onClick={() => setBudgetModel("xgboost")}>
										<span>02</span><strong>XGBoost</strong><small>Gradient-boosted trees</small>
									</button>
								</div>
								<p className="marketplace-feature__explain">
									These estimates are experimental: validation performance on the supplied dataset was weak, so results are for exploration—not pricing advice.
								</p>
							</div>
							<div className="marketplace-feature__workspace">
								<form className="marketplace-form marketplace-form--budget" onSubmit={submitBudget}>
									<label className="marketplace-form__wide">
									<span>Sample project title · edit or select the text</span>
										<input name="title" value={budgetForm.title} onChange={updateBudgetField} placeholder="e.g. Analytics dashboard for an online store" minLength={2} required />
									</label>
									<label className="marketplace-form__wide">
										<span>Project description</span>
										<textarea name="description" value={budgetForm.description} onChange={updateBudgetField} placeholder="Describe the expected work, deliverables, and scope…" rows={4} minLength={10} required />
									</label>
									<label>
										<span>Category</span>
										<input name="category" value={budgetForm.category} onChange={updateBudgetField} placeholder="e.g. Data Analysis" minLength={2} required />
									</label>
									<label>
										<span>Skills <small>comma separated</small></span>
										<input name="skills" value={budgetForm.skills} onChange={updateBudgetField} placeholder="Python, SQL, Tableau" />
									</label>
									<label>
										<span>Experience level</span>
										<select name="experience_level" value={budgetForm.experience_level} onChange={updateBudgetField}>
											<option>Entry level</option><option>Intermediate</option><option>Expert</option>
										</select>
									</label>
									<label>
										<span>Payment type</span>
										<select name="payment_type" value={budgetForm.payment_type} onChange={updateBudgetField}>
											<option>Fixed-price</option><option>Hourly</option>
										</select>
									</label>
									<div className="marketplace-form__footer marketplace-form__wide">
										<span>{budgetModel === "random_forest" ? "Random Forest" : "XGBoost"} · historical data</span>
										<button type="submit" disabled={isRunning}>
											{isRunning ? "Estimating…" : "Estimate budget"} <ArrowIcon />
										</button>
									</div>
								</form>
								{budgetError && <p className="marketplace-lab__error" role="alert">{budgetError}</p>}
								{budgetResult ? (
									<div className="marketplace-budget-result" aria-live="polite">
										<div>
										<p className="marketplace-lab__eyebrow">{budgetResult.source === "sample" ? "SAMPLE PROJECT · NOT A MODEL PREDICTION" : `MODEL ESTIMATE · ${budgetResult.model}`}</p>
										<strong>
											{budgetResult.source === "sample"
												? budgetResult.estimated_budget === 0 ? "Input ready" : "$800–$1,500"
												: new Intl.NumberFormat("en-US", { style: "currency", currency: budgetResult.currency, maximumFractionDigits: 0 }).format(budgetResult.estimated_budget)}
										</strong>
										<p>{budgetResult.note}</p>
									</div>
									<span aria-hidden="true">$</span>
									</div>
								) : (
									<div className="marketplace-empty marketplace-empty--budget">
										<span aria-hidden="true">$</span>
										<strong>Your estimate appears here</strong>
										<p>{apiStatus === "ready" ? "Complete the listing details and run the selected model." : "Start the local ML API and train the model artifacts. See the README commands."}</p>
									</div>
								)}
							</div>
						</div>
					)}
				</div>
				<footer className="marketplace-lab__footer">
					<span>RESEARCH DEMO · NOT A PRODUCTION RECOMMENDER</span>
					<span>Resume categories are proxies; budget model validation is weak.</span>
				</footer>
			</section>
		</div>
	);
}

function ChatDialog({ onClose }) {
	const [expanded, setExpanded] = useState(false);
	const [input, setInput] = useState("");
	const [messages, setMessages] = useState([]);
	const [models, setModels] = useState([]);
	const [selectedModel, setSelectedModel] = useState("");
	const [connection, setConnection] = useState("loading");
	const [connectionError, setConnectionError] = useState("");
	const [isGenerating, setIsGenerating] = useState(false);
	const [proposalBrief, setProposalBrief] = useState("");
	const [proposalBudget, setProposalBudget] = useState("");
	const [proposalTimeline, setProposalTimeline] = useState("");
	const [proposalResult, setProposalResult] = useState("");
	const [proposalError, setProposalError] = useState("");
	const [isGeneratingProposal, setIsGeneratingProposal] = useState(false);
	const [reviewText, setReviewText] = useState("");
	const [reviewResult, setReviewResult] = useState("");
	const [reviewError, setReviewError] = useState("");
	const [isClassifyingReview, setIsClassifyingReview] = useState(false);
	const dialogRef = useRef(null);
	const outputEndRef = useRef(null);
	const nextMessageId = useRef(0);
	const modelRequestRef = useRef(null);
	const chatRequestRef = useRef(null);
	const toolRequestsRef = useRef({ proposal: null, sentiment: null });

	useEffect(() => {
		const previousOverflow = document.body.style.overflow;
		document.body.style.overflow = "hidden";
		dialogRef.current?.focus();

		const onKeyDown = (event) => {
			if (event.key === "Escape") onClose();
		};
		window.addEventListener("keydown", onKeyDown);
		return () => {
			document.body.style.overflow = previousOverflow;
			window.removeEventListener("keydown", onKeyDown);
		};
	}, [onClose]);

	useEffect(() => {
		outputEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
	}, [messages]);

	const loadModels = useCallback(async (signal) => {
		setConnection("loading");
		setConnectionError("");
		try {
			const response = await fetch("/ollama/api/tags", { signal });
			if (!response.ok) throw new Error(`Ollama returned HTTP ${response.status}.`);
			const data = await response.json();
			const installedModels = Array.isArray(data.models)
				? data.models.filter((entry) => typeof entry.name === "string")
				: [];
			if (installedModels.length === 0) {
				throw new Error("No Ollama models are installed. Use `ollama pull llama3.2:3b` to install one.");
			}
			setModels(installedModels);
			setSelectedModel((current) => (
				installedModels.some((entry) => entry.name === current)
					? current
					: installedModels.find((entry) => entry.name === "llama3.2:3b")?.name
						?? installedModels[0].name
			));
			setConnection("ready");
		} catch (error) {
			if (error.name === "AbortError") return;
			setConnection("error");
			setConnectionError(`Could not reach Ollama. ${error.message}`);
		}
	}, []);

	useEffect(() => {
		const controller = new AbortController();
		modelRequestRef.current = controller;
		void loadModels(controller.signal);
		return () => controller.abort();
	}, [loadModels]);

	useEffect(() => () => chatRequestRef.current?.abort(), []);
	useEffect(() => () => {
		Object.values(toolRequestsRef.current).forEach((controller) => controller?.abort());
	}, []);

	const retryModelLoad = () => {
		modelRequestRef.current?.abort();
		const controller = new AbortController();
		modelRequestRef.current = controller;
		void loadModels(controller.signal);
	};

	const appendAssistantText = (id, text) => {
		if (!text) return;
		setMessages((current) => current.map((message) => (
			message.id === id ? { ...message, text: message.text + text } : message
		)));
	};

	const sendMessage = async (event) => {
		event.preventDefault();
		const text = input.trim();
		if (
			!text
			|| !selectedModel
			|| connection !== "ready"
			|| isGenerating
			|| isGeneratingProposal
			|| isClassifyingReview
		) return;

		const userMessage = { id: nextMessageId.current++, role: "user", text };
		const assistantId = nextMessageId.current++;
		const controller = new AbortController();
		chatRequestRef.current = controller;
		setMessages((current) => [...current, userMessage, {
			id: assistantId,
			role: "assistant",
			text: "",
		}]);
		setInput("");
		setIsGenerating(true);
		setConnectionError("");

		try {
			const response = await fetch("/ollama/api/chat", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					model: selectedModel,
					messages: [
						{
							role: "system",
							text: "You are a freelance proposal reviewer. Review proposals for clarity, fit to the project brief, scope, timeline, budget, risks, and missing details. Give practical, constructive feedback. Do not claim to use a knowledge base or files unless they are provided in the conversation.",
						},
						...messages,
						userMessage,
					]
						.filter((message) => !message.error && message.text)
						.map(({ role, text: content }) => ({ role, content })),
					stream: true,
				}),
				signal: controller.signal,
			});
			if (!response.ok) {
				const detail = await response.text();
				throw new Error(detail || `Ollama returned HTTP ${response.status}.`);
			}
			if (!response.body) throw new Error("Ollama returned an empty response stream.");

			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let pending = "";
			let streamError = "";
			const readChunk = (line) => {
				if (!line.trim()) return;
				const chunk = JSON.parse(line);
				if (chunk.error) {
					streamError = chunk.error;
					return;
				}
				appendAssistantText(assistantId, chunk.message?.content ?? "");
			};

			while (true) {
				const { value, done } = await reader.read();
				pending += decoder.decode(value, { stream: !done });
				const lines = pending.split("\n");
				pending = lines.pop() ?? "";
				lines.forEach(readChunk);
				if (done) break;
			}
			if (pending.trim()) readChunk(pending);
			if (streamError) throw new Error(streamError);
		} catch (error) {
			if (error.name !== "AbortError") {
				setMessages((current) => current.map((message) => (
					message.id === assistantId
						? { ...message, text: `Error: ${error.message}`, error: true }
						: message
				)));
				setConnectionError(error.message);
			}
		} finally {
			if (chatRequestRef.current === controller) {
				chatRequestRef.current = null;
				setIsGenerating(false);
			}
		}
	};

	const runTool = async (tool, prompt, instructions) => {
		if (
			!selectedModel
			|| connection !== "ready"
			|| isGenerating
			|| isGeneratingProposal
			|| isClassifyingReview
		) return;
		const controller = new AbortController();
		toolRequestsRef.current[tool] = controller;
		let timedOut = false;
		const timeoutId = window.setTimeout(() => {
			timedOut = true;
			controller.abort();
		}, 180000);
		if (tool === "proposal") {
			setIsGeneratingProposal(true);
			setProposalError("");
			setProposalResult("");
		} else {
			setIsClassifyingReview(true);
			setReviewError("");
			setReviewResult("");
		}

		try {
			const response = await fetch("/ollama/api/chat", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					model: selectedModel,
					messages: [
						{ role: "system", content: instructions },
						{ role: "user", content: prompt },
					],
					stream: false,
					options: {
						temperature: 0.3,
						num_predict: tool === "proposal" ? 350 : 160,
					},
				}),
				signal: controller.signal,
			});
			if (!response.ok) {
				const detail = await response.text();
				throw new Error(detail || `Ollama returned HTTP ${response.status}.`);
			}
			const data = await response.json();
			const result = data.message?.content?.trim();
			if (!result) throw new Error("The selected Ollama model returned an empty result.");
			if (tool === "proposal") setProposalResult(result);
			else setReviewResult(result);
		} catch (error) {
			if (error.name !== "AbortError") {
				if (tool === "proposal") setProposalError(error.message);
				else setReviewError(error.message);
			}
			if (timedOut) {
				const message = "Ollama did not finish within 3 minutes. Check that the local model is responding, then retry.";
				if (tool === "proposal") setProposalError(message);
				else setReviewError(message);
			}
		} finally {
			window.clearTimeout(timeoutId);
			if (toolRequestsRef.current[tool] === controller) {
				toolRequestsRef.current[tool] = null;
				if (tool === "proposal") setIsGeneratingProposal(false);
				else setIsClassifyingReview(false);
			}
		}
	};

	const generateProposal = (event) => {
		event.preventDefault();
		const brief = proposalBrief.trim();
		if (!brief) return;
		const details = [
			`Project brief: ${brief}`,
			proposalBudget.trim() && `Budget: ${proposalBudget.trim()}`,
			proposalTimeline.trim() && `Timeline: ${proposalTimeline.trim()}`,
		].filter(Boolean).join("\n");
		void runTool(
			"proposal",
			`Write a polished freelance proposal based on these details:\n${details}`,
			"Write clear, professional freelance project proposals. Include a concise understanding of the brief, proposed approach and deliverables, a realistic schedule if supplied, and a confident closing. Do not invent credentials, prices, or commitments that were not supplied. Format the result with useful headings.",
		);
	};

	const classifyReview = async (event) => {
		event.preventDefault();
		const review = reviewText.trim();
		if (!review) return;

		toolRequestsRef.current.sentiment?.abort();
		const controller = new AbortController();
		toolRequestsRef.current.sentiment = controller;

		setIsClassifyingReview(true);
		setReviewError("");
		setReviewResult("");

		try {
			const response = await fetch("/sentiment-api/predict", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ review_text: review }),
				signal: controller.signal,
			});

			if (!response.ok) {
				const detail = await response.text();
				throw new Error(detail || `Sentiment API returned HTTP ${response.status}.`);
			}

			const data = await response.json();
			const sentiment = data.sentiment ? data.sentiment.toUpperCase() : "UNKNOWN";
			const confidence = typeof data.confidence === "number" ? Math.round(data.confidence * 100) : 0;
			const probs = data.probabilities
				? ` (Positive: ${(data.probabilities.positive * 100).toFixed(1)}%, Neutral: ${(data.probabilities.neutral * 100).toFixed(1)}%, Negative: ${(data.probabilities.negative * 100).toFixed(1)}%)`
				: "";

			setReviewResult(`Sentiment: ${sentiment} (${confidence}% confidence)${probs}`);
		} catch (error) {
			if (error.name !== "AbortError") {
				setReviewError(`Could not reach sentiment classifier: ${error.message}`);
			}
		} finally {
			if (toolRequestsRef.current.sentiment === controller) {
				toolRequestsRef.current.sentiment = null;
				setIsClassifyingReview(false);
			}
		}
	};

	return (
		<div
			className="dialog-backdrop dialog-backdrop--project"
			onMouseDown={(event) => {
				if (event.target === event.currentTarget) onClose();
			}}
		>
			<section
				ref={dialogRef}
				className={`project-dialog project-dialog--chat${expanded ? " project-dialog--expanded" : ""}`}
				role="dialog"
				aria-modal="true"
				aria-labelledby="chat-dialog-title"
				tabIndex={-1}
			>
				<header className="chat-dialog__header">
					<div>
						<p className="eyebrow">Cerebro / Local assistant</p>
						<h2 id="chat-dialog-title">Proposal Review</h2>
					</div>
					<div className="chat-dialog__header-actions">
						<span className={`chat-dialog__connection chat-dialog__connection--${connection}`}>
							{connection === "loading"
								? "Checking Ollama…"
								: connection === "ready"
									? `Ollama · ${selectedModel}`
									: "Ollama · Offline"}
						</span>
						<button
							className="project-dialog__expand"
							aria-label={expanded ? "Restore chat window size" : "Expand chat window"}
							onClick={() => setExpanded((value) => !value)}
						>
							{expanded ? "↙" : "↗"}
						</button>
						<button className="project-dialog__close" aria-label="Close chat" onClick={onClose}>
							×
						</button>
					</div>
				</header>
				<div className="chat-dialog__main">
					<div className="chat-dialog__toolbar">
						<label htmlFor="chat-model-select">Model</label>
						<select
							id="chat-model-select"
							value={selectedModel}
							onChange={(event) => setSelectedModel(event.target.value)}
							disabled={connection !== "ready" || isGenerating || isGeneratingProposal || isClassifyingReview}
						>
							{models.map((entry) => (
								<option key={entry.name} value={entry.name}>{entry.name}</option>
							))}
						</select>
						{connectionError && (
							<p className="chat-dialog__error" role="alert">{connectionError}</p>
						)}
						{connection === "error" && (
							<button className="chat-dialog__retry" type="button" onClick={retryModelLoad}>
								Retry
							</button>
						)}
					</div>
					<div className="chat-dialog__output" role="log" aria-live="polite" aria-relevant="additions">
						{messages.length === 0 ? (
							<div className="chat-dialog__welcome">
								<span className="chat-dialog__spark" aria-hidden="true">✳</span>
								<h3>Ready to review a proposal?</h3>
								<p>Paste a freelance proposal or ask a review question. Cerebro will assess the scope, fit, clarity, timeline, budget, and possible risks.</p>
							</div>
						) : (
							<div className="chat-dialog__messages">
								{messages.map((message) => (
									<article
										className={`chat-message chat-message--${message.role}`}
										key={message.id}
									>
										<p className="chat-message__role">
											{message.role === "user" ? "You" : `Cerebro · ${selectedModel}`}
										</p>
										<p>{message.text || (isGenerating && message.role === "assistant" ? "Thinking…" : "")}</p>
									</article>
								))}
								<div ref={outputEndRef} />
							</div>
						)}
					</div>
					<form className="chat-dialog__composer" onSubmit={sendMessage}>
						<label className="visually-hidden" htmlFor="chat-message-input">Paste a proposal for review</label>
						<input
							id="chat-message-input"
							type="text"
							value={input}
							onChange={(event) => setInput(event.target.value)}
							placeholder="Paste a proposal or ask for a review..."
							autoComplete="off"
							disabled={connection !== "ready" || isGenerating || isGeneratingProposal || isClassifyingReview}
						/>
						<button type="submit" disabled={!input.trim() || connection !== "ready" || isGenerating || isGeneratingProposal || isClassifyingReview}>
							{isGenerating ? "Thinking…" : <>Send <ArrowIcon /></>}
						</button>
					</form>
					<p className="chat-dialog__footnote">Proposal reviews are processed locally by Ollama on this computer.</p>
				</div>
				<div className="chat-dialog__tools" aria-label="AI tools">
					<section className="chat-tool" aria-labelledby="proposal-tool-title">
						<div className="chat-tool__heading">
							<p className="eyebrow">01 / Freelance assistant</p>
							<h3 id="proposal-tool-title">Freelance proposal generator</h3>
							<p>Turn a project brief into a polished proposal with a clear scope and next steps.</p>
						</div>
						<form className="chat-tool__form" onSubmit={generateProposal}>
							<label className="chat-tool__field chat-tool__field--wide">
								<span>Project brief <span aria-hidden="true">*</span></span>
								<textarea
									value={proposalBrief}
									onChange={(event) => setProposalBrief(event.target.value)}
									placeholder="Describe the client's project, goals, and requested work..."
									rows={4}
									required
								/>
							</label>
							<label className="chat-tool__field">
								<span>Budget (optional)</span>
								<input
									type="text"
									value={proposalBudget}
									onChange={(event) => setProposalBudget(event.target.value)}
									placeholder="e.g. $1,500"
								/>
							</label>
							<label className="chat-tool__field">
								<span>Timeline (optional)</span>
								<input
									type="text"
									value={proposalTimeline}
									onChange={(event) => setProposalTimeline(event.target.value)}
									placeholder="e.g. 3 weeks"
								/>
							</label>
							<button
								className="chat-tool__submit"
								type="submit"
								disabled={!proposalBrief.trim() || connection !== "ready" || isGenerating || isGeneratingProposal || isClassifyingReview}
							>
								{isGeneratingProposal ? "Generating…" : "Generate proposal"} <ArrowIcon />
							</button>
						</form>
						{proposalError && <p className="chat-tool__error" role="alert">{proposalError}</p>}
						{(proposalResult || isGeneratingProposal) && (
							<div className="chat-tool__result" aria-live="polite">
								<h4>{isGeneratingProposal ? "Writing your proposal…" : "Generated proposal"}</h4>
								<p>{proposalResult || "The selected model is drafting a proposal."}</p>
							</div>
						)}
					</section>
					<section className="chat-tool" aria-labelledby="sentiment-tool-title">
						<div className="chat-tool__heading">
							<p className="eyebrow">02 / Customer insights</p>
							<h3 id="sentiment-tool-title">Customer review sentiment classifier</h3>
							<p>Classify customer reviews using your trained TF-IDF + Logistic Regression model.</p>
						</div>
						<form className="chat-tool__form chat-tool__form--single" onSubmit={classifyReview}>
							<label className="chat-tool__field chat-tool__field--wide">
								<span>Customer review <span aria-hidden="true">*</span></span>
								<textarea
									value={reviewText}
									onChange={(event) => setReviewText(event.target.value)}
									placeholder="Paste a customer review to analyze..."
									rows={4}
									required
								/>
							</label>
							<button
								className="chat-tool__submit"
								type="submit"
								disabled={!reviewText.trim() || isClassifyingReview}
							>
								{isClassifyingReview ? "Analyzing…" : "Classify sentiment"} <ArrowIcon />
							</button>
						</form>
						{reviewError && <p className="chat-tool__error" role="alert">{reviewError}</p>}
						{(reviewResult || isClassifyingReview) && (
							<div className="chat-tool__result" aria-live="polite">
								<h4>{isClassifyingReview ? "Analyzing review…" : "Sentiment analysis"}</h4>
								<p>{reviewResult || "The selected model is reviewing the text."}</p>
							</div>
						)}
					</section>
				</div>
			</section>
		</div>
	);
}

function ProposalTools() {
	const [models, setModels] = useState([]);
	const [model, setModel] = useState("");
	const [status, setStatus] = useState("loading");
	const [brief, setBrief] = useState("");
	const [budget, setBudget] = useState("");
	const [timeline, setTimeline] = useState("");
	const [proposalResult, setProposalResult] = useState("");
	const [reviewText, setReviewText] = useState("");
	const [reviewResult, setReviewResult] = useState("");
	const [error, setError] = useState("");
	const [working, setWorking] = useState("");

	const loadModels = useCallback(async () => {
		setStatus("loading");
		try {
			const response = await fetch("/ollama/api/tags");
			const data = await response.json();
			if (!response.ok || !data.models?.length) throw new Error("No local Ollama models are available.");
			setModels(data.models);
			setModel((current) => current || data.models.find((item) => item.name === "llama3.2:3b")?.name || data.models[0].name);
			setStatus("ready");
		} catch (requestError) {
			setStatus("error");
			setError(`Could not reach Ollama. ${requestError.message}`);
		}
	}, []);

	useEffect(() => { void loadModels(); }, [loadModels]);
	const run = async (kind, prompt, instructions) => {
		if (kind === "sentiment") {
			setWorking("sentiment");
			setError("");
			setReviewResult("");
			try {
				const response = await fetch("/sentiment-api/predict", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ review_text: reviewText.trim() }),
				});
				if (!response.ok) {
					const detail = await response.text();
					throw new Error(detail || `Sentiment API returned HTTP ${response.status}.`);
				}
				const data = await response.json();
				const sentiment = data.sentiment ? data.sentiment.toUpperCase() : "UNKNOWN";
				const confidence = typeof data.confidence === "number" ? Math.round(data.confidence * 100) : 0;
				const probs = data.probabilities
					? ` (Positive: ${(data.probabilities.positive * 100).toFixed(1)}%, Neutral: ${(data.probabilities.neutral * 100).toFixed(1)}%, Negative: ${(data.probabilities.negative * 100).toFixed(1)}%)`
					: "";
				setReviewResult(`Sentiment: ${sentiment} (${confidence}% confidence)${probs}`);
			} catch (requestError) {
				setError(`Could not reach sentiment classifier: ${requestError.message}`);
			} finally {
				setWorking("");
			}
			return;
		}

		if (!model) return;
		setWorking(kind); setError("");
		try {
			const response = await fetch("/ollama/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model, stream: false, messages: [{ role: "system", content: instructions }, { role: "user", content: prompt }] }) });
			const data = await response.json();
			if (!response.ok || !data.message?.content) throw new Error(data.error || "The model returned an empty result.");
			setProposalResult(data.message.content);
		} catch (requestError) { setError(requestError.message); }
		finally { setWorking(""); }
	};

	return <section className="review-tools" aria-label="Local AI tools">
		<div className="review-tools__bar">
			<div>
				<p className="eyebrow">04 / Local tools</p>
				<h3>Draft and review tools</h3>
			</div>
			{status === "error" ? <button type="button" onClick={loadModels}>Retry Ollama</button> : null}
		</div>
		{error ? <p className="review-error" role="alert">{error}</p> : null}
		<div className="review-tools__grid">
			<section className="chat-tool">
				<div className="chat-tool__heading">
					<div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: "0.5rem" }}>
						<p className="eyebrow">Freelance assistant</p>
						<label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.75rem", color: "#625e68" }}>
							LLM:{" "}
							<select value={model} onChange={(event) => setModel(event.target.value)} disabled={status !== "ready" || Boolean(working)}>
								{models.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}
							</select>
						</label>
					</div>
					<h3>Freelance proposal generator</h3>
					<p>Turn a project brief into a polished proposal with a clear scope and next steps.</p>
				</div>
				<form className="chat-tool__form" onSubmit={(event) => { event.preventDefault(); void run("proposal", `Project brief: ${brief}\nBudget: ${budget || "Not supplied"}\nTimeline: ${timeline || "Not supplied"}`, "Write a clear professional freelance proposal. Include understanding, approach, deliverables, schedule when supplied, and a confident closing. Do not invent credentials, prices, or commitments."); }}>
					<label className="chat-tool__field chat-tool__field--wide">
						<span>Project brief *</span>
						<textarea value={brief} onChange={(event) => setBrief(event.target.value)} placeholder="Describe the client's project, goals, and requested work..." rows={4} required />
					</label>
					<label className="chat-tool__field">
						<span>Budget (optional)</span>
						<input value={budget} onChange={(event) => setBudget(event.target.value)} placeholder="e.g. $1,500" />
					</label>
					<label className="chat-tool__field">
						<span>Timeline (optional)</span>
						<input value={timeline} onChange={(event) => setTimeline(event.target.value)} placeholder="e.g. 3 weeks" />
					</label>
					<button className="chat-tool__submit" disabled={!brief.trim() || status !== "ready" || Boolean(working)}>
						{working === "proposal" ? "Generating…" : "Generate proposal"} <ArrowIcon />
					</button>
				</form>
				{proposalResult ? <div className="chat-tool__result"><h4>Generated proposal</h4><p>{proposalResult}</p></div> : null}
			</section>

			<section className="chat-tool">
				<div className="chat-tool__heading">
					<div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: "0.5rem" }}>
						<p className="eyebrow">Customer insights</p>
						<span style={{ fontSize: "0.72rem", color: "#286443", background: "rgba(40,100,67,0.1)", padding: "0.2rem 0.5rem", borderRadius: "0.35rem", fontWeight: 500 }}>
							TF-IDF + Logistic Regression
						</span>
					</div>
					<h3>Customer review sentiment classifier</h3>
					<p>Classify customer reviews using your trained sentiment model.</p>
				</div>
				<form className="chat-tool__form chat-tool__form--single" onSubmit={(event) => { event.preventDefault(); void run("sentiment"); }}>
					<label className="chat-tool__field chat-tool__field--wide">
						<span>Customer review *</span>
						<textarea value={reviewText} onChange={(event) => setReviewText(event.target.value)} placeholder="Paste a customer review to analyze..." rows={4} required />
					</label>
					<button className="chat-tool__submit" disabled={!reviewText.trim() || Boolean(working)}>
						{working === "sentiment" ? "Analyzing…" : "Classify sentiment"} <ArrowIcon />
					</button>
				</form>
				{reviewResult ? <div className="chat-tool__result"><h4>Sentiment analysis</h4><p>{reviewResult}</p></div> : null}
			</section>
		</div>
	</section>;
}

function ProposalReviewWorkspace({ onClose }) {
	const [project, setProject] = useState("JOB-001");
	const [proposal, setProposal] = useState("");
	const [evidence, setEvidence] = useState([]);
	const [searchState, setSearchState] = useState("idle");
	const [searchError, setSearchError] = useState("");
	const [showAllEvidence, setShowAllEvidence] = useState(false);
	const [expandedEvidence, setExpandedEvidence] = useState(null);
	const dialogRef = useRef(null);

	useEffect(() => {
		const onKeyDown = (event) => event.key === "Escape" && onClose();
		dialogRef.current?.focus();
		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [onClose]);

	const findEvidence = async (event) => {
		event.preventDefault();
		if (!proposal.trim()) return;
		setSearchState("loading");
		setSearchError("");
		try {
			const response = await fetch("/rag-api/search", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ query: `${project}: ${proposal.trim()}`, limit: 5 }),
			});
			const data = await response.json();
			if (!response.ok) throw new Error(data.detail || "The knowledge-base search is unavailable.");
			const uniqueEvidence = (data.results ?? []).filter((item, index, results) => (
				results.findIndex((candidate) => candidate.source.pdf_file === item.source.pdf_file) === index
			));
			setEvidence(uniqueEvidence.slice(0, 3));
			setShowAllEvidence(false);
			setExpandedEvidence(null);
			setSearchState("complete");
		} catch (error) {
			setSearchError(error.message);
			setSearchState("error");
		}
	};

	const evidenceToShow = showAllEvidence ? evidence : evidence.slice(0, 3);
	const evidenceTitle = (fileName) => fileName.replace(/^[A-Z]{2}-\d+_/, "").replace(/\.pdf$/i, "").replaceAll("_", " ");
	const excerpt = (text, limit = 310) => text.length > limit ? `${text.slice(0, limit).replace(/\s+\S*$/, "")}…` : text;

	return (
		<div className="dialog-backdrop dialog-backdrop--project" onMouseDown={(event) => {
			if (event.target === event.currentTarget) onClose();
		}}>
			<section ref={dialogRef} className="review-workspace" role="dialog" aria-modal="true" aria-labelledby="review-workspace-title" tabIndex={-1}>
				<header className="review-workspace__header">
					<div><p className="eyebrow">Cerebro / Proposal evaluation</p><h2 id="review-workspace-title">Proposal Review Workspace</h2></div>
					<div className="review-workspace__actions"><span className="review-workspace__status">Hybrid RAG · semantic + BM25</span><button className="project-dialog__close" aria-label="Close proposal workspace" onClick={onClose}>×</button></div>
				</header>
				<div className="review-workspace__scroll">
					<div className="review-workspace__body">
					<section className="review-input" aria-labelledby="review-input-title">
						<div className="review-section-heading"><p className="eyebrow">01 / Input</p><h3 id="review-input-title">Add a proposal for review</h3><p>Select the related project, then paste a freelancer proposal. This phase retrieves supporting evidence; it does not yet produce an automated score.</p></div>
						<form onSubmit={findEvidence}>
							<label className="review-field"><span>Related project</span><select value={project} onChange={(event) => setProject(event.target.value)}>{Array.from({ length: 10 }, (_, index) => `JOB-${String(index + 1).padStart(3, "0")}`).map((job) => <option key={job}>{job}</option>)}</select></label>
							<label className="review-field"><span>Freelancer proposal</span><textarea value={proposal} onChange={(event) => setProposal(event.target.value)} placeholder="Paste the proposal, estimate, approach, portfolio evidence, and timeline here…" rows={12} required /></label>
							<button className="review-primary-action" type="submit" disabled={!proposal.trim() || searchState === "loading"}>{searchState === "loading" ? "Finding evidence…" : "Find supporting evidence"} <ArrowIcon /></button>
						</form>
					</section>
					<section className="review-results" aria-labelledby="review-results-title">
						<div className="review-section-heading"><p className="eyebrow">02 / Evidence</p><h3 id="review-results-title">Retrieved knowledge</h3><p>{evidence.length ? `${evidence.length} distinct sources matched your proposal.` : "Relevant requirements, guidance, risk flags, and comparable proposals will appear here."}</p></div>
						{searchError ? <p className="review-error" role="alert">{searchError}</p> : null}
						{searchState === "idle" ? <div className="review-empty"><strong>Evidence will appear here.</strong><span>Relevant requirements, scoring guidance, risk flags, and comparable proposals will be cited by PDF and page.</span></div> : null}
						{evidence.length > 0 ? <ol className="evidence-list">{evidence.map((item, index) => <li key={`${item.source.pdf_file}-${item.source.page}-${index}`}><div><span>{item.source.category.replaceAll("_", " ")}</span><strong>{item.source.pdf_file} · p. {item.source.page}</strong></div><p>{item.text}</p></li>)}</ol> : null}
					</section>
				</div>
				<ProposalTools />
				</div>
			</section>
		</div>
	);
}

function InfoPanel({ panel, onClose }) {
	useEffect(() => {
		const onKeyDown = (event) => {
			if (event.key === "Escape") onClose();
		};
		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [onClose]);

	return (
		<div className="dialog-backdrop" onMouseDown={(event) => {
			if (event.target === event.currentTarget) onClose();
		}}>
			<section className="info-panel" role="dialog" aria-modal="true" aria-labelledby="info-panel-title">
				<button className="project-dialog__close" aria-label="Close" onClick={onClose}>×</button>
				<p className="eyebrow">Cerebro / {panel}</p>
				<h2 id="info-panel-title">
					{panel === "About" ? "A platform for e-commerce and freelance." : "Selected digital work."}
				</h2>
				<p>
					{panel === "About"
						? "Cerebro is a platform for e-commerce and freelance work, bringing digital projects and services together in one place."
						: "Explore work across ticketing, automotive, commerce and interactive web experiences. Select a triangle to see the project details."}
				</p>
			</section>
		</div>
	);
}

export default function App() {
	const [dark, setDark] = useState(false);
	const [activeProject, setActiveProject] = useState(null);
	const [activePanel, setActivePanel] = useState(null);
	const [dragOffset, setDragOffset] = useState(0);
	const [isDragging, setIsDragging] = useState(false);
	const [hoveredProject, setHoveredProject] = useState(null);
	const galleryWindowRef = useRef(null);
	const dragRef = useRef(null);
	const glideFrame = useRef(0);
	const suppressClick = useRef(false);

	const stopGlide = useCallback(() => {
		if (glideFrame.current) cancelAnimationFrame(glideFrame.current);
		glideFrame.current = 0;
	}, []);

	const clampOffset = useCallback((offset) => {
		const viewport = galleryWindowRef.current;
		const sideways = viewport
			? viewport.clientWidth / Math.max(1, viewport.clientHeight) < 1.2
			: window.innerWidth / window.innerHeight < 1.2;
		const dimension = sideways
			? viewport?.clientHeight ?? window.innerHeight
			: viewport?.clientWidth ?? window.innerWidth;
		const limit = dimension * 0.38;
		return Math.max(-limit, Math.min(limit, offset));
	}, []);

	const startGlide = useCallback(
		(velocity) => {
			if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
			let currentVelocity = velocity * 0.35;
			const tick = () => {
				currentVelocity *= 0.84;
				if (Math.abs(currentVelocity) < 0.15) {
					glideFrame.current = 0;
					return;
				}
				setDragOffset((current) => {
					const next = clampOffset(current + currentVelocity);
					if (next === current) {
						cancelAnimationFrame(glideFrame.current);
						glideFrame.current = 0;
					}
					return next;
				});
				if (glideFrame.current) glideFrame.current = requestAnimationFrame(tick);
			};
			glideFrame.current = requestAnimationFrame(tick);
		},
		[clampOffset],
	);

	const handlePointerDown = useCallback((event) => {
		if (event.button !== 0 || dragRef.current) return;
		stopGlide();
		dragRef.current = {
			pointerId: event.pointerId,
			startX: event.clientX,
			startY: event.clientY,
			startOffset: dragOffset,
			lastX: event.clientX,
			lastY: event.clientY,
			lastTime: performance.now(),
			velocity: 0,
			dragging: false,
			sideways: window.innerWidth / window.innerHeight < 1.2,
		};
	}, [dragOffset, stopGlide]);

	const handlePointerMove = useCallback((event) => {
		const drag = dragRef.current;
		if (!drag || event.pointerId !== drag.pointerId) return;
		const delta = drag.sideways
			? event.clientY - drag.startY
			: event.clientX - drag.startX;
		if (!drag.dragging && Math.abs(delta) < 6) return;
		drag.dragging = true;
		setIsDragging(true);
		suppressClick.current = true;
		event.preventDefault();
		const now = performance.now();
		const elapsed = now - drag.lastTime;
		if (elapsed > 0) {
			const lastPosition = drag.sideways ? drag.lastY : drag.lastX;
			const position = drag.sideways ? event.clientY : event.clientX;
			drag.velocity = ((position - lastPosition) / elapsed) * 16;
		}
		drag.lastX = event.clientX;
		drag.lastY = event.clientY;
		drag.lastTime = now;
		setDragOffset(clampOffset(drag.startOffset + delta));
	}, [clampOffset]);

	const handlePointerUp = useCallback((event) => {
		const drag = dragRef.current;
		if (!drag || event.pointerId !== drag.pointerId) return;
		dragRef.current = null;
		if (drag.dragging) {
			setIsDragging(false);
			startGlide(drag.velocity);
			window.setTimeout(() => {
				suppressClick.current = false;
			}, 0);
		}
	}, [startGlide]);

	useEffect(() => {
		window.addEventListener("pointermove", handlePointerMove, { passive: false });
		window.addEventListener("pointerup", handlePointerUp);
		window.addEventListener("pointercancel", handlePointerUp);
		return () => {
			window.removeEventListener("pointermove", handlePointerMove);
			window.removeEventListener("pointerup", handlePointerUp);
			window.removeEventListener("pointercancel", handlePointerUp);
		};
	}, [handlePointerMove, handlePointerUp]);

	const handleProjectSelect = useCallback((project) => {
		if (suppressClick.current) {
			suppressClick.current = false;
			return;
		}
		if (project.href) {
			window.location.assign(project.href);
			return;
		}
		setActiveProject(project);
	}, []);
	const handleProjectHover = useCallback((project) => setHoveredProject(project), []);
	const handleProjectLeave = useCallback((project) => {
		setHoveredProject((current) => current?.id === project.id ? null : current);
	}, []);

	const closeProject = useCallback(() => setActiveProject(null), []);
	const closePanel = useCallback(() => setActivePanel(null), []);

	// A research run outlives its dialog, so a pill on the gallery says it is still running (or has finished).
	const advisor = useAdvisorRun();
	const advisorProject = galleryProjects.find((project) => project.id === "freelance-advisor");
	const advisorOpen = activeProject?.id === "freelance-advisor";
	const [advisorSeen, setAdvisorSeen] = useState(true);
	useEffect(() => {
		if (advisor.phase === "running") setAdvisorSeen(false);
	}, [advisor.phase]);
	useEffect(() => {
		if (advisorOpen) setAdvisorSeen(true);
	}, [advisorOpen, advisor.phase]);
	const advisorPillVisible = advisor.phase === "running" || (advisor.phase === "done" && !advisorSeen);

	return (
		<main className={`portfolio${dark ? " portfolio--dark" : ""}`}>
			<div className={`project-backdrop${hoveredProject ? " project-backdrop--active" : ""}`} aria-hidden="true">
				{hoveredProject && (
					<img
						key={hoveredProject.id}
						className="project-backdrop__image"
						src={hoveredProject.images[0]}
						alt=""
					/>
				)}
				<div className="project-backdrop__shade" />
				<span className="project-backdrop__title">
					{hoveredProject?.name ?? "CEREBRO E-COMMERCE & FREELANCE"}
				</span>
			</div>
			<div className="scanline-overlay" aria-hidden="true" />

			<header className="site-header">
				<div className="site-header__left">
					<a className="brand" href="/" aria-label="Cerebro home">
						<img src={brandLogo} alt="" />
					</a>
				</div>
				<div className="site-header__top-right">
					<button
						className="theme-toggle"
						aria-label={`Switch to ${dark ? "light" : "dark"} theme`}
						onClick={() => setDark((value) => !value)}
					>
						<ThemeIcon dark={dark} />
						<span>{dark ? "Light mode" : "Dark mode"}</span>
					</button>
				</div>
				<div className="site-header__right">
					<nav className="side-navigation" aria-label="Main navigation">
						<button onClick={() => setActivePanel("About")}>About</button>
					</nav>
				</div>
			</header>

			<section className="gallery-section" aria-label="Selected projects">
				<div
					ref={galleryWindowRef}
					className="gallery-window"
					onPointerDown={handlePointerDown}
					data-dragging={isDragging}
				>
					<TriangleScene
						projects={galleryProjects}
						dark={dark}
						pan={dragOffset}
						onHover={handleProjectHover}
						onLeave={handleProjectLeave}
						onSelect={handleProjectSelect}
					/>
					<div className="project-accessibility-list" aria-label="Project list">
						{galleryProjects.map((project) => (
							<button key={project.id} onClick={() => project.href ? window.location.assign(project.href) : setActiveProject(project)}>
								Open {project.name}
							</button>
						))}
					</div>
				</div>
				<div className="gallery-ai-launch">
					<div>
						<p className="eyebrow">TWO MODELS · ONE LAB</p>
						<strong>Freelance Marketplace AI</strong>
					</div>
					<button
						type="button"
						onClick={() => setActiveProject(marketplaceAiProject)}
						aria-label="Open the interactive freelancer matching and budget prediction models"
					>
						Open AI lab <ArrowIcon />
					</button>
				</div>
			</section>

			{activeProject && (activeProject.id === "cerebro-chat"
				? <ProposalReviewWorkspace onClose={closeProject} />
				: activeProject.id === "business-intelligence"
					? <BusinessIntelligenceWorkspace onClose={closeProject} />
					: activeProject.id === "freelance-advisor"
						? <AdvisorDialog onClose={closeProject} />
						: activeProject.id === "freelance-marketplace-ai"
							? <MarketplaceAIDialog onClose={closeProject} />
							: <ProjectDialog project={activeProject} onClose={closeProject} />)}
			{!advisorOpen && advisorPillVisible && (
				<AdvisorPill run={advisor} onOpen={() => setActiveProject(advisorProject)} />
			)}
			{activePanel && <InfoPanel panel={activePanel} onClose={closePanel} />}
		</main>
	);
}
