from app.resource_guard import ResourceGuard, ResourceLimits, ResourceSnapshot


def test_cpu_and_ram_thresholds_deny_start():
    guard = ResourceGuard(ResourceLimits(sample_interval_seconds=0))
    busy = ResourceSnapshot(cpu_percent=81, ram_percent=20, logical_cpus=16)
    assert guard.safe_to_start(busy) is False


def test_gpu_job_requires_safe_gpu_telemetry():
    guard = ResourceGuard(ResourceLimits(sample_interval_seconds=0))
    missing_gpu = ResourceSnapshot(cpu_percent=10, ram_percent=20, logical_cpus=16)
    assert guard.safe_to_start(missing_gpu, gpu_required=True) is False
    safe_gpu = ResourceSnapshot(cpu_percent=10, ram_percent=20, logical_cpus=16, vram_percent=25, temperature_c=54)
    assert guard.safe_to_start(safe_gpu, gpu_required=True) is True


def test_thread_count_is_bounded():
    guard = ResourceGuard(ResourceLimits(sample_interval_seconds=0))
    assert guard.bounded_thread_count() >= 1
    assert len(guard.environment()) == 4
