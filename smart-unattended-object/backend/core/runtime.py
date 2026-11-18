"""
runtime.py

Decides *once* how this machine will run inference, and records the reasoning
so a slow deployment can be diagnosed from the logs instead of guessed at.

Three things earn their own module here.

**Device is resolved explicitly, never implicitly.**  The old code called
``torch.cuda.is_available()`` and moved on. When that returns False the whole
system silently drops to CPU and simply feels slow -- the single most common
way a working install turns into a "why is this machine slower" ticket. The
usual cause is not the driver but a CPU-only PyTorch wheel, so
:func:`describe_device` reports ``torch.version.cuda`` too: if that is ``None``
the wheel is wrong and no amount of driver work will fix it.

**FP16 is not automatically a win.**  Half precision is *slower* than FP32 on
compute capability below 7.0 (Pascal and older), because those cards have no
tensor cores. So fp16 is gated on the actual capability of the selected GPU.

**CUDA is asynchronous.**  ``time.perf_counter()`` around a forward pass
measures kernel *dispatch*, not execution, so naive timing under-reports GPU
work by an order of magnitude. :func:`sync` inserts the barrier that makes a
measurement mean something -- and is a no-op on CPU.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Optional

import torch

from backend.core.config import settings
from backend.core.logging import get_logger

log = get_logger("runtime")

_lock = threading.Lock()
_profile: Optional["RuntimeProfile"] = None


@dataclass(frozen=True)
class RuntimeProfile:
    device: str            # "cuda:0" or "cpu" -- always explicit, never bare "cuda"
    is_cuda: bool
    half: bool
    gpu_name: str = ""
    capability: tuple = ()
    total_vram_gb: float = 0.0
    torch_version: str = ""
    cuda_build: Optional[str] = None
    reason: str = ""

    @property
    def torch_device(self) -> torch.device:
        return torch.device(self.device)

    def as_dict(self) -> dict:
        return {
            "device": self.device,
            "is_cuda": self.is_cuda,
            "half_precision": self.half,
            "gpu_name": self.gpu_name,
            "compute_capability": ".".join(str(v) for v in self.capability) if self.capability else None,
            "total_vram_gb": self.total_vram_gb,
            "torch_version": self.torch_version,
            "torch_cuda_build": self.cuda_build,
            "selection_reason": self.reason,
        }


def _resolve() -> RuntimeProfile:
    requested = (settings.device or "auto").strip().lower()
    torch_version = torch.__version__
    cuda_build = torch.version.cuda  # None => CPU-only wheel

    if requested == "cpu":
        _tune_cpu_threads()
        return RuntimeProfile(
            device="cpu", is_cuda=False, half=False,
            torch_version=torch_version, cuda_build=cuda_build,
            reason="explicitly requested via UOD_DEVICE=cpu",
        )

    available = torch.cuda.is_available()

    if not available:
        if cuda_build is None:
            reason = (
                "CUDA unavailable because this PyTorch build has no CUDA support "
                f"(torch {torch_version} reports version.cuda=None). This is a "
                "CPU-only wheel -- reinstall from the CUDA index, e.g. "
                "pip install torch --index-url https://download.pytorch.org/whl/cu121"
            )
        else:
            reason = (
                f"torch {torch_version} was built against CUDA {cuda_build} but no "
                "usable GPU was found -- check the NVIDIA driver (R525+ for cu12x) "
                "and that a device is visible to this process"
            )
        if requested.startswith("cuda"):
            log.error("UOD_DEVICE=%s was requested but %s", requested, reason)
        _tune_cpu_threads()
        return RuntimeProfile(
            device="cpu", is_cuda=False, half=False,
            torch_version=torch_version, cuda_build=cuda_build,
            reason=reason,
        )

    index = 0
    if requested.startswith("cuda:"):
        try:
            index = int(requested.split(":", 1)[1])
        except ValueError:
            index = 0
    if index >= torch.cuda.device_count():
        log.warning(
            "cuda:%d requested but only %d device(s) present; using cuda:0",
            index, torch.cuda.device_count(),
        )
        index = 0

    name = torch.cuda.get_device_name(index)
    capability = torch.cuda.get_device_capability(index)
    vram = torch.cuda.get_device_properties(index).total_memory / (1024 ** 3)

    # Tensor cores arrive at compute capability 7.0 (Volta/Turing). Below that
    # fp16 emulation costs more than the bandwidth it saves.
    tensor_cores = capability[0] >= 7
    half = bool(settings.allow_fp16 and tensor_cores)
    if settings.allow_fp16 and not tensor_cores:
        reason = (
            f"fp32 on {name}: compute capability {capability[0]}.{capability[1]} "
            "predates tensor cores, where fp16 runs slower than fp32"
        )
    elif half:
        reason = f"fp16 on {name} (compute {capability[0]}.{capability[1]}, tensor cores present)"
    else:
        reason = f"fp32 on {name} (fp16 disabled via UOD_FP16)"

    # cuDNN picks the fastest convolution algorithm per input shape and caches
    # it. Worth it here because our input shapes are fixed -- one tile size and
    # one frame size -- so the benchmark cost is paid once, not per frame.
    torch.backends.cudnn.benchmark = True

    return RuntimeProfile(
        device=f"cuda:{index}", is_cuda=True, half=half,
        gpu_name=name, capability=capability, total_vram_gb=round(vram, 2),
        torch_version=torch_version, cuda_build=cuda_build, reason=reason,
    )


def _tune_cpu_threads() -> None:
    """Keep PyTorch from fanning out over every core.

    On CPU, torch defaults to one thread per physical core. With several camera
    threads each entering the model, those thread pools oversubscribe the
    machine and every camera gets slower than it would alone. Leaving a couple
    of cores for frame acquisition and JPEG encoding beats maximum width.
    """
    configured = settings.cpu_threads
    if configured > 0:
        threads = configured
    else:
        cores = os.cpu_count() or 4
        threads = max(1, min(cores - 2, 8))
    try:
        torch.set_num_threads(threads)
    except Exception:  # pragma: no cover - platform dependent
        return
    log.info("CPU inference using %d torch thread(s)", threads)


def get_profile() -> RuntimeProfile:
    """Resolve the runtime profile once and reuse it."""
    global _profile
    if _profile is not None:
        return _profile
    with _lock:
        if _profile is None:
            _profile = _resolve()
            log.info("device: %s | %s", _profile.device, _profile.reason)
    return _profile


def sync() -> None:
    """Barrier so a surrounding timer measures execution, not dispatch."""
    profile = get_profile()
    if profile.is_cuda:
        torch.cuda.synchronize(profile.torch_device)


def vram_snapshot() -> dict:
    """Current VRAM use.

    ``reserved`` exceeding ``allocated`` is the caching allocator holding blocks
    for reuse -- normal, not a leak. Deliberately no ``empty_cache()`` helper:
    calling it in a hot loop forces the allocator to re-request memory from the
    driver every frame and measurably slows inference.
    """
    profile = get_profile()
    if not profile.is_cuda:
        return {}
    device = profile.torch_device
    return {
        "allocated_gb": round(torch.cuda.memory_allocated(device) / 1024 ** 3, 3),
        "reserved_gb": round(torch.cuda.memory_reserved(device) / 1024 ** 3, 3),
        "total_gb": profile.total_vram_gb,
    }


def describe_device() -> dict:
    return {**get_profile().as_dict(), **({"vram": vram_snapshot()} if get_profile().is_cuda else {})}
