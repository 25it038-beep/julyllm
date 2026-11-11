---
name: windows-automation
description: Windows desktop automation, process management, window focusing, and system telemetry.
required_tools: ["computer_use", "terminal_exec"]
safety_tier: PRIVILEGED
---

# Windows Desktop Automation Skill

Automates desktop operations and window management on Windows using Win32 API.

## Procedure
1. Enumerate active windows using `computer_use` (action `list_windows`).
2. Focus the target application window using `focus_window`.
3. Dispatch automated keystrokes or mouse clicks as required.
4. Verify execution state and restore normal window layout.
