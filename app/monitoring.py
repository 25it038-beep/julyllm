"""
HS AI SOLUTIONS - JULY CLOUD AI MONITORING & METRICS
System Health, Memory Footprint, Latency, & Throughput Tracker
Founder: Harshan Seliyan
"""

import os
import time
import threading
from typing import Dict, Any, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class MetricsCollector:
    """
    Thread-safe operational telemetry collector for cloud inference.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.start_time = time.time()
        self.model_loaded_time: Optional[float] = None
        self.load_duration_seconds: float = 0.0

        self.total_requests: int = 0
        self.active_requests: int = 0
        self.error_count: int = 0
        self.total_tokens_generated: int = 0
        self.total_latency_seconds: float = 0.0
        self.last_generation_speed_tps: float = 0.0

    def record_model_load_start(self) -> float:
        return time.time()

    def record_model_load_complete(self, start_ts: float):
        with self._lock:
            self.model_loaded_time = time.time()
            self.load_duration_seconds = round(self.model_loaded_time - start_ts, 3)

    def request_start(self):
        with self._lock:
            self.total_requests += 1
            self.active_requests += 1

    def request_end(self, duration_seconds: float, tokens_count: int = 0, is_error: bool = False):
        with self._lock:
            self.active_requests = max(0, self.active_requests - 1)
            if is_error:
                self.error_count += 1
            else:
                self.total_tokens_generated += tokens_count
                self.total_latency_seconds += duration_seconds
                if duration_seconds > 0 and tokens_count > 0:
                    self.last_generation_speed_tps = round(tokens_count / duration_seconds, 2)

    def get_system_memory(self) -> Dict[str, float]:
        """Returns total, used, and available system memory in MB."""
        if HAS_PSUTIL:
            try:
                mem = psutil.virtual_memory()
                return {
                    "total_mb": round(mem.total / (1024 * 1024), 2),
                    "used_mb": round(mem.used / (1024 * 1024), 2),
                    "available_mb": round(mem.available / (1024 * 1024), 2),
                    "percent_used": mem.percent
                }
            except Exception:
                pass
        # Fallback reading Linux /proc/meminfo if available
        if os.path.exists("/proc/meminfo"):
            try:
                meminfo = {}
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            k = parts[0].strip()
                            v = parts[1].strip().split()[0]
                            meminfo[k] = int(v) * 1024  # kB to bytes
                total = meminfo.get("MemTotal", 0)
                available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
                used = total - available
                return {
                    "total_mb": round(total / (1024 * 1024), 2),
                    "used_mb": round(used / (1024 * 1024), 2),
                    "available_mb": round(available / (1024 * 1024), 2),
                    "percent_used": round((used / total * 100), 1) if total else 0.0
                }
            except Exception:
                pass
        return {"total_mb": 0.0, "used_mb": 0.0, "available_mb": 0.0, "percent_used": 0.0}

    def get_cpu_utilization(self) -> float:
        if HAS_PSUTIL:
            try:
                return psutil.cpu_percent(interval=None)
            except Exception:
                pass
        return 0.0

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            uptime = round(time.time() - self.start_time, 1)
            avg_latency_ms = (
                round((self.total_latency_seconds / max(1, self.total_requests - self.error_count)) * 1000, 2)
                if (self.total_requests - self.error_count) > 0 else 0.0
            )
            mem = self.get_system_memory()
            cpu = self.get_cpu_utilization()

            return {
                "uptime_seconds": uptime,
                "model_load_duration_seconds": self.load_duration_seconds,
                "total_requests": self.total_requests,
                "active_requests": self.active_requests,
                "error_count": self.error_count,
                "total_tokens_generated": self.total_tokens_generated,
                "average_latency_ms": avg_latency_ms,
                "generation_speed_tps": self.last_generation_speed_tps,
                "memory_total_mb": mem["total_mb"],
                "memory_used_mb": mem["used_mb"],
                "memory_available_mb": mem["available_mb"],
                "memory_percent": mem["percent_used"],
                "cpu_percent": cpu,
            }


metrics = MetricsCollector()
