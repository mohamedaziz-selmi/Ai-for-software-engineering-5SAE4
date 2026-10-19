## Appendix A: prompt-engineering log for the model tuning

How I steered the model selection, the review tuning and RAFT, written as structured prompts. The wording is
reconstructed from the working session; every step and every result below really happened and is measured in the
file named under it.

---

### A.1 Choosing the model by measurement

```text
ROLE: You are my ML engineer for the AI Assistant & Delivery Review module.
CONTEXT: I have an RTX 4060 Laptop (8 GB VRAM). Two candidate open models: Qwen2.5-7B-Instruct and
Qwen3-4B-Instruct-2507, both served by our private Ollama.
TASK: Compare them on BOTH features with the same retrieval (e5-base, top-5), the same prompts and the same
citation verifier. Hosted fallback OFF during the evaluation.
CONSTRAINTS: No hosted model in the comparison. Report the numbers as measured, even if the difference is small.
ACCEPTANCE: A table per feature (assistant dev set, live delivery review) and a recommendation I can defend.
OUTPUT: eval/results/model_selection.md
```

**Result:** Qwen3-4B → Qwen2.5-7B: review 9/13 → 13/13, scope verdicts 2/5 → 4/5. Kept (`eval/results/model_selection.md`).

---

### A.2 RAFT run 1: first fine-tuning

```text
ROLE: Fine-tuning engineer.
TASK: Fine-tune Qwen2.5-7B-Instruct with RAFT for our RAG prompt, using Unsloth 4-bit QLoRA on my laptop GPU.
DATA: Generated FR/EN project documents with known answers; split by PROJECT (train / val / test never share a
document). Context = the right chunk + the most similar distractor chunks; drop the right chunk in ~20% of cases so
the target is "not in the documents".
HYPERPARAMETERS: LoRA rank 16, alpha 16, all attention and MLP projections, 2 epochs, lr 2e-4, batch 1 x 8.
LOSS: on the assistant JSON only.
ACCEPTANCE: Compare with the SAME base model through the SAME export path, fallback off, on the held-out split AND
on our hand-written dev document. Do not switch the app unless the hand-written results do not regress.
```

**Result:** base → RAFT run 1: held-out abstention 23/33 → 33/33, distractor citations 4 → 0; hand-written dev 23/24 → 20/24 with 1 harmful answer. Not adopted (`eval/results/raft_findings.md`).

---

### A.3 Making the review stricter and repeatable

```text
ROLE: Prompt engineer for the hosted reviewer (gpt-oss-120b on Groq).
PROBLEM: On the corrected deliverable the reviewer called the data-location rule "partial" just because it saw no
analytics code, and some verdicts change from one run to the next.
TASK: Write review_judge.v2: explicit verdict definitions applied in a fixed order (violates, partial, conforms,
cannot_determine), and the rule "the absence of code is never evidence". Use temperature 0 and a fixed seed.
CONSTRAINTS: Keep v1 for traceability, store the prompt version with every result, check that the provider still
accepts strict JSON schema with the seed.
ACCEPTANCE: Run each demo deliverable twice and show, per requirement, which verdicts changed.
```

**Result:** defective deliverable 13/13 (1 run) → 12/13 twice with identical verdicts; false "partial" on data location gone. Kept (`eval/results/review_stability.md`).

---

### A.4 Fixing false rejections in the evidence check

```text
CONTEXT: In one run a correct "conforms" was withheld because the model quoted lines 5-14 but skipped the
docstring on line 11.
TASK: Accept a multi-line quote that skips lines or drops a trailing comment ONLY if every quoted line occurs
inside a real line of the file, in order, within the stated range.
CONSTRAINTS: Nothing reworded or invented may pass. Add regression tests built from the real model outputs.
```

**Result:** same model output 11/13 → 12/13 (withheld REQ-003 restored); reworded quotes still rejected. Kept (`backend/tests/test_review.py`).

---

### A.5 Trying a third review prompt, and rejecting it

```text
TASK: Try review_judge.v3: a requirement part that is planned for a later milestone should make the verdict
"partial", not "violates"; add an example for timing requirements that code performs synchronously.
ACCEPTANCE: Same two-runs-per-deliverable protocol as v2. Keep v3 only if it is at least as accurate AND more stable.
```

**Result:** v2 → v3: requirements whose verdict changed between repeated runs 1 → 2 (REQ-004 now flips); corrected deliverable 12/13 → 11/13 (v3's second run was cut short by the rate limit). Rejected (`eval/results/review_stability.md`).

---

### A.6 RAFT run 2: training data that cannot be memorised

```text
ROLE: Data engineer for RAFT run 2.
DIAGNOSIS: Run 1 learned the generator's layout and answer templates instead of the skill.
TASK: Write a second generator:
  - 4 document styles (bullet sections, numbered contract articles, tables, short brief) in BOTH languages,
    with varied section names;
  - several phrasings for every question and every answer;
  - counter-template examples: features the document explicitly EXCLUDES, asked as "is it included?";
  - more "not in the documents" cases, including related-but-missing facts.
CONSTRAINTS: Reuse the runtime prompt, masker and citation check; every label must pass the runtime verifier.
Never use the demo documents or the final test set.
```

**Result:** 1 style, 1,056 examples → 4 styles × 2 languages, 1,977 examples, 0 labels rejected. Effect: section 7 (`raft/data/generated_v2/stats.json`).

---

### A.7 Choosing checkpoints on hand-written data

```text
TASK: Write a small hand-written validation set in a different style from the generator and from the test set:
two documents (an English statement of work with a table, a French specification with a scope table) and 28
questions (facts, in/out of scope, not in the documents, off-topic).
SCORING: The runtime rules: an answer counts only if a quote passes verification; harmful = an answered scope
question with the opposite verdict, or a "verified" answer to a question the documents do not answer.
USE: Model selection only. The final test set stays untouched until the final comparison.
```

**Result:** a selection set the generator never saw: base 16/28 (scope 0/8, 2 harmful) vs RAFT run 1 22/28 (scope 6/8, 0 harmful) (`raft/results/scores_prompts.json`).

---

### A.8 RAFT run 2: two configurations

```text
TASK: Train two configurations on the new data and compare them on the hand-written validation set:
  A) 1 epoch, LoRA rank 16, lr 2e-4   (run 1's validation loss was already near zero after epoch 1)
  B) 1 epoch, LoRA rank 8,  lr 1e-4   (a gentler update that should generalise better)
CONSTRAINTS (my laptop): the GPU must never exceed 79 C. Rest the GPU as long as it works (about half load), pause
at 76 C until 70 C, and stop the job if it reaches 79 C. I accept that it takes about twice as long.
```

**Result:** A trained (2 h 43 min at half load, GPU peak 61 °C, 0 heat pauses); B not run, the PC was shut down at 05:00. A on the hand-written set: 22/28 → 24/28, scope 6/8 → 8/8, 0 harmful (`raft/results/scores_prompts.json`).

---

### A.9 Fair export and the switch decision

```text
TASK: Export the better adapter (merge -> GGUF -> 5-bit) and evaluate it in the real app pipeline against the base
model on the 33-question test set, fallback off.
DECISION RULE: Switch the app to RAFT only if it beats the base on the hand-written questions AND makes no harmful
mistake. Otherwise keep the base and write down why.
```

**Result:** RAFT 2a vs base in the real app: correct 19/24 vs 23/24, 1 harmful vs 0. Rule not met: base stays the default; RAFT kept as a selectable model and local backup (`eval/results/assistant_final-*.md`).