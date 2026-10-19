"""Offline merge + Ollama import (this Ollama version rejects LoRA ADAPTER lines).

Streams the local 4-bit checkpoint tensor by tensor: NF4 weights are dequantized on the GPU with
bitsandbytes; with --mode raft the trained LoRA delta (B @ A * alpha/r) is added; everything is written as
bf16 safetensors. Then `ollama create --quantize int4` imports it into the private Ollama with the base
model's chat template and parameters (and its licence text).

Run it twice for a fair comparison: --mode base (same 4-bit weights, no adapter) and --mode raft. Both go
through the identical dequantize -> bf16 -> int4 import path, so the only difference is the adapter.

  .venv-raft\\Scripts\\python.exe raft\\merge_export.py --mode base --tag assistant-base-requant:qwen2.5-7b
  .venv-raft\\Scripts\\python.exe raft\\merge_export.py --mode raft --tag assistant-raft:qwen2.5-7b
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(MODULE_ROOT / "storage" / "hf"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
BASE_REPO = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
QS_SUFFIXES = (".absmax", ".quant_map", ".nested_absmax", ".nested_quant_map", ".quant_state.bitsandbytes__nf4")


def ollama(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "OLLAMA_HOST": "127.0.0.1:11435"}
    return subprocess.run(["ollama", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)


def main() -> None:
    import bitsandbytes.functional as bnbf
    import torch
    from huggingface_hub import snapshot_download
    from safetensors import safe_open
    from safetensors.torch import save_file
    from train import cool_down  # same heat guard as training (owner's 79 C limit)

    heat: dict = {}
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["base", "raft"], required=True)
    parser.add_argument("--run", default="qwen2.5-7b-raft")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--base-tag", default="qwen2.5:7b-instruct", help="Ollama tag whose template/parameters/licence are reused")
    parser.add_argument("--no-import", action="store_true", help="only write merged bf16 safetensors (then raft/requant_gguf.py)")
    parser.add_argument("--quantize", default="int4", help="Ollama 0.40 safetensors import accepts int4, int8, nvfp4, mxfp4, mxfp8")
    args = parser.parse_args()

    src = Path(snapshot_download(BASE_REPO, local_files_only=True))
    out = MODULE_ROOT / "raft" / "outputs" / args.run / f"merged-{args.mode}-bf16"
    record: dict = {"mode": args.mode, "tag": args.tag, "source": BASE_REPO, "out": str(out.relative_to(MODULE_ROOT)), "quantize": args.quantize}
    started = time.perf_counter()

    lora: dict[str, tuple] = {}
    scale = 1.0
    if args.mode == "raft":
        adapter = MODULE_ROOT / "raft" / "outputs" / args.run / "adapter"
        cfg = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8"))
        if cfg.get("use_dora") or cfg.get("use_rslora"):
            raise SystemExit("DoRA/rsLoRA merge not implemented")
        scale = cfg["lora_alpha"] / cfg["r"]
        with safe_open(str(adapter / "adapter_model.safetensors"), "pt") as f:
            tensors = {k: f.get_tensor(k) for k in f.keys()}
        for key in tensors:
            if key.endswith(".lora_A.weight"):
                module = key.removeprefix("base_model.model.").removesuffix(".lora_A.weight")
                lora[f"{module}.weight"] = (tensors[key], tensors[key.replace("lora_A", "lora_B")])
        record.update({"lora_modules": len(lora), "lora_scale": scale})

    if (out / "model.safetensors.index.json").exists() and (out / "config.json").exists():
        record["merge"] = "reused existing merged weights"
        return import_into_ollama(args, out, record)
    out.mkdir(parents=True, exist_ok=True)
    shard: dict = {}
    shard_bytes, shard_index, weight_map, merged = 0, 1, {}, 0

    def flush() -> None:
        nonlocal shard, shard_bytes, shard_index
        if not shard:
            return
        name = f"model-{shard_index:05d}.safetensors"
        save_file(shard, str(out / name), metadata={"format": "pt"})
        weight_map.update({k: name for k in shard})
        shard, shard_bytes, shard_index = {}, 0, shard_index + 1

    with safe_open(str(src / "model.safetensors"), "pt") as f:
        keys = list(f.keys())
        companions = {k for k in keys if k.endswith(QS_SUFFIXES)}
        for key in keys:
            if key in companions:
                continue
            tensor = f.get_tensor(key)
            if f"{key}.quant_state.bitsandbytes__nf4" in companions:
                qs = {suffix[1:]: f.get_tensor(key + suffix) for suffix in QS_SUFFIXES}
                state = bnbf.QuantState.from_dict(qs, device=torch.device("cuda"))
                weight = bnbf.dequantize_4bit(tensor.cuda(), state).float()
                if key in lora:
                    a, b = (t.cuda().float() for t in lora[key])
                    weight += (b @ a) * scale
                    merged += 1
                tensor = weight.to(torch.bfloat16).cpu()
                cool_down(heat)  # owner's 79 C limit: pause at 76 C until 70 C
            shard[key] = tensor.contiguous()
            shard_bytes += tensor.numel() * tensor.element_size()
            if shard_bytes > 3_000_000_000:
                flush()
        flush()
    if args.mode == "raft" and merged != len(lora):
        raise SystemExit(f"Merged {merged} of {len(lora)} LoRA modules: key mismatch")
    (out / "model.safetensors.index.json").write_text(json.dumps({"metadata": {}, "weight_map": weight_map}, indent=1), encoding="utf-8")
    config = json.loads((src / "config.json").read_text(encoding="utf-8"))
    config.pop("quantization_config", None)
    config["torch_dtype"] = "bfloat16"
    (out / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    for name in ("generation_config.json", "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt",
                 "special_tokens_map.json", "added_tokens.json"):
        if (src / name).exists():
            shutil.copy(src / name, out / name)
    record.update({"merged_lora_modules": merged, "merge_s": round(time.perf_counter() - started, 1)})
    if args.no_import:
        results = MODULE_ROOT / "raft" / "results"
        (results / f"{args.run}-merge-{args.mode}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(json.dumps(record, indent=2))
        return
    import_into_ollama(args, out, record)


def import_into_ollama(args, out: Path, record: dict) -> None:
    base = ollama("show", "--modelfile", args.base_tag)
    if base.returncode != 0:
        raise SystemExit(f"Cannot read the base Modelfile ({args.base_tag}); is the private Ollama running? {base.stderr[-300:]}")
    lines = [line for line in base.stdout.splitlines() if not line.startswith("FROM ")]
    modelfile = out.parent / f"Modelfile.{args.mode}"
    modelfile.write_text(f"FROM {out.as_posix()}\n" + "\n".join(lines) + "\n", encoding="utf-8")
    started = time.perf_counter()
    created = ollama("create", args.tag, "-f", str(modelfile), "--quantize", args.quantize)
    record.update({"ollama_create_returncode": created.returncode, "ollama_create_s": round(time.perf_counter() - started, 1),
                   "ollama_output_tail": (created.stdout + created.stderr).strip()[-500:]})
    results = MODULE_ROOT / "raft" / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / f"{args.run}-merge-{args.mode}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, indent=2))
    if created.returncode != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
