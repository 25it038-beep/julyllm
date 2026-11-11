"""
HS AI SOLUTIONS — WINDOWS COMPUTER USE & DESKTOP AUTOMATION TOOL
Module: hs_ecosystem.agent.tools.computer_use_tool
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM

Enables desktop automation on Windows using Win32 API:
- Mouse click & movement (SetCursorPos, mouse_event)
- Keyboard input & key combinations
- Window enumeration & focus management (EnumWindows, SetForegroundWindow)
- Screen metrics & resolution inspection
"""

from __future__ import annotations
import sys
import time
import ctypes
from ctypes import wintypes
from typing import Dict, Any, Optional, List
from .base import BaseTool, ToolCategory, PermissionTier, ToolResult


class ComputerUseTool(BaseTool):
    """Controls Windows mouse, keyboard, and window state using native Win32 API."""

    def __init__(self):
        super().__init__(
            name="computer_use",
            description="Controls Windows desktop: mouse cursor, clicks, keystrokes, active window focus, and screen metrics.",
            category=ToolCategory.COMPUTER_USE,
            permission_tier=PermissionTier.PRIVILEGED,
            timeout_seconds=15.0
        )
        self.is_windows = sys.platform == "win32"
        if self.is_windows:
            self.user32 = ctypes.windll.user32

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["mouse_move", "mouse_click", "keyboard_type", "get_screen_size", "get_cursor_pos", "list_windows", "focus_window"],
                    "description": "Desktop operation to perform."
                },
                "x": {"type": "integer", "description": "X coordinate for mouse move/click."},
                "y": {"type": "integer", "description": "Y coordinate for mouse move/click."},
                "text": {"type": "string", "description": "Text to type into focused window."},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                "window_title": {"type": "string", "description": "Target window title substring to focus."}
            },
            "required": ["action"]
        }

    def execute(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        t0 = time.time()
        if not self.is_windows:
            return ToolResult(success=False, output="", error="Computer use is only supported on Windows.", duration_seconds=round(time.time() - t0, 3))

        action = arguments.get("action")

        try:
            if action == "get_screen_size":
                width = self.user32.GetSystemMetrics(0)  # SM_CXSCREEN
                height = self.user32.GetSystemMetrics(1) # SM_CYSCREEN
                return ToolResult(
                    success=True,
                    output={"width": width, "height": height},
                    duration_seconds=round(time.time() - t0, 3)
                )

            elif action == "get_cursor_pos":
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                pt = POINT()
                self.user32.GetCursorPos(ctypes.byref(pt))
                return ToolResult(
                    success=True,
                    output={"x": pt.x, "y": pt.y},
                    duration_seconds=round(time.time() - t0, 3)
                )

            elif action == "mouse_move":
                x = int(arguments.get("x", 0))
                y = int(arguments.get("y", 0))
                self.user32.SetCursorPos(x, y)
                return ToolResult(
                    success=True,
                    output=f"Cursor moved to ({x}, {y})",
                    duration_seconds=round(time.time() - t0, 3)
                )

            elif action == "mouse_click":
                x = arguments.get("x")
                y = arguments.get("y")
                button = arguments.get("button", "left")

                if x is not None and y is not None:
                    self.user32.SetCursorPos(int(x), int(y))
                    time.sleep(0.05)

                # Mouse event flags
                MOUSEEVENTF_LEFTDOWN = 0x0002
                MOUSEEVENTF_LEFTUP = 0x0004
                MOUSEEVENTF_RIGHTDOWN = 0x0008
                MOUSEEVENTF_RIGHTUP = 0x0010

                if button == "left":
                    self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.02)
                    self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                elif button == "right":
                    self.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                    time.sleep(0.02)
                    self.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

                return ToolResult(
                    success=True,
                    output=f"Mouse {button}-click executed.",
                    duration_seconds=round(time.time() - t0, 3)
                )

            elif action == "keyboard_type":
                text = arguments.get("text", "")
                for char in text:
                    vk = ctypes.windll.user32.VkKeyScanW(ord(char))
                    if vk != -1:
                        self.user32.keybd_event(vk & 0xFF, 0, 0, 0)
                        time.sleep(0.01)
                        self.user32.keybd_event(vk & 0xFF, 0, 2, 0)
                    time.sleep(0.01)
                return ToolResult(
                    success=True,
                    output=f"Typed {len(text)} characters.",
                    duration_seconds=round(time.time() - t0, 3)
                )

            elif action == "list_windows":
                windows = []
                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

                def enum_proc(hwnd, lparam):
                    if self.user32.IsWindowVisible(hwnd):
                        length = self.user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            self.user32.GetWindowTextW(hwnd, buff, length + 1)
                            title = buff.value.strip()
                            if title:
                                windows.append({"hwnd": hwnd, "title": title})
                    return True

                self.user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
                return ToolResult(
                    success=True,
                    output=windows[:30],
                    duration_seconds=round(time.time() - t0, 3),
                    metadata={"count": len(windows)}
                )

            elif action == "focus_window":
                title_sub = arguments.get("window_title", "").lower()
                target_hwnd = None

                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

                def enum_find(hwnd, lparam):
                    nonlocal target_hwnd
                    if self.user32.IsWindowVisible(hwnd):
                        length = self.user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            self.user32.GetWindowTextW(hwnd, buff, length + 1)
                            if title_sub in buff.value.lower():
                                target_hwnd = hwnd
                                return False
                    return True

                self.user32.EnumWindows(WNDENUMPROC(enum_find), 0)
                if target_hwnd:
                    self.user32.SetForegroundWindow(target_hwnd)
                    return ToolResult(success=True, output=f"Focused window (HWND: {target_hwnd})", duration_seconds=round(time.time() - t0, 3))
                return ToolResult(success=False, output="", error=f"Window with title containing '{title_sub}' not found.", duration_seconds=round(time.time() - t0, 3))

            return ToolResult(success=False, output="", error=f"Unknown computer use action: {action}", duration_seconds=round(time.time() - t0, 3))

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Computer use failed: {e}", duration_seconds=round(time.time() - t0, 3))
