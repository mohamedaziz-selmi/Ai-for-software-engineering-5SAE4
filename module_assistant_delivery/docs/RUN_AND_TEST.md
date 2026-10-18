# Run and test the AI Assistant & Delivery Review module

On a new PC, run `scripts\setup.ps1` once first (see `README.md`). Commands are for PowerShell, run from
the `module_assistant_delivery` folder.

## 1. Start

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1
```

Three minimized windows open: the private model server, the module (port 8003) and the gateway (port 8080).
Wait until the script prints the addresses. Then open **http://127.0.0.1:8080/assistant/**.

From the template dashboard instead: in the `freelance2` folder run `npm run dev`, open
http://127.0.0.1:8766/ and click the **AI Assistant & Delivery Review** tile.

## 2. Automated tests (about 1 minute)

```powershell
cd backend; ..\.venv\Scripts\python.exe -m pytest; cd ..
```

Expected: `47 passed`.

## 3. Health

Open http://127.0.0.1:8080/api/ai/health. Expected: `"ready": true`. The `review` part says `configured`
when your Groq key is in `.env`, and `degraded` without it.

## 4. Assistant (tab 01 Project assistant)

1. Identity **Freelancer A (demo)**, project **Atelier Lumière**.
2. Ask: *How many orders can a shop accept per pickup slot?*
   Expected: at most 20 orders per 15-minute slot, with citation C1 marked verified. The first question
   takes about a minute (models load), later ones about 10 seconds.
3. Ask: *What is the hosting budget for the second year?*
   Expected: the information is not in the project documents (no invented answer).
4. Switch the identity to **Freelancer C (demo, other project only)**. Expected: Atelier Lumière is not
   available (not a project member).

## 5. Delivery review (tab 02, needs the Groq key in `.env`)

1. Identity **Freelancer A (demo)**. Under *Requirements*, click **Extract from documents**.
2. Under *Submit a deliverable*: milestone **M2: customer ordering flow on staging**, folder
   `data\seed\deliverables\PRJ-DEMO-001_M2`, then **Submit**.
3. Click **Run review** (about 2 minutes). Expected: a conformance report whose findings cite file and
   lines. The planted defects are found:
   - NN-1: capacity 25 instead of 20 and booking closes 1 hour before the slot, in `src/slots.py`.
   - NN-4: SHA-256 password hashing instead of Argon2id or bcrypt, in `src/accounts.py`.
4. Switch to **Client B (demo)** and click **Open last review**. Accept or dismiss a finding, or use
   **Explain this finding**.

## 6. Help & support (tab 03)

The FAQ lists the entries. Send a support request. Expected: *Request recorded.*

## 7. Stop

Close the three minimized windows.

## Optional: evaluations (local model, fallback off)

```powershell
.\.venv\Scripts\python.exe eval\run_assistant_eval.py --model qwen2.5:7b-instruct --label check
```

Results go to `eval\results\`.
