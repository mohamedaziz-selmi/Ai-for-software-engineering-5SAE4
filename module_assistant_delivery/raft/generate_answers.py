"""Generates answers for a prompt file with the 4-bit base model, or the base + a LoRA adapter (RAFT run 2 selection).

Training venv (.venv-raft), private Ollama stopped (it needs the GPU). Greedy decoding, prompts exactly as the
runtime renders them. Unlike the app, decoding is not JSON-schema constrained here, so a malformed reply counts
as a failure: the comparison between candidates stays fair because all of them are run the same way.

  .venv-raft\\Scripts\\python.exe raft\\generate_answers.py --label base
  .venv-raft\\Scripts\\python.exe raft\\generate_answers.py --label run2a --adapter raft\\outputs\\qwen2.5-7b-raft2a\\adapter
  (--prompts raft\\data\\generated_v2\\test.jsonl for the generator-shaped test split)
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(MODULE_ROOT / "storage" / "hf"))
RESULTS = MODULE_ROOT / "raft" / "results"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--adapter", default="", help="LoRA adapter directory; empty = the base model alone")
    parser.add_argument("--base", default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit")
    parser.add_argument("--prompts", default=str(MODULE_ROOT / "raft" / "data" / "handwritten_val" / "prompts.jsonl"))
    parser.add_argument("--max-new", type=int, default=512)
    parser.add_argument("--duty", type=float, default=1.0, help="average GPU load: 0.5 = rest as long as each answer took")
    args = parser.parse_args()

    import torch
    from unsloth import FastLanguageModel
    from train import cool_down  # same heat guard as training

    heat: dict = {}

    model, tokenizer = FastLanguageModel.from_pretrained(model_name=args.adapter or args.base, max_seq_length=4096, load_in_4bit=True, dtype=None)
    FastLanguageModel.for_inference(model)
    rows = [json.loads(l) for l in Path(args.prompts).read_text(encoding="utf-8").splitlines() if l.strip()]
    out = []
    for row in rows:
        messages = [m for m in row["messages"] if m["role"] != "assistant"]  # training-split rows carry their target
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt", add_special_tokens=False).to("cuda")
        started = time.perf_counter()
        with torch.no_grad():
            # repetition_penalty=1.0: Qwen's generation_config sets 1.05, which transformers applies to the WHOLE prompt,
            # so numbers copied from the document were penalised ("21 days" came out as "22 days", 2026-10-19).
            # Ollama only penalises the last 64 tokens, so the app itself was not affected this way.
            generated = model.generate(**inputs, max_new_tokens=args.max_new, do_sample=False, repetition_penalty=1.0)
        reply = tokenizer.decode(generated[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        took = time.perf_counter() - started
        out.append({"id": row["id"], "reply": reply, "seconds": round(took, 2)})
        if args.duty < 1.0:
            time.sleep(took * (1 - args.duty) / args.duty)
            cool_down(heat)  # pause at 76 C until 70 C: below the owner's 79 C limit
    RESULTS.mkdir(parents=True, exist_ok=True)
    name = f"answers_{Path(args.prompts).stem}_{args.label}.jsonl"
    (RESULTS / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print(f"{len(out)} answers -> raft/results/{name} | GPU max {heat.get('max_temp_c')} C, heat pauses {heat.get('heat_pauses', 0)}")


if __name__ == "__main__":
    main()
