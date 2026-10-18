import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import AssistantWorkspace from "./AssistantWorkspace.jsx";

// Standalone page at /assistant/: the workspace on the template's paper backdrop.
createRoot(document.getElementById("root")).render(
	<StrictMode>
		<main className="ad-frame">
			<AssistantWorkspace />
		</main>
	</StrictMode>,
);
