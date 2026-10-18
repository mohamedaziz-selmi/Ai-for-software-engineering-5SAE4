"""Requantize a bf16 GGUF in pure Python (gguf-py from llama.cpp v0.5.0, storage/tools).

Why: Ollama 0.40.6 only quantizes safetensors imports (via an MLX importer without Qwen2 support) and
rejects LoRA adapters, so the GGUF must arrive pre-quantized. gguf-py can write Q5_0/Q8_0 (not K-quants).
Layout, like llama.cpp's quantizer: 2-D weights -> Q5_0; token embeddings and output head -> Q8_0;
F32 tensors (norms, biases) unchanged. Large tensors are processed in row chunks to bound RAM.

  .venv-raft\\Scripts\\python.exe -E -s raft\\requant_gguf.py IN.bf16.gguf OUT.q5_0.gguf
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "storage" / "tools" / "llama.cpp-v0.5.0-src" / "extracted" / "gguf-py"))

import gguf  # noqa: E402
from gguf.quants import dequantize, quant_shape_from_byte_shape, quant_shape_to_byte_shape, quantize  # noqa: E402

T = gguf.GGMLQuantizationType
HIGH_PRECISION = {"token_embd.weight", "output.weight"}
ROWS_PER_CHUNK = 8192


def target_type(tensor) -> T:
    if tensor.tensor_type == T.F32:
        return T.F32
    shape = quant_shape_from_byte_shape(tensor.data.shape, tensor.tensor_type)
    if len(shape) != 2 or shape[-1] % 32:
        return T.F32
    return T.Q8_0 if tensor.name in HIGH_PRECISION else T.Q5_0


def convert(tensor, qtype: T) -> np.ndarray:
    if qtype == T.F32 and tensor.tensor_type == T.F32:
        return tensor.data
    rows, cols = quant_shape_from_byte_shape(tensor.data.shape, tensor.tensor_type)
    if qtype == T.F32:
        return dequantize(tensor.data, tensor.tensor_type).astype(np.float32).reshape(rows, cols)
    out = np.empty(quant_shape_to_byte_shape((rows, cols), qtype), dtype=np.uint8)
    for start in range(0, rows, ROWS_PER_CHUNK):
        part = dequantize(tensor.data[start : start + ROWS_PER_CHUNK], tensor.tensor_type).astype(np.float32)
        out[start : start + ROWS_PER_CHUNK] = quantize(part, qtype)
    return out


def main(src: str, dst: str) -> None:
    started = time.perf_counter()
    reader = gguf.GGUFReader(src)
    arch = reader.fields["general.architecture"].contents()
    writer = gguf.GGUFWriter(dst, arch=arch, endianess=reader.endianess)
    for field in reader.fields.values():
        if field.name == gguf.Keys.General.ARCHITECTURE or field.name.startswith("GGUF."):
            continue
        value_type = field.types[0]
        sub_type = field.types[-1] if value_type == gguf.GGUFValueType.ARRAY else None
        value = field.contents()
        if field.name == gguf.Keys.General.FILE_TYPE:
            value = int(gguf.LlamaFileType.MOSTLY_Q5_0)
        writer.add_key_value(field.name, value, value_type, sub_type=sub_type)

    plan = [(t, target_type(t)) for t in reader.tensors]
    for tensor, qtype in plan:
        if qtype == T.F32:
            shape = quant_shape_from_byte_shape(tensor.data.shape, tensor.tensor_type) if tensor.tensor_type != T.F32 else tensor.data.shape
            writer.add_tensor_info(tensor.name, shape, np.dtype(np.float32), int(np.prod(shape)) * 4)
        else:
            byte_shape = quant_shape_to_byte_shape(quant_shape_from_byte_shape(tensor.data.shape, tensor.tensor_type), qtype)
            writer.add_tensor_info(tensor.name, byte_shape, np.dtype(np.uint8), int(np.prod(byte_shape)), raw_dtype=qtype)
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_ti_data_to_file()
    counts: dict[str, int] = {}
    for i, (tensor, qtype) in enumerate(plan, start=1):
        writer.write_tensor_data(convert(tensor, qtype), tensor_endianess=reader.endianess)
        counts[qtype.name] = counts.get(qtype.name, 0) + 1
        if i % 40 == 0:
            print(f"{i}/{len(plan)} tensors, {time.perf_counter() - started:.0f}s", flush=True)
    writer.close()
    print(f"done in {time.perf_counter() - started:.0f}s: {counts} -> {dst} ({Path(dst).stat().st_size / 2**30:.2f} GiB)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
