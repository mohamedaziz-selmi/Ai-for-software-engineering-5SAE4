# Validation

Date: 18 October 2026

Runtime: Node.js 24.19.0 on Windows.

Command: `node --test test/gateway.test.mjs`

Result: 9 passed, 0 failed.

Checks:

1. Exactly two gateway upstreams; invalid configuration, remote targets and direct proxy loops rejected.
2. Path-boundary routing and ambiguous-path rejection.
3. Two-hop routing, existing prefix rewrites and AI route separation.
4. Binary body and authorization preservation; forwarding-header spoofing removed.
5. Upstream 429, Retry-After and multiple cookies preserved without retries.
6. Streaming reaches the client before the backend ends its response.
7. An unavailable AI service returns 502 while the existing-platform route still responds.
8. Idle upstream timeout returns 504.
9. WebSocket upgrade and bytes traverse both proxy layers.

Tests used temporary loopback servers. The first attempt was blocked by the session's network restrictions; after network permission was granted, all tests passed. No teammates' servers were started and no original application files were changed by these tests.

Not established by these tests: real browser/UI compatibility, availability of existing services, AI implementation, production security, authentication, or deployment readiness.
