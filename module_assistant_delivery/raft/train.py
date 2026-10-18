"""RAFT training with Unsloth 4-bit QLoRA (spec 8.5). Run in .venv-raft with the private Ollama stopped.

Smoke run (feasibility: memory, speed, OOM) then the planned run, e.g.:
  .venv-raft\\Scripts\\python.exe raft\\train.py --model unsloth/Qwen3-4B-Instruct-2507-bnb-4bit --run qwen3-4b-smoke --smoke
  .venv-raft\\Scripts\\python.exe raft\\train.py --model unsloth/Qwen3-4B-Instruct-2507-bnb-4bit --run qwen3-4b-raft --epochs 2

Examples longer than --max-seq tokens are DROPPED and counted, never truncated (evidence and targets
stay whole). Loss is computed on the assistant JSON only. Results (real numbers) go to raft/results/.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(MODULE_ROOT / "storage" / "hf"))
DATA = MODULE_ROOT / "raft" / "data" / "generated"
RESULTS = MODULE_ROOT / "raft" / "results"
OUTPUTS = MODULE_ROOT / "raft" / "outputs"


def load(split: str) -> list[dict]:
    return [json.loads(l) for l in (DATA / f"{split}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="4-bit checkpoint of the SAME model that is served as the base")
    parser.add_argument("--run", required=True)
    parser.add_argument("--max-seq", type=int, default=2048)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--smoke", action="store_true", help="4 optimizer steps (4 x grad-accum examples) only: feasibility check")
    args = parser.parse_args()

    import torch
    from unsloth import FastLanguageModel  # import before transformers/trl, as Unsloth requires
    from unsloth.chat_templates import train_on_responses_only
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    record: dict = {"run": args.run, "model": args.model, "max_seq": args.max_seq, "lora_rank": args.rank,
                    "grad_accum": args.grad_accum, "lr": args.lr, "epochs": args.epochs, "smoke": args.smoke,
                    "gpu": torch.cuda.get_device_name(0), "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    free, total = torch.cuda.mem_get_info()
    record["vram_free_before_mib"] = free // 2**20
    record["vram_total_mib"] = total // 2**20

    t0 = time.perf_counter()
    model, tokenizer = FastLanguageModel.from_pretrained(model_name=args.model, max_seq_length=args.max_seq, load_in_4bit=True, dtype=None)
    model = FastLanguageModel.get_peft_model(
        model, r=args.rank, lora_alpha=args.rank, lora_dropout=0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=3407,
    )
    record["load_s"] = round(time.perf_counter() - t0, 1)
    record["vram_after_load_mib"] = torch.cuda.memory_reserved() // 2**20

    def to_text(rows: list[dict]) -> tuple[list[dict], int, int]:
        kept, dropped, longest = [], 0, 0
        for r in rows:
            text = tokenizer.apply_chat_template(r["messages"], tokenize=False)
            n = len(tokenizer(text, add_special_tokens=False)["input_ids"])
            longest = max(longest, n)
            if n > args.max_seq:
                dropped += 1
                continue
            kept.append({"text": text})
        return kept, dropped, longest

    train_rows, train_drop, train_longest = to_text(load("train"))
    val_rows, val_drop, _ = to_text(load("val"))
    if args.smoke:
        val_rows = val_rows[:16]
    record.update({"train_examples": len(train_rows), "train_dropped_too_long": train_drop, "longest_example_tokens": train_longest,
                   "val_examples": len(val_rows), "val_dropped_too_long": val_drop})

    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer,
        train_dataset=Dataset.from_list(train_rows), eval_dataset=Dataset.from_list(val_rows),
        args=SFTConfig(
            output_dir=str(OUTPUTS / args.run), dataset_text_field="text", max_seq_length=args.max_seq, packing=False,
            per_device_train_batch_size=1, per_device_eval_batch_size=1, gradient_accumulation_steps=args.grad_accum,
            num_train_epochs=args.epochs, max_steps=4 if args.smoke else -1,
            learning_rate=args.lr, warmup_steps=2 if args.smoke else 10, lr_scheduler_type="linear", optim="adamw_8bit", weight_decay=0.01,
            logging_steps=1, report_to="none", seed=3407,
            # Planned runs: validation loss every epoch and keep the best epoch (guards against overfitting
            # the templated synthetic data). Smoke runs skip evaluation during training.
            eval_strategy="no" if args.smoke else "epoch", save_strategy="no" if args.smoke else "epoch",
            save_total_limit=None if args.smoke else 2, load_best_model_at_end=not args.smoke,
            metric_for_best_model="eval_loss", greater_is_better=False,
            bf16=torch.cuda.is_bf16_supported(), fp16=not torch.cuda.is_bf16_supported(),
        ),
    )
    # Loss on the assistant JSON only (Qwen chat format).
    trainer = train_on_responses_only(trainer, instruction_part="<|im_start|>user\n", response_part="<|im_start|>assistant\n")

    torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    try:
        stats = trainer.train()
        record["status"] = "completed"
        record["train_loss"] = round(stats.training_loss, 4)
        record["optimizer_steps"] = stats.global_step
    except torch.OutOfMemoryError as exc:
        record["status"] = "out_of_memory"
        record["error"] = str(exc)[:400]
    record["train_s"] = round(time.perf_counter() - t0, 1)
    record["peak_vram_allocated_mib"] = torch.cuda.max_memory_allocated() // 2**20
    record["peak_vram_reserved_mib"] = torch.cuda.max_memory_reserved() // 2**20
    record["loss_curve"] = [round(h["loss"], 4) for h in trainer.state.log_history if "loss" in h]
    record["val_loss_per_epoch"] = [round(h["eval_loss"], 4) for h in trainer.state.log_history if "eval_loss" in h]
    record["best_checkpoint"] = trainer.state.best_model_checkpoint

    if record["status"] == "completed":
        metrics = trainer.evaluate()
        record["val_loss"] = round(metrics["eval_loss"], 4)
        if not args.smoke:
            adapter = OUTPUTS / args.run / "adapter"
            model.save_pretrained(str(adapter))
            tokenizer.save_pretrained(str(adapter))
            record["adapter_dir"] = str(adapter.relative_to(MODULE_ROOT))
    record["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{args.run}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in record.items() if k != "loss_curve"}, indent=2))


if __name__ == "__main__":
    main()
