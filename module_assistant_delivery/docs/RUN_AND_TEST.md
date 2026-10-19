# Run and test the AI Assistant & Delivery Review module

On a new PC, run `scripts\setup.ps1` once first (see `README.md`). Commands are for PowerShell, run from
the `module_assistant_delivery` folder.

## 1. Start

Double-click `..\control_center\START_PLATFORM.cmd`. It starts the control center and the front end (gateway,
facade, dashboard) and opens http://127.0.0.1:8080. Click the round button (bottom right) and switch on
**AI Assistant & Delivery Review**, then open **http://127.0.0.1:8080/assistant/**.

Only this module: `powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1` (private model, module, gateway).

## 2. Automated tests (about 1 minute)

```powershell
cd backend; ..\.venv\Scripts\python.exe -m pytest; cd ..
```

Expected: `61 passed`.

## 3. Health and API (Swagger)

Open http://127.0.0.1:8080/api/ai/health. Expected: `"ready": true`. The `review` part says `configured`
when your Groq key is in `.env`, and `degraded` without it.

Open http://127.0.0.1:8003/api/ai/docs: the 28 operations, each with the refusals it can return. On any operation,
**Try it out**, put a demo identity in `x-demo-user` (`demo-freelancer-a`, `demo-client-b`, `demo-freelancer-c` or
`demo-admin`), fill the fields, **Execute**. For example `GET /api/ai/documents` with `demo-freelancer-c` and
`PRJ-DEMO-001` answers 403: that freelancer is not a member of the project. Report screenshots of these requests:
`scripts\capture_swagger.py`.

## 4. Assistant (page Assistant)

1. Identity **Freelancer A (demo)**, project **Atelier Lumière**.
2. Ask: *How many orders can a shop accept per pickup slot?*
   Expected: at most 20 orders per 15-minute slot, with the quote highlighted under *Sources*. The model loads
   at start-up (about 30 s); answers then take 2 to 3 seconds.
3. Ask: *What is the hosting budget for the second year?*
   Expected: the information is not in the project documents (no invented answer).
4. Model button in the composer → **RAFT fine-tuned**, ask again. Expected: the line under the answer says
   *RAFT fine-tuned answered* (the first answer after a switch takes about 10 s: the model loads).
5. Model menu → **Failure drill** on, ask again. Expected: *Base + RAG skipped by the failure drill → RAFT fine-tuned
   answered* (or the reverse if RAFT is chosen). Switch the drill off.
6. Switch the identity to **Freelancer C (demo, other project only)**. Expected: Atelier Lumière is not
   available (not a project member).

## 5. Delivery review (page Delivery review, needs the Groq key in `.env`)

1. Identity **Freelancer A (demo)**. Under *Requirements*, click **Extract from documents**.
2. Under *Submit a deliverable*: milestone **M2: customer ordering flow on staging**, folder
   `data\seed\deliverables\PRJ-DEMO-001_M2`, then **Submit**.
3. Click **Run review** (about 2 minutes). Expected: a conformance report whose findings cite file and
   lines. The planted defects are found:
   - NN-1: capacity 25 instead of 20 and booking closes 1 hour before the slot, in `src/slots.py`.
   - NN-4: SHA-256 password hashing instead of Argon2id or bcrypt, in `src/accounts.py`.
4. Switch to **Client B (demo)** and click **Open last review**. Accept or dismiss a finding, or use
   **Explain this finding**.

## 5b. A file of every type

`demo\documents` holds one accepted document per type (Markdown, PDF, TXT, DOCX, and a corrected version of the
minutes), `demo\deliverables\M3_back_office` a milestone in 9 file kinds, and `demo\rejected` the files the upload checks
must refuse. What to ask and what to expect: `demo\README.md`, scenarios 14 to 19.

## 6. Help & support (page Help)

The FAQ lists the entries. Send a support request. Expected: *Request recorded.*

## 7. Stop

Close the three minimized windows.

## Optional: evaluations (local model, fallback off)

```powershell
.\.venv\Scripts\python.exe eval\run_assistant_eval.py --model qwen2.5:7b-instruct --label check
```

Results go to `eval\results\`.
