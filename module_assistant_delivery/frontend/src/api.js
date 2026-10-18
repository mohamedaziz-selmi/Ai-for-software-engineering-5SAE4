// Same-origin API client. The X-Demo-User header carries the DEMO identity: it is not authentication.

export class ApiError extends Error {
	constructor(status, body) {
		const detail = body?.detail ?? body;
		super(detail?.message || body?.message || `Request failed (HTTP ${status}).`);
		this.status = status;
		this.body = body;
	}
}

export async function api(path, { user, method = "GET", json, form, signal } = {}) {
	const headers = {};
	if (user) headers["X-Demo-User"] = user;
	let body;
	if (json !== undefined) {
		headers["Content-Type"] = "application/json";
		body = JSON.stringify(json);
	} else if (form) {
		body = form;
	}
	let response;
	try {
		response = await fetch(`/api/ai${path}`, { method, headers, body, signal });
	} catch (error) {
		if (error.name === "AbortError") throw error;
		throw new ApiError(0, { message: "The assistant service is unreachable. Is the backend running on port 8003?" });
	}
	const data = await response.json().catch(() => null);
	if (!response.ok) throw new ApiError(response.status, data);
	return data;
}
