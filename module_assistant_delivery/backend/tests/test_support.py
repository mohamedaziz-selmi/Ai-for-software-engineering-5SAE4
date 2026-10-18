from conftest import CLIENT, FREELANCER, OTHER, SEED_DOCS, cite, upload
from test_review import finding, judge, submit

ADMIN = "demo-admin"


def test_chat_history_is_private_to_its_author(env):
    client = env["make"]()
    upload(client, FREELANCER, "PRJ-DEMO-001", SEED_DOCS / "PRJ-DEMO-001_cahier_des_charges.md")
    env["local"].responses = [cite("Fixed price: 18,000 TND excluding VAT")]
    conv = client.post("/api/ai/chat", headers={"X-Demo-User": FREELANCER}, json={"project_id": "PRJ-DEMO-001", "message": "What is the fixed price?"}).json()["conversation_id"]
    history = client.get(f"/api/ai/conversations/{conv}", headers={"X-Demo-User": FREELANCER}).json()
    assert [m["role"] for m in history["messages"]] == ["user", "assistant"]
    assert history["messages"][1]["citations"][0]["verified"] is True
    assert client.get(f"/api/ai/conversations/{conv}", headers={"X-Demo-User": CLIENT}).status_code == 404
    listing = client.get("/api/ai/conversations", params={"project_id": "PRJ-DEMO-001"}, headers={"X-Demo-User": FREELANCER}).json()
    assert listing["conversations"][0]["first_question"] == "What is the fixed price?"


def test_faq_is_public_but_only_admin_edits(env):
    client = env["make"]()
    body = {"question": "How do I upload a document?", "answer": "Use the documents panel.", "language": "en"}
    assert client.post("/api/ai/faq", headers={"X-Demo-User": FREELANCER}, json=body).status_code == 403
    entry = client.post("/api/ai/faq", headers={"X-Demo-User": ADMIN}, json=body).json()["id"]
    assert client.get("/api/ai/faq").json()["faq"][0]["question"] == body["question"]
    assert client.put(f"/api/ai/faq/{entry}", headers={"X-Demo-User": ADMIN}, json={**body, "answer": "Updated."}).status_code == 200
    assert client.delete(f"/api/ai/faq/{entry}", headers={"X-Demo-User": ADMIN}).status_code == 204
    assert client.get("/api/ai/faq").json()["faq"] == []


def test_support_requests_are_scoped_and_admin_triaged(env):
    client = env["make"]()
    created = client.post("/api/ai/support-requests", headers={"X-Demo-User": FREELANCER},
                          json={"subject": "Upload fails", "body": "PDF upload says no text.", "category": "bug", "project_id": "PRJ-DEMO-001"})
    assert created.status_code == 201
    assert client.post("/api/ai/support-requests", headers={"X-Demo-User": OTHER},
                       json={"subject": "x" * 5, "body": "y" * 5, "project_id": "PRJ-DEMO-001"}).status_code == 403
    assert client.get("/api/ai/support-requests", headers={"X-Demo-User": OTHER}).json()["support_requests"] == []
    assert len(client.get("/api/ai/support-requests", headers={"X-Demo-User": ADMIN}).json()["support_requests"]) == 1
    rid = created.json()["id"]
    assert client.patch(f"/api/ai/support-requests/{rid}", headers={"X-Demo-User": FREELANCER}, json={"status": "closed"}).status_code == 403
    assert client.patch(f"/api/ai/support-requests/{rid}", headers={"X-Demo-User": ADMIN}, json={"status": "closed"}).json()["status"] == "closed"


def test_explain_finding_uses_the_assistant_with_document_citations(env):
    client = env["make"]()
    client.app.state.run_reviews_inline = True
    upload(client, FREELANCER, "PRJ-DEMO-001", SEED_DOCS / "PRJ-DEMO-001_cahier_des_charges.md")
    deliverable = submit(client).json()["deliverable_id"]
    env["hosted"].responses = [judge({"NN-1": ("violates", [finding("src/slots.py", 6, 6, "MAX_ORDERS_PER_SLOT = 25")])})] * 13
    review_id = client.post(f"/api/ai/deliverables/{deliverable}/review", headers={"X-Demo-User": CLIENT}).json()["review_id"]
    finding_id = client.get(f"/api/ai/reviews/{review_id}", headers={"X-Demo-User": CLIENT}).json()["findings"][0]["id"]
    env["local"].responses = [cite("a shop accepts at most 20 orders per 15-minute pickup slot")]
    body = client.post(f"/api/ai/findings/{finding_id}/explain", headers={"X-Demo-User": FREELANCER}).json()
    assert body["status"] == "answered" and "Non-negotiable" in body["citations"][0]["section"]
    assert client.post(f"/api/ai/findings/{finding_id}/explain", headers={"X-Demo-User": OTHER}).status_code == 403
