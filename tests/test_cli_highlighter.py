"""
Unit test for CLI Model Thinking and Result Stream Highlighter.
"""
import unittest
import time
import re

# We will test the ThinkingResultStreamFilter class logic here
class ThinkingResultStreamFilter:
    """
    Differentiates model thinking and result by highlighting in CLI.
    Handles streaming tokens split across chunk boundaries.
    """
    STATE_INITIAL = "INITIAL"
    STATE_THINKING = "THINKING"
    STATE_RESULT = "RESULT"

    OPEN_TAGS = ["<think>", "<thought>", "<reasoning>", "[thinking]", "[think]"]
    OPEN_TEXT_MARKERS = [
        "thinking process:", "thought:", "thoughts:", "reasoning:",
        "### thinking", "## thinking", "### reasoning", "## reasoning",
        "### thought process", "## thought process"
    ]
    CLOSE_REGEX = re.compile(
        r"(?:</think>|</thought>|</reasoning>|\[/thinking\]|\[/think\]|"
        r"(?:^|\n)\s*(?:###?\s*(?:answer|result|solution|response|conclusion)|final answer:|answer:|result:))",
        re.IGNORECASE
    )

    def __init__(self, model_name: str = "JULY", badge_color: str = "\033[96m", thinking_mode: str = "expanded"):
        self.model_name = model_name
        self.badge_color = badge_color
        self.thinking_mode = thinking_mode  # "expanded", "collapsed", "hidden"
        self.state = self.STATE_INITIAL
        self.buffer = ""
        self.think_start_time = 0.0
        self.has_thought = False
        self.in_visual = False
        self.result_header_printed = False

    def process(self, token: str) -> str:
        self.buffer += token
        output = []

        while self.buffer:
            if self.state == self.STATE_INITIAL:
                # Check if buffer starts with whitespace
                stripped = self.buffer.lstrip()
                leading_ws = self.buffer[:len(self.buffer) - len(stripped)]

                if not stripped:
                    # Only whitespace so far, wait for actual content
                    break

                low_stripped = stripped.lower()

                # Check if stripped matches start of any opening tag
                matched_open = None
                for tag in self.OPEN_TAGS:
                    if low_stripped.startswith(tag):
                        matched_open = tag
                        break

                if matched_open:
                    self.state = self.STATE_THINKING
                    self.has_thought = True
                    self.think_start_time = time.time()
                    tag_len = len(matched_open)
                    self.buffer = stripped[tag_len:]
                    if self.buffer.startswith("\n"):
                        self.buffer = self.buffer[1:]
                    
                    if self.thinking_mode == "expanded":
                        header = (
                            f"\n  \033[38;5;244m╭─ 🧠 Thinking Process ──────────────────────────────────────────\033[0m\n"
                            f"  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m"
                        )
                        output.append(header)
                    continue

                # Check if stripped could potentially be part of an open tag
                potential_match = False
                for tag in self.OPEN_TAGS:
                    if tag.startswith(low_stripped) or (low_stripped.startswith("<") and len(low_stripped) < 12):
                        potential_match = True
                        break

                if potential_match and len(stripped) < 15:
                    # Need more tokens to be certain
                    break

                # Check for textual thinking markers like "Thinking Process:" or "### Thinking"
                matched_text_marker = None
                for marker in self.OPEN_TEXT_MARKERS:
                    if low_stripped.startswith(marker):
                        matched_text_marker = marker
                        break

                if matched_text_marker:
                    self.state = self.STATE_THINKING
                    self.has_thought = True
                    self.think_start_time = time.time()
                    marker_len = len(matched_text_marker)
                    self.buffer = stripped[marker_len:]
                    if self.buffer.startswith("\n"):
                        self.buffer = self.buffer[1:]
                    if self.thinking_mode == "expanded":
                        header = (
                            f"\n  \033[38;5;244m╭─ 🧠 Thinking Process ──────────────────────────────────────────\033[0m\n"
                            f"  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m"
                        )
                        output.append(header)
                    continue

                # Not an opening tag, directly transition to RESULT
                self.state = self.STATE_RESULT
                # If there's leading whitespace or text, let RESULT state process it
                continue

            elif self.state == self.STATE_THINKING:
                # Look for closing tag or result transition marker via regex
                m = self.CLOSE_REGEX.search(self.buffer)
                if m:
                    close_idx = m.start()
                    tag_len = len(m.group(0))

                    # Text before closing marker belongs to thinking
                    thinking_chunk = self.buffer[:close_idx]
                    if self.thinking_mode == "expanded":
                        formatted_chunk = thinking_chunk.replace("\n", "\n  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m")
                        output.append(formatted_chunk)

                    # Consume closing tag/marker
                    self.buffer = self.buffer[close_idx + tag_len:]
                    if self.buffer.startswith("\n"):
                        self.buffer = self.buffer.lstrip("\r\n")

                    dur = max(0.1, time.time() - self.think_start_time)
                    if self.thinking_mode == "expanded":
                        footer = (
                            f"\033[0m\n  \033[38;5;244m╰───────────────────────────────────────────\033[0m "
                            f"\033[90m(thought for {dur:.1f}s)\033[0m\n\n"
                            f"  {self.badge_color}\033[1m✦ Result:\033[0m\n  \033[0m"
                        )
                    elif self.thinking_mode == "collapsed":
                        footer = (
                            f"\n  \033[90m[🧠 Thought for {dur:.1f}s]\033[0m\n\n"
                            f"  {self.badge_color}\033[1m✦ Result:\033[0m\n  \033[0m"
                        )
                    else:  # hidden
                        footer = f"\n  {self.badge_color}\033[1m✦ Result:\033[0m\n  \033[0m"

                    output.append(footer)
                    self.result_header_printed = True
                    self.state = self.STATE_RESULT
                    continue
                else:
                    # Check if buffer ends with a partial closing tag
                    partial_len = 0
                    low = self.buffer.lower()
                    for tag in ["</think>", "</thought>", "</reasoning>", "[/thinking]"]:
                        for pl in range(1, len(tag)):
                            if low.endswith(tag[:pl]):
                                if pl > partial_len:
                                    partial_len = pl

                    if partial_len > 0:
                        to_emit = self.buffer[:-partial_len]
                        self.buffer = self.buffer[-partial_len:]
                    else:
                        to_emit = self.buffer
                        self.buffer = ""

                    if to_emit and self.thinking_mode == "expanded":
                        formatted = to_emit.replace("\n", "\n  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m")
                        output.append(formatted)
                    break

            elif self.state == self.STATE_RESULT:
                # Handle visual filtering or detection of open thinking tags
                if not self.in_visual:
                    low = self.buffer.lower()

                    # Check for mid-stream thinking tag
                    matched_open = None
                    open_idx = -1
                    for tag in self.OPEN_TAGS:
                        idx = low.find(tag)
                        if idx != -1:
                            if open_idx == -1 or idx < open_idx:
                                open_idx = idx
                                matched_open = tag

                    if matched_open is not None:
                        # Flush text before the open tag
                        pre_text = self.buffer[:open_idx]
                        if pre_text:
                            output.append(pre_text)
                        
                        tag_len = len(matched_open)
                        self.buffer = self.buffer[open_idx + tag_len:]
                        if self.buffer.startswith("\n"):
                            self.buffer = self.buffer[1:]
                        
                        self.state = self.STATE_THINKING
                        self.has_thought = True
                        self.think_start_time = time.time()
                        if self.thinking_mode == "expanded":
                            header = (
                                f"\n  \033[38;5;244m╭─ 🧠 Thinking Process ──────────────────────────────────────────\033[0m\n"
                                f"  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m"
                            )
                            output.append(header)
                        continue

                    if "<visual" in low:
                        idx = low.find("<visual")
                        pre_vis = self.buffer[:idx]
                        self.buffer = self.buffer[idx:]
                        self.in_visual = True
                        output.append(pre_vis)
                        continue

                    # Check if buffer ends with a partial tag of OPEN_TAGS or <visual
                    partial_len = 0
                    for tag in self.OPEN_TAGS + ["<visual"]:
                        for pl in range(1, len(tag)):
                            if low.endswith(tag[:pl]):
                                if pl > partial_len:
                                    partial_len = pl

                    if partial_len > 0:
                        to_emit = self.buffer[:-partial_len]
                        self.buffer = self.buffer[-partial_len:]
                        if to_emit:
                            output.append(to_emit)
                        break
                    else:
                        output.append(self.buffer)
                        self.buffer = ""
                        break
                else:
                    low = self.buffer.lower()
                    if "</visual>" in low:
                        idx = low.find("</visual>")
                        self.buffer = self.buffer[idx + len("</visual>"):]
                        self.in_visual = False
                        continue
                    elif ">" in self.buffer and "}" in self.buffer:
                        idx = self.buffer.find(">")
                        self.buffer = self.buffer[idx + 1:]
                        self.in_visual = False
                        continue
                    break

        return "".join(output)

    def flush(self) -> str:
        output = []
        if self.state == self.STATE_THINKING:
            if self.buffer and self.thinking_mode == "expanded":
                formatted = self.buffer.replace("\n", "\n  \033[38;5;240m│\033[0m \033[38;5;245m\033[3m")
                output.append(formatted)
            dur = max(0.1, time.time() - self.think_start_time)
            if self.thinking_mode == "expanded":
                footer = (
                    f"\033[0m\n  \033[38;5;244m╰───────────────────────────────────────────\033[0m "
                    f"\033[90m(thought for {dur:.1f}s)\033[0m\n"
                )
            elif self.thinking_mode == "collapsed":
                footer = f"\n  \033[90m[🧠 Thought for {dur:.1f}s]\033[0m\n"
            else:
                footer = ""
            output.append(footer)
            self.buffer = ""
        elif self.state == self.STATE_INITIAL:
            output.append(self.buffer)
            self.buffer = ""
        elif self.state == self.STATE_RESULT:
            if not self.in_visual:
                output.append(self.buffer)
            self.buffer = ""
        return "".join(output)


class TestHighlighter(unittest.TestCase):
    def test_thinking_with_tags(self):
        f = ThinkingResultStreamFilter(model_name="JULY")
        tokens = ["<th", "ink>\n", "Step 1: let's analyze the input.\n", "Step 2: compute 2+2=4.\n", "</think>\n", "The answer is 4."]
        res = ""
        for t in tokens:
            res += f.process(t)
        res += f.flush()
        print("\n--- TEST THINKING WITH TAGS OUTPUT ---")
        print(res)
        self.assertIn("Thinking Process", res)
        self.assertIn("Step 1: let's analyze", res)
        self.assertIn("Result:", res)
        self.assertIn("The answer is 4.", res)
        self.assertNotIn("<think>", res)
        self.assertNotIn("</think>", res)

    def test_direct_answer_no_thinking(self):
        f = ThinkingResultStreamFilter(model_name="JULY")
        tokens = ["Hello! ", "I am ", "JULY LLM. ", "How can I help you?"]
        res = ""
        for t in tokens:
            res += f.process(t)
        res += f.flush()
        print("\n--- TEST NO THINKING OUTPUT ---")
        print(res)
        self.assertNotIn("Thinking Process", res)
        self.assertIn("Hello! I am JULY LLM. How can I help you?", res)


    def test_thinking_with_leading_whitespace(self):
        f = ThinkingResultStreamFilter(model_name="JULY")
        tokens = ["  \n", "<think>", "\nSolving step by step:\n- Alpha\n- Beta\n", "</think>\n\n", "Final solution is X."]
        res = ""
        for t in tokens:
            res += f.process(t)
        res += f.flush()
        print("\n--- TEST LEADING WS OUTPUT ---")
        print(res)
        self.assertIn("Thinking Process", res)
        self.assertIn("- Alpha", res)
        self.assertIn("Final solution is X.", res)

    def test_visual_filtering_in_result(self):
        f = ThinkingResultStreamFilter(model_name="JULY")
        tokens = [
            "<think>Plan diagram</think>",
            "Here is the chart:\n<visual type='mermaid'>graph TD; A-->B;</visual>\nEnjoy the chart!"
        ]
        res = ""
        for t in tokens:
            res += f.process(t)
        res += f.flush()
        print("\n--- TEST VISUAL IN RESULT OUTPUT ---")
        print(res)
        self.assertNotIn("<visual", res)
        self.assertNotIn("graph TD", res)
        self.assertIn("Here is the chart:", res)
        self.assertIn("Enjoy the chart!", res)

    def test_thought_textual_marker(self):
        f = ThinkingResultStreamFilter(model_name="JULY")
        tokens = ["Thought: The user wants to invert a matrix.\nLet me compute the determinant.\nFinal Answer: The inverse exists."]
        res = ""
        for t in tokens:
            res += f.process(t)
        res += f.flush()
        print("\n--- TEST TEXTUAL MARKER OUTPUT ---")
        print(res)
        self.assertIn("Thinking Process", res)
        self.assertIn("compute the determinant", res)
        self.assertIn("The inverse exists.", res)


    def test_thinking_after_intro_text(self):
        f = ThinkingResultStreamFilter(model_name="JULY")
        tokens = ["Sure, I can help! ", "<th", "ink>\n", "Step 1: check user question.\n", "</think>\n", "Here is the solution: 42."]
        res = ""
        for t in tokens:
            res += f.process(t)
        res += f.flush()
        print("\n--- TEST THINKING AFTER INTRO OUTPUT ---")
        print(res)
        self.assertIn("Sure, I can help!", res)
        self.assertIn("Thinking Process", res)
        self.assertIn("Step 1: check user question.", res)
        self.assertIn("Result:", res)
        self.assertIn("Here is the solution: 42.", res)
        self.assertNotIn("<think>", res)
        self.assertNotIn("</think>", res)


    def test_markdown_headers_thinking(self):
        f = ThinkingResultStreamFilter(model_name="JULY")
        tokens = [
            "### Thinking\n",
            "First, I will derive the equation.\n",
            "Second, evaluate at t=0.\n\n",
            "### Result\n",
            "The final velocity is 0 m/s."
        ]
        res = ""
        for t in tokens:
            res += f.process(t)
        res += f.flush()
        print("\n--- TEST MARKDOWN HEADERS OUTPUT ---")
        print(res)
        self.assertIn("Thinking Process", res)
        self.assertIn("First, I will derive the equation.", res)
        self.assertIn("The final velocity is 0 m/s.", res)


    def test_thinking_collapsed_mode(self):
        f = ThinkingResultStreamFilter(model_name="JULY", thinking_mode="collapsed")
        tokens = ["<think>Internal deep calculation</think>Result is 100."]
        res = ""
        for t in tokens:
            res += f.process(t)
        res += f.flush()
        self.assertNotIn("Internal deep calculation", res)
        self.assertIn("[🧠 Thought for", res)
        self.assertIn("Result is 100.", res)

    def test_thinking_hidden_mode(self):
        f = ThinkingResultStreamFilter(model_name="JULY", thinking_mode="hidden")
        tokens = ["<think>Internal deep calculation</think>Result is 100."]
        res = ""
        for t in tokens:
            res += f.process(t)
        res += f.flush()
        self.assertNotIn("Internal deep calculation", res)
        self.assertNotIn("[🧠 Thought for", res)
        self.assertIn("Result is 100.", res)


if __name__ == "__main__":
    unittest.main()
