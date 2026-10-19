"""Resource-aware admission control for local model training and inference jobs."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, asdict
from typing import Callable, Optional

import psutil

LOGGER = logging.getLogger(__name__)

try:
    import pynvml
except ImportError:  # pragma: no cover - exercised on machines without NVML
    pynvml = None


@dataclass(frozen=True)
class ResourceLimits:
    """Admission and warning limits. They are policies, not hardware guarantees."""

    cpu_start_percent: float = 80.0
    cpu_stop_percent: float = 90.0
    ram_start_percent: float = 80.0
    ram_stop_percent: float = 90.0
    vram_start_percent: float = 80.0
    vram_stop_percent: float = 90.0
    gpu_warning_temperature_c: float = 80.0
    gpu_stop_temperature_c: float = 85.0
    sample_interval_seconds: float = 1.0


@dataclass(frozen=True)
class ResourceSnapshot:
    """Point-in-time telemetry. Missing sensors are represented by ``None``."""

    cpu_percent: float
    ram_percent: float
    logical_cpus: int
    gpu_name: Optional[str] = None
    gpu_percent: Optional[float] = None
    vram_percent: Optional[float] = None
    temperature_c: Optional[float] = None
    sensor_error: Optional[str] = None


class ResourceGuard:
    """Monitor resources and prevent unsafe background jobs from starting.

    The guard does not cap GPU utilization and does not replace manufacturer
    thermal protections. It only admits, pauses, or rejects application jobs
    based on observed telemetry and configured policy thresholds.
    """

    def __init__(self, limits: ResourceLimits | None = None, logger: logging.Logger | None = None):
        self.limits = limits or ResourceLimits()
        self.logger = logger or LOGGER
        self._nvml_ready = False
        self._init_nvml()

    def _init_nvml(self) -> None:
        if pynvml is None:
            return
        try:
            pynvml.nvmlInit()
            self._nvml_ready = True
        except Exception as exc:  # pragma: no cover - driver dependent
            self.logger.warning("NVML unavailable: %s", exc)

    def snapshot(self) -> ResourceSnapshot:
        """Return CPU/RAM/GPU telemetry and report unavailable sensors honestly."""
        gpu_name = gpu_percent = vram_percent = temperature_c = None
        sensor_error = None
        if self._nvml_ready:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                name = pynvml.nvmlDeviceGetName(handle)
                gpu_name = name.decode() if hasattr(name, "decode") else str(name)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_percent = float(util.gpu)
                vram_percent = float(memory.used / memory.total * 100)
                temperature_c = float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
            except Exception as exc:  # pragma: no cover - driver dependent
                sensor_error = f"NVML read failed: {exc}"
        else:
            sensor_error = "NVML unavailable; GPU telemetry is not reported"
        return ResourceSnapshot(
            cpu_percent=float(psutil.cpu_percent(interval=self.limits.sample_interval_seconds)),
            ram_percent=float(psutil.virtual_memory().percent),
            logical_cpus=os.cpu_count() or 1,
            gpu_name=gpu_name,
            gpu_percent=gpu_percent,
            vram_percent=vram_percent,
            temperature_c=temperature_c,
            sensor_error=sensor_error,
        )

    def safe_to_start(self, snapshot: ResourceSnapshot | None = None, gpu_required: bool = False) -> bool:
        """Return whether a new job may start under the start thresholds."""
        current = snapshot or self.snapshot()
        if current.cpu_percent >= self.limits.cpu_start_percent or current.ram_percent >= self.limits.ram_start_percent:
            return False
        if gpu_required:
            if current.vram_percent is None:
                self.logger.warning("GPU job denied because VRAM telemetry is unavailable")
                return False
            if current.vram_percent >= self.limits.vram_start_percent:
                return False
            if current.temperature_c is not None and current.temperature_c >= self.limits.gpu_warning_temperature_c:
                return False
        return True

    def should_pause(self, snapshot: ResourceSnapshot | None = None, gpu_required: bool = False) -> bool:
        """Return whether a running job should pause or throttle."""
        current = snapshot or self.snapshot()
        if current.cpu_percent >= self.limits.cpu_stop_percent or current.ram_percent >= self.limits.ram_stop_percent:
            return True
        if gpu_required and ((current.vram_percent is not None and current.vram_percent >= self.limits.vram_stop_percent) or (current.temperature_c is not None and current.temperature_c >= self.limits.gpu_stop_temperature_c)):
            return True
        return False

    def bounded_thread_count(self) -> int:
        """Return the default training concurrency requested by the brief."""
        return max(1, (os.cpu_count() or 1) // 2)

    def environment(self) -> dict[str, str]:
        """Return bounded BLAS/OpenMP settings for child training processes."""
        count = str(self.bounded_thread_count())
        return {"OMP_NUM_THREADS": count, "MKL_NUM_THREADS": count, "OPENBLAS_NUM_THREADS": count, "NUMEXPR_NUM_THREADS": count}

    def as_dict(self, snapshot: ResourceSnapshot | None = None) -> dict:
        """Serialize telemetry for structured logs or a status endpoint."""
        return asdict(snapshot or self.snapshot())
