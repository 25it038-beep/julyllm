"""
HS AI SOLUTIONS — CPU & SYSTEM ARCHITECTURE RENDERER
Module: july_distribution.client.visual.renderers.architecture
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders detailed, technically accurate CPU architectures and OS resource allocation / deadlock diagrams directly in terminal.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich import box

from ..models import VisualRequest


class ArchitectureRenderer:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, req: VisualRequest):
        title = req.title.lower()
        sub = req.data.get("subtype", "").lower()

        if "deadlock" in title or "deadlock" in sub or "resource" in title:
            self.render_deadlock_diagram(req)
        elif "os" in title and "kernel" in title:
            self.render_os_kernel_diagram(req)
        else:
            self.render_cpu_architecture(req)

    def render_cpu_architecture(self, req: VisualRequest):
        """
        Renders a detailed Von Neumann / Modern Superscalar CPU Architecture:
        - Control Unit (CU) & Instruction Decoder
        - Arithmetic Logic Unit (ALU) & Floating Point Unit (FPU)
        - Registers: Program Counter (PC), Instruction Reg (IR), Memory Address Reg (MAR), Memory Data Reg (MDR), Accumulator (ACC)
        - Cache Hierarchy: L1 Instruction/Data Cache, L2 Unified Cache, L3 Shared Cache
        - System Bus System: Control Bus, Address Bus, Data Bus
        - Primary Memory (DRAM RAM) & Secondary Storage
        """
        # 1. Registers Block
        reg_table = Table(box=box.SIMPLE_HEAD, title="[bold cyan]REGISTERS FILE[/]", border_style="cyan")
        reg_table.add_column("Register", style="bold yellow")
        reg_table.add_column("Function", style="white")
        reg_table.add_row("PC (Program Counter)", "Points to next instruction memory address")
        reg_table.add_row("IR (Instruction Reg)", "Holds fetched instruction for opcode decoding")
        reg_table.add_row("MAR (Memory Address)", "Holds RAM address for Read/Write operation")
        reg_table.add_row("MDR (Memory Data)", "Data buffer to/from memory bus")
        reg_table.add_row("ACC (Accumulator)", "Stores immediate output from ALU operations")
        reg_table.add_row("R0 - R15 (GPRs)", "Fast working registers for operands")

        # 2. Control Unit & ALU
        cu_panel = Panel(
            "[bold white]• Instruction Decoder & Sequencer\n"
            "• Branch Target Predictor\n"
            "• Timing & Control Signal Generator\n"
            "• Clock Generator (Cycle Timing)[/]",
            title="[bold yellow]CONTROL UNIT (CU)[/]",
            border_style="yellow",
            box=box.ROUNDED
        )

        alu_panel = Panel(
            "[bold white]• 64-bit Integer ALU (Add/Sub/Logic/Shift)\n"
            "• FPU (IEEE 754 Floating Point Unit)\n"
            "• Status Register / Flags (Z, C, N, V)\n"
            "• SIMD Vector Math Engine (AVX/NEON)[/]",
            title="[bold green]ARITHMETIC LOGIC UNIT (ALU)[/]",
            border_style="green",
            box=box.ROUNDED
        )

        core_columns = Columns([cu_panel, alu_panel], expand=True)

        # 3. Cache & Memory Hierarchy
        cache_table = Table(box=box.ROUNDED, border_style="magenta", expand=True)
        cache_table.add_column("Level", style="bold magenta", width=14)
        cache_table.add_column("Capacity / Latency", style="yellow", width=22)
        cache_table.add_column("Placement & Characteristics", style="white")
        cache_table.add_row("L1 Cache (I/D)", "64 KB • 1 ns (~4 cycles)", "Split L1I (Code) and L1D (Data) per core")
        cache_table.add_row("L2 Cache", "512 KB - 1 MB • 3-4 ns", "Unified non-inclusive per-core cache")
        cache_table.add_row("L3 Cache", "16 MB - 64 MB • 10-15 ns", "Shared across all CPU compute cores")
        cache_table.add_row("Main Memory (RAM)", "16 GB - 64 GB • 60-80 ns", "DDR5 Multi-channel synchronous dynamic RAM")

        # 4. Bus Diagram ASCII Art
        bus_art = """
   ┌────────────────────────────────────────────────────────────────────────┐
   │ 🔴 CONTROL BUS  (R/W Signals, Clock, Interrupts, Ready Handshakes)      │
   ├────────────────────────────────────────────────────────────────────────┤
   │ 🟡 ADDRESS BUS  (Unidirectional 64-bit Memory Address Pointer)          │
   ├────────────────────────────────────────────────────────────────────────┤
   │ 🟢 DATA BUS     (Bidirectional High-Speed Data / Instruction Bus)      │
   └────────────────────────────────────────────────────────────────────────┘
                       ▲                              ▲
                       │                              │
          ┌────────────┴────────────┐    ┌────────────┴────────────┐
          │     I/O CONTROLLER      │    │    DDR5 SYSTEM RAM      │
          │ PCIe 5.0, NVMe, USB4    │    │ Channels A/B, Low-CAS   │
          └─────────────────────────┘    └─────────────────────────┘
        """

        self.console.print(Panel(
            "[bold white]VON NEUMANN & MODERN HARVARD SUPERSCALAR CPU ARCHITECTURE[/]\n"
            "[dim]Synchronous Clocked Fetch-Decode-Execute Pipeline[/]",
            title="[bold green]🖥️ CPU INTERNAL ARCHITECTURE[/]",
            border_style="bright_blue"
        ))

        self.console.print(core_columns)
        self.console.print(reg_table)
        self.console.print(Panel(cache_table, title="[bold magenta]CACHE HIERARCHY & MEMORY SUBSYSTEM[/]", border_style="magenta"))
        self.console.print(Panel(bus_art, title="[bold yellow]SYSTEM BUS & INTERCONNECT[/]", border_style="yellow"))

        if req.explanation:
            self.console.print(Panel(f"[bold white]{req.explanation}[/]", title="[bold cyan]Architectural Analysis[/]", border_style="cyan"))

    def render_deadlock_diagram(self, req: VisualRequest):
        """Renders OS Resource Allocation Graph and Deadlock cycle."""
        deadlock_art = """
        [bold red]⚠️ OS DEADLOCK: CIRCULAR WAIT IN RESOURCE ALLOCATION GRAPH (RAG)[/]

            ┌────────────────┐                    ┌────────────────┐
            │  [bold green]PROCESS (P1)[/]   │ ─── Request ────▶  │ [bold yellow]RESOURCE (R1)[/]  │
            │  Thread Alpha  │                    │ Scanner Unit   │
            └───────┬────────┘                    └────────┬───────┘
                    ▲                                      │
                    │ Hold                                 │ Hold
                    │                                      ▼
            ┌───────┴────────┐                    ┌────────────────┐
            │ [bold yellow]RESOURCE (R2)[/]  │ ◀─── Request ──── │  [bold green]PROCESS (P2)[/]   │
            │ Disk Drive     │                    │ Thread Beta    │
            └────────────────┘                    └────────────────┘

        [bold red]DEADLOCK CONDITIONS SATISFIED (COFFMAN CONDITIONS):[/]
        1. [yellow]Mutual Exclusion:[/] Resources R1 and R2 cannot be shared simultaneously.
        2. [yellow]Hold and Wait:[/] P1 holds R2 and waits for R1; P2 holds R1 and waits for R2.
        3. [yellow]No Preemption:[/] Neither resource can be forcefully taken away.
        4. [yellow]Circular Wait:[/] Closed loop dependency cycle: P1 ──▶ R1 ──▶ P2 ──▶ R2 ──▶ P1.
        """
        self.console.print(Panel(deadlock_art, title="[bold red]🛑 OS RESOURCE ALLOCATION & DEADLOCK GRAPH[/]", border_style="red"))

    def render_os_kernel_diagram(self, req: VisualRequest):
        """Renders OS User vs Kernel space architecture."""
        os_art = """
    ┌────────────────────────────────────────────────────────────────────────┐
    │ [bold cyan]USER SPACE (Ring 3 - Unprivileged)[/]                                  │
    │  [green]User Applications[/]  │  [green]System Daemons[/]  │  [green]CLI Shell[/]  │  [green]Language Runtimes[/]  │
    ├────────────────────────────────────────────────────────────────────────┤
    │ [bold yellow]SYSTEM CALL INTERFACE (POSIX / Win32 syscall / sysenter / int 0x80)[/]  │
    ├────────────────────────────────────────────────────────────────────────┤
    │ [bold magenta]KERNEL SPACE (Ring 0 - Privileged Monolithic / Microkernel)[/]            │
    │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
    │  │ [bold white]Process Scheduler[/] │  │ [bold white]Virtual Memory[/]    │  │ [bold white]VFS / Filesystem[/] │      │
    │  │ CFS / Round Robin│  │ Paging & TLB     │  │ Ext4 / NTFS      │      │
    │  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
    │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
    │  │ [bold white]IPC & Sockets[/]     │  │ [bold white]Device Drivers[/]    │  │ [bold white]Security / ACLs[/]  │      │
    │  │ Pipes, Shared Mem│  │ Network, Disk,GPU│  │ Seccomp, LSM     │      │
    │  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
    ├────────────────────────────────────────────────────────────────────────┤
    │ [bold blue]HARDWARE ABSTRACTION LAYER (HAL) & BARE-METAL SILICON[/]                  │
    └────────────────────────────────────────────────────────────────────────┘
        """
        self.console.print(Panel(os_art, title="[bold blue]OPERATING SYSTEM KERNEL & MEMORY ISOLATION[/]", border_style="bright_blue"))
