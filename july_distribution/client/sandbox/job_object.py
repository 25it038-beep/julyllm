"""
HS AI SOLUTIONS — WINDOWS SANDBOX EXECUTION ENGINE
Module: july_distribution.client.sandbox.job_object
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Architecture: Windows Isolated Execution Engine

Provides production-grade Windows Job Object management:
- Hard process and job memory limits (JOB_OBJECT_LIMIT_PROCESS_MEMORY, JOB_OBJECT_LIMIT_JOB_MEMORY)
- Hard CPU rate cap (JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP)
- Process tree tracking and automatic termination on job close (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
- Atomic termination of entire process tree (TerminateJobObject)
- Kernel accounting query (QueryInformationJobObject)
"""

from __future__ import annotations
import os
import sys
import ctypes
from ctypes import wintypes
from typing import Optional, Dict, Any, List

# Windows Kernel32 DLL binding
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Win32 Limit Flags
JOB_OBJECT_LIMIT_WORKINGSET = 0x00000001
JOB_OBJECT_LIMIT_PROCESS_TIME = 0x00000002
JOB_OBJECT_LIMIT_JOB_TIME = 0x00000004
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
JOB_OBJECT_LIMIT_AFFINITY = 0x00000010
JOB_OBJECT_LIMIT_PRIORITY_CLASS = 0x00000020
JOB_OBJECT_LIMIT_PRESERVE_JOB_TIME = 0x00000040
JOB_OBJECT_LIMIT_SCHEDULING_CLASS = 0x00000080
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x00000400
JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00001000
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

# CPU Rate Control Flags
JOB_OBJECT_CPU_RATE_CONTROL_ENABLE = 0x00000001
JOB_OBJECT_CPU_RATE_CONTROL_WEIGHT_BASED = 0x00000002
JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP = 0x00000004
JOB_OBJECT_CPU_RATE_CONTROL_NOTIFY = 0x00000008
JOB_OBJECT_CPU_RATE_CONTROL_MIN_MAX_RATE = 0x00000010

# Information Classes
JobObjectBasicAccountingInformation = 1
JobObjectBasicLimitInformation = 2
JobObjectBasicProcessIdList = 3
JobObjectBasicUIRestrictions = 4
JobObjectSecurityLimitInformation = 5
JobObjectEndOfJobTimeInformation = 6
JobObjectAssociateCompletionPortInformation = 7
JobObjectBasicAndIoAccountingInformation = 8
JobObjectExtendedLimitInformation = 9
JobObjectCpuRateControlInformation = 15


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class JOBOBJECT_CPU_RATE_CONTROL_INFORMATION(ctypes.Structure):
    class DUMMYUNIONNAME(ctypes.Union):
        _fields_ = [
            ("CpuRate", wintypes.DWORD),
            ("Weight", wintypes.DWORD),
        ]
    _anonymous_ = ("DUMMYUNIONNAME",)
    _fields_ = [
        ("ControlFlags", wintypes.DWORD),
        ("DUMMYUNIONNAME", DUMMYUNIONNAME),
    ]


class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_int64),
        ("TotalKernelTime", ctypes.c_int64),
        ("ThisPeriodTotalUserTime", ctypes.c_int64),
        ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


# Setup argtypes & restypes
kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
kernel32.CreateJobObjectW.restype = wintypes.HANDLE

kernel32.SetInformationJobObject.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    wintypes.DWORD
]
kernel32.SetInformationJobObject.restype = wintypes.BOOL

kernel32.QueryInformationJobObject.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD)
]
kernel32.QueryInformationJobObject.restype = wintypes.BOOL

kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
kernel32.AssignProcessToJobObject.restype = wintypes.BOOL

kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.TerminateJobObject.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


class WindowsJobObject:
    """
    Manages a Win32 Job Object with strict resource enforcement:
    - Hard Process & Job memory quotas (OOM termination)
    - Hard CPU cap
    - Max active processes (anti-forkbomb)
    - Kill-on-close guarantee
    """

    def __init__(
        self,
        name: Optional[str] = None,
        max_process_memory_mb: int = 512,
        max_job_memory_mb: int = 1024,
        max_active_processes: int = 16,
        cpu_rate_percent: float = 50.0,
        kill_on_close: bool = True
    ):
        self.name = name
        self.max_process_memory_mb = max_process_memory_mb
        self.max_job_memory_mb = max_job_memory_mb
        self.max_active_processes = max_active_processes
        self.cpu_rate_percent = cpu_rate_percent
        self.kill_on_close = kill_on_close

        self._handle: Optional[wintypes.HANDLE] = None
        self._is_active = False
        self._assigned_pids: List[int] = []

        self._initialize_job()

    @property
    def handle(self) -> Optional[wintypes.HANDLE]:
        return self._handle

    @property
    def is_active(self) -> bool:
        return self._is_active and (self._handle is not None)

    def _initialize_job(self):
        """Creates the Job Object and applies all security and resource quotas."""
        if os.name != "nt":
            raise OSError("WindowsJobObject is exclusively supported on Windows NT kernels.")

        if self.max_process_memory_mb <= 0 or self.max_job_memory_mb <= 0:
            raise ValueError(
                f"Invalid memory limits: process={self.max_process_memory_mb}MB, job={self.max_job_memory_mb}MB"
            )

        hJob = kernel32.CreateJobObjectW(None, self.name)
        if not hJob:
            err = ctypes.get_last_error()
            raise OSError(f"Failed to create Windows Job Object (Win32 Error: {err})")

        self._handle = hJob
        self._is_active = True

        # 1. Apply Extended Limit Information
        ext_limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limit_flags = (
            JOB_OBJECT_LIMIT_PROCESS_MEMORY |
            JOB_OBJECT_LIMIT_JOB_MEMORY |
            JOB_OBJECT_LIMIT_ACTIVE_PROCESS |
            JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
        )
        if self.kill_on_close:
            limit_flags |= JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

        ext_limits.BasicLimitInformation.LimitFlags = limit_flags
        ext_limits.BasicLimitInformation.ActiveProcessLimit = self.max_active_processes
        ext_limits.ProcessMemoryLimit = int(self.max_process_memory_mb * 1024 * 1024)
        ext_limits.JobMemoryLimit = int(self.max_job_memory_mb * 1024 * 1024)

        ok = kernel32.SetInformationJobObject(
            self._handle,
            JobObjectExtendedLimitInformation,
            ctypes.byref(ext_limits),
            ctypes.sizeof(ext_limits)
        )
        if not ok:
            err = ctypes.get_last_error()
            self.close()
            raise OSError(f"Failed to set JobObjectExtendedLimitInformation (Win32 Error: {err})")

        # 2. Apply CPU Rate Control Information (Hard Cap)
        if self.cpu_rate_percent > 0:
            cpu_info = JOBOBJECT_CPU_RATE_CONTROL_INFORMATION()
            cpu_info.ControlFlags = JOB_OBJECT_CPU_RATE_CONTROL_ENABLE | JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP
            # CpuRate is expressed as cycles per 10,000 cycles (e.g. 50% = 5,000)
            rate_val = int(min(100.0, max(1.0, self.cpu_rate_percent)) * 100)
            cpu_info.CpuRate = rate_val

            # Note: CPU rate control may fail on older Windows or if hypervisor restricts it; handle gracefully
            ok_cpu = kernel32.SetInformationJobObject(
                self._handle,
                JobObjectCpuRateControlInformation,
                ctypes.byref(cpu_info),
                ctypes.sizeof(cpu_info)
            )
            # Not fatal if CPU rate control fails on some non-enterprise environments

    def assign_process(self, process_handle: int, pid: Optional[int] = None) -> bool:
        """Assigns an unmanaged or newly created Windows process to this Job Object."""
        if not self._handle:
            raise RuntimeError("Cannot assign process: Job Object handle is invalid or closed.")

        hProc = wintypes.HANDLE(process_handle)
        ok = kernel32.AssignProcessToJobObject(self._handle, hProc)
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(f"Failed to assign process to Job Object (Win32 Error: {err})")

        if pid is not None and pid not in self._assigned_pids:
            self._assigned_pids.append(pid)
        return True

    def terminate(self, exit_code: int = 1) -> bool:
        """Atomically terminates the entire process tree inside this Job Object."""
        if not self._handle or not self._is_active:
            return False

        ok = kernel32.TerminateJobObject(self._handle, exit_code)
        self._assigned_pids.clear()
        return bool(ok)

    def get_telemetry(self) -> Dict[str, Any]:
        """Queries kernel for current memory, process count, and CPU time telemetry."""
        if not self._handle or not self._is_active:
            return {
                "active_processes": 0,
                "total_processes": 0,
                "peak_memory_mb": 0.0,
                "user_time_sec": 0.0,
                "kernel_time_sec": 0.0,
                "is_active": False
            }

        # Query Basic Accounting
        acc_info = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
        kernel32.QueryInformationJobObject(
            self._handle,
            JobObjectBasicAccountingInformation,
            ctypes.byref(acc_info),
            ctypes.sizeof(acc_info),
            None
        )

        # Query Extended Limits (contains PeakJobMemoryUsed)
        ext_info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        kernel32.QueryInformationJobObject(
            self._handle,
            JobObjectExtendedLimitInformation,
            ctypes.byref(ext_info),
            ctypes.sizeof(ext_info),
            None
        )

        # Time is in 100-nanosecond units (10^-7 sec)
        user_sec = acc_info.TotalUserTime / 10_000_000.0
        kernel_sec = acc_info.TotalKernelTime / 10_000_000.0
        peak_mb = ext_info.PeakJobMemoryUsed / (1024.0 * 1024.0)

        return {
            "active_processes": acc_info.ActiveProcesses,
            "total_processes": acc_info.TotalProcesses,
            "peak_memory_mb": round(peak_mb, 2),
            "user_time_sec": round(user_sec, 3),
            "kernel_time_sec": round(kernel_sec, 3),
            "is_active": True
        }

    def close(self):
        """Closes the Job Object handle, triggering kill-on-close if configured."""
        if self._handle:
            try:
                kernel32.CloseHandle(self._handle)
            except Exception:
                pass
            self._handle = None
            self._is_active = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()
