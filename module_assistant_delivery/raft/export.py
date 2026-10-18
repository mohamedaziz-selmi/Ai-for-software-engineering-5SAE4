"""SUPERSEDED by raft/export_gguf.ps1: Ollama 0.40.6 answers "LoRA adapters are no longer supported" (2026-10-18).
Kept as a record of the attempted route.

Serve a trained RAFT adapter from the private Ollama (spec 8.5 "Serve").

Default: no 16-bit merge. The Modelfile is `FROM <base tag>` + `ADAPTER <LoRA>`, so the RAFT model is
the SAME quantized base the app already serves (same template and parameters) plus the trained adapter.
The base-vs-RAFT comparison then differs only by the adapter. (A full 16-bit merge of a 7B would need
~15 GB RAM on a 16 GB laptop and the original 16-bit weights.)

If Ollama rejects a safetensors adapter for this architecture, pass --gguf-converter with the path to
llama.cpp's convert_lora_to_gguf.py to convert the adapter to a GGUF LoRA first.

  .venv-raft\\Scripts\\python.exe raft\\export.py --run qwen2.5-7b-raft --base-tag qwen2.5:7b-instruct --tag assistant-raft:qwen2.5-7b
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = MODULE_ROOT / "raft" / "outputs"
RESULTS = MODULE_ROOT / "raft" / "results"


def ollama(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "OLLAMA_HOST": "127.0.0.1:11435"}
    return subprocess.run(["ollama", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--base-tag", required=True, help="Ollama tag of the served base model (the same checkpoint)")
    parser.add_argument("--tag", required=True, help="Ollama tag for the RAFT model")
    parser.add_argument("--gguf-converter", help="path to llama.cpp convert_lora_to_gguf.py (fallback)")
    parser.add_argument("--base-hf-dir", help="HF directory of the base model (config/tokenizer), needed by the converter")
    args = parser.parse_args()

    adapter = OUTPUTS / args.run / "adapter"
    if not (adapter / "adapter_config.json").exists():
        raise SystemExit(f"No trained adapter at {adapter}")
    target = adapter
    if args.gguf_converter:
        target = OUTPUTS / args.run / "adapter.gguf"
        cmd = [sys.executable, args.gguf_converter, str(adapter), "--outfile", str(target), "--outtype", "f16"]
        if args.base_hf_dir:
            cmd += ["--base", args.base_hf_dir]
        converted = subprocess.run(cmd, capture_output=True, text=True)
        if converted.returncode != 0:
            raise SystemExit(f"GGUF conversion failed: {converted.stderr[-800:]}")

    modelfile = OUTPUTS / args.run / "Modelfile"
    modelfile.write_text(f"FROM {args.base_tag}\nADAPTER {target.as_posix()}\n", encoding="utf-8")
    created = ollama("create", args.tag, "-f", str(modelfile))
    shown = ollama("show", args.tag) if created.returncode == 0 else None
    record = {"run": args.run, "tag": args.tag, "base_tag": args.base_tag, "adapter": str(target.relative_to(MODULE_ROOT)),
              "method": "gguf_lora" if args.gguf_converter else "safetensors_adapter", "returncode": created.returncode,
              "output_tail": (created.stdout + created.stderr).strip()[-800:], "show": shown.stdout[-600:] if shown else None}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{args.run}-export.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, indent=2))
    if created.returncode != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
