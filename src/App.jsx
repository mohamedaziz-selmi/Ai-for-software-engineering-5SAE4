import React, { useCallback, useEffect, useRef, useState } from "react";
import TriangleScene from "./TriangleScene.jsx";
import BusinessIntelligenceWorkspace from "./BusinessIntelligence.jsx";
import brandLogo from "../logo.png";
import chatPreview from "./chat-preview.svg";
import biPreview from "./bi-preview.svg";
import assistantPreview from "../module_assistant_delivery/frontend/tile-preview.svg";

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
	{ ...projects[0], id: "bee-tickets-copy-2" },
];

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
							<dt>Employer</dt>
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
							<dt>Frontend</dt>
							<dd>{project.frontend}</dd>
						</div>
						<div>
							<dt>Backend</dt>
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
			</section>

			{activeProject && (activeProject.id === "cerebro-chat"
				? <ProposalReviewWorkspace onClose={closeProject} />
				: activeProject.id === "business-intelligence"
					? <BusinessIntelligenceWorkspace onClose={closeProject} />
					: <ProjectDialog project={activeProject} onClose={closeProject} />)}
			{activePanel && <InfoPanel panel={activePanel} onClose={closePanel} />}
		</main>
	);
}
