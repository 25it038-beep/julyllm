"""
HS AI SOLUTIONS — CPU & SYSTEM ARCHITECTURE RENDERER (HIGH-CLARITY)
Module: july_distribution.client.visual.renderers.architecture
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Renders crisp, high-clarity CPU microarchitectures and OS deadlock graphs fitted to terminal width.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
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
        Renders a crystal-clear Von Neumann & Harvard CPU microarchitecture
        guaranteed to never wrap on standard 79-column terminals.
        """
        header = Panel(
            "[bold white]VON NEUMANN & MODERN SUPERSCALAR CPU ARCHITECTURE[/]\n"
            "[dim]Pipelined Fetch-Decode-Execute Microarchitecture & Bus Interconnect[/]",
            title="[bold green]🖥️ CPU INTERNAL ARCHITECTURE[/]",
            border_style="bright_blue",
            expand=False
        )
        self.console.print(header)

        cpu_map = (
            " ┌──────────────────── [bold yellow]CPU CORE SUBSYSTEM[/] ────────────────────┐\n"
            " │                                                               │\n"
            " │  ┌─────────────────────┐             ┌─────────────────────┐  │\n"
            " │  │ [bold yellow]CONTROL UNIT (CU)[/]   │             │ [bold green]ARITHMETIC UNIT[/]     │  │\n"
            " │  │ • Opcode Decoder    │             │ • 64-bit Integer ALU│  │\n"
            " │  │ • Branch Predictor  │ ──Control──▶│ • IEEE 754 FPU Float│  │\n"
            " │  │ • Clock / Sequencer │             │ • SIMD Vector Math  │  │\n"
            " │  └─────────────────────┘             └─────────────────────┘  │\n"
            " │                             ▲                                 │\n"
            " │                             │ Operands & Results              │\n"
            " │                             ▼                                 │\n"
            " │  ┌─────────────────────────────────────────────────────────┐  │\n"
            " │  │ [bold cyan]HIGH-SPEED REGISTERS:[/] PC • IR • MAR • MDR • ACC • R0..R15 │  │\n"
            " │  └─────────────────────────────────────────────────────────┘  │\n"
            " └──────────────────────────────┬────────────────────────────────┘\n"
            "                                │ [cyan]L1/L2 Interconnect Bus[/]\n"
            "                                ▼\n"
            " ┌───────────────────────────────────────────────────────────────┐\n"
            " │ [bold magenta]CACHE HIERARCHY:[/] L1 Inst/Data (64KB) ──▶ L2 (1MB) ──▶ L3 (32MB)   │\n"
            " └──────────────────────────────┬────────────────────────────────┘\n"
            "                                │ [yellow]Memory Bus Interconnect[/]\n"
            "                                ▼\n"
            " ┌───────────────────────────────────────────────────────────────┐\n"
            " │ 🔴 [bold red]CONTROL BUS[/]    🟡 [bold yellow]ADDRESS BUS[/]    🟢 [bold green]DATA BUS (64-bit / Bidirectional)[/]│\n"
            " └──────────────────────────────┬────────────────────────────────┘\n"
            "                                │ [blue]DDR5 Memory Channels[/]\n"
            "                                ▼\n"
            " ┌───────────────────────────────────────────────────────────────┐\n"
            " │ [bold blue]PRIMARY SYSTEM MEMORY:[/] High-Speed Low-Latency DDR5 SDRAM (RAM) │\n"
            " └───────────────────────────────────────────────────────────────┘"
        )
        self.console.print(Panel(cpu_map, title="[bold cyan]MICROPROCESSOR DATA PATH & SUBSYSTEM MAP[/]", border_style="cyan", expand=False))

        # Register Specifications Table
        reg_table = Table(box=box.ROUNDED, border_style="yellow", show_header=True)
        reg_table.add_column("Register", style="bold yellow", width=16)
        reg_table.add_column("Full Name", style="cyan", width=22)
        reg_table.add_column("Operational Function", style="white")

        reg_table.add_row("PC", "Program Counter", "Holds the memory address of the next instruction")
        reg_table.add_row("IR", "Instruction Register", "Holds current opcode being decoded by the CU")
        reg_table.add_row("MAR", "Memory Address Reg.", "Specifies RAM address targeted for Read or Write")
        reg_table.add_row("MDR", "Memory Data Reg.", "Temporary buffer between CPU registers and Data Bus")
        reg_table.add_row("ACC", "Accumulator", "Buffers intermediate outputs of arithmetic/logic ops")
        reg_table.add_row("GPRs", "R0 - R15", "General-purpose 64-bit working registers for data")

        self.console.print(reg_table)

    def render_deadlock_diagram(self, req: VisualRequest):
        """Renders OS Resource Allocation Graph and Deadlock cycle."""
        deadlock_art = (
            "   [bold red]CIRCULAR WAIT DEPENDENCY IN RESOURCE ALLOCATION GRAPH (RAG)[/]\n\n"
            "       ┌────────────────┐                  ┌────────────────┐\n"
            "       │  [bold green]PROCESS (P1)[/]   │ ─── Request ───▶ │ [bold yellow]RESOURCE (R1)[/]  │\n"
            "       │  Thread Alpha  │                  │ Scanner Device │\n"
            "       └───────┬────────┘                  └────────┬───────┘\n"
            "               ▲                                    │\n"
            "               │ Hold                               │ Hold\n"
            "               │                                    ▼\n"
            "       ┌───────┴────────┐                  ┌────────────────┐\n"
            "       │ [bold yellow]RESOURCE (R2)[/]  │ ◀─── Request ─── │  [bold green]PROCESS (P2)[/]   │\n"
            "       │ Disk Controller│                  │ Thread Beta    │\n"
            "       └────────────────┘                  └────────────────┘\n\n"
            "   [bold red]DEADLOCK STATE VERIFIED (COFFMAN CONDITIONS):[/]\n"
            "   • [yellow]Mutual Exclusion:[/] Resources R1 and R2 cannot be shared.\n"
            "   • [yellow]Hold and Wait:[/] P1 holds R2 and waits for R1; P2 holds R1 and waits for R2.\n"
            "   • [yellow]No Preemption:[/] Neither resource can be preempted.\n"
            "   • [yellow]Circular Wait:[/] P1 ──▶ R1 ──▶ P2 ──▶ R2 ──▶ P1 (Permanent Starvation)"
        )
        self.console.print(Panel(deadlock_art, title="[bold red]🛑 OS RESOURCE ALLOCATION & DEADLOCK GRAPH[/]", border_style="red", expand=False))

    def render_os_kernel_diagram(self, req: VisualRequest):
        """Renders OS User vs Kernel space architecture."""
        os_art = (
            " ┌───────────────────────────────────────────────────────────────┐\n"
            " │ [bold cyan]USER SPACE (Ring 3 - Unprivileged)[/]                            │\n"
            " │  User Applications • CLI Shell • Daemons • Python Runtimes    │\n"
            " ├───────────────────────────────────────────────────────────────┤\n"
            " │ [bold yellow]SYSTEM CALL INTERFACE (POSIX / Win32 syscall / sysenter)[/]      │\n"
            " ├───────────────────────────────────────────────────────────────┤\n"
            " │ [bold magenta]KERNEL SPACE (Ring 0 - Privileged Mode)[/]                       │\n"
            " │  • Process Scheduler (CFS/Round-Robin)  • Virtual Memory      │\n"
            " │  • Virtual File System (VFS/NTFS)       • Device Drivers      │\n"
            " │  • Inter-Process Comms (IPC/Sockets)    • Memory Management   │\n"
            " ├───────────────────────────────────────────────────────────────┤\n"
            " │ [bold blue]HARDWARE ABSTRACTION LAYER (HAL) & SILICON (CPU/RAM/GPU)[/]        │\n"
            " └───────────────────────────────────────────────────────────────┘"
        )
        self.console.print(Panel(os_art, title="[bold blue]OPERATING SYSTEM KERNEL ARCHITECTURE[/]", border_style="bright_blue", expand=False))
