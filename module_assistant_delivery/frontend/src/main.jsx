import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// Self-hosted fonts (bundled into dist; nothing is fetched from the internet): interface, reading serif, code.
import "@fontsource-variable/hanken-grotesk";
import "@fontsource-variable/source-serif-4/opsz.css";
import "@fontsource-variable/source-serif-4/opsz-italic.css";
import "@fontsource-variable/jetbrains-mono";
import AssistantWorkspace from "./AssistantWorkspace.jsx";

// Standalone page at /assistant/.
createRoot(document.getElementById("root")).render(
	<StrictMode>
		<AssistantWorkspace />
	</StrictMode>,
);
