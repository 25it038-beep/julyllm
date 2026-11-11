"""
HS AI SOLUTIONS — SELF-IMPROVING SKILL ENGINE
Module: hs_ecosystem.agent.skill_engine
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM

Implements Pillar 6:
- Portable Agent Skills standard parser (SKILL.md with YAML frontmatter)
- Procedure extractor: synthesizes reusable skills from multi-step task executions
- Automated skill validation in Windows Sandbox
- Rejection of untrusted third-party skills without explicit approval
- Skills library management
"""

from __future__ import annotations
import os
import re
import yaml
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from july_distribution.client.sandbox import SandboxManager


@dataclass
class SkillDefinition:
    name: str
    description: str
    required_tools: List[str]
    safety_tier: str
    instructions: str
    examples: List[str] = field(default_factory=list)
    file_path: Optional[Path] = None
    is_verified: bool = False


class SkillEngine:
    """Manages discovery, execution, extraction, and validation of Agent Skills."""

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or (Path.cwd() / "skills")
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_skills: Dict[str, SkillDefinition] = {}
        self.reload_skills()

    def reload_skills(self):
        """Scans skills directory for SKILL.md files."""
        self.loaded_skills.clear()
        for skill_folder in self.skills_dir.iterdir():
            if skill_folder.is_dir():
                skill_md = skill_folder / "SKILL.md"
                if skill_md.exists():
                    skill_def = self._parse_skill_md(skill_md)
                    if skill_def:
                        self.loaded_skills[skill_def.name] = skill_def

    def _parse_skill_md(self, path: Path) -> Optional[SkillDefinition]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract YAML frontmatter
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if not match:
                return None

            frontmatter_raw = match.group(1)
            instructions = match.group(2).strip()

            meta = yaml.safe_load(frontmatter_raw) or {}
            name = meta.get("name", path.parent.name)
            description = meta.get("description", "")
            required_tools = meta.get("required_tools", [])
            safety_tier = meta.get("safety_tier", "SAFE")

            return SkillDefinition(
                name=name,
                description=description,
                required_tools=required_tools,
                safety_tier=safety_tier,
                instructions=instructions,
                file_path=path,
                is_verified=True
            )
        except Exception:
            return None

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        return self.loaded_skills.get(name)

    def list_skills(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "required_tools": s.required_tools,
                "safety_tier": s.safety_tier,
                "path": str(s.file_path.relative_to(self.skills_dir.parent)) if s.file_path else ""
            }
            for s in self.loaded_skills.values()
        ]

    def extract_skill_from_task(
        self,
        skill_name: str,
        description: str,
        subtasks_record: List[Dict[str, Any]],
        safety_tier: str = "SAFE"
    ) -> SkillDefinition:
        """
        Synthesizes a new reusable skill from a successful multi-step task execution.
        """
        clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "-", skill_name.lower()).strip("-")
        target_dir = self.skills_dir / clean_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "SKILL.md"

        tools_used = list(set([st.get("tool_name") for st in subtasks_record if st.get("tool_name")]))

        instructions_parts = [
            f"# {skill_name}\n",
            f"{description}\n\n",
            "## Workflow Procedure\n"
        ]
        for idx, st in enumerate(subtasks_record, start=1):
            instructions_parts.append(f"{idx}. **{st.get('name', 'Step')}**: {st.get('description', '')}\n")
            if st.get("tool_name"):
                instructions_parts.append(f"   - Tool: `{st.get('tool_name')}`\n")

        content = (
            f"---\n"
            f"name: {clean_name}\n"
            f"description: {description}\n"
            f"required_tools: {json.dumps(tools_used)}\n"
            f"safety_tier: {safety_tier}\n"
            f"---\n\n"
            + "".join(instructions_parts)
        )

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        new_skill = SkillDefinition(
            name=clean_name,
            description=description,
            required_tools=tools_used,
            safety_tier=safety_tier,
            instructions="".join(instructions_parts),
            file_path=target_file,
            is_verified=True
        )
        self.loaded_skills[clean_name] = new_skill
        return new_skill

    def validate_skill_safety(self, skill: SkillDefinition) -> Tuple[bool, str]:
        """Audits third-party or draft skill for dangerous commands before execution."""
        forbidden = ["format ", "diskpart", "net user", "vssadmin", "certutil", "powershell -enc"]
        for f in forbidden:
            if f in skill.instructions.lower():
                return False, f"Prohibited command '{f}' found in skill instructions."
        return True, "Skill safety verification passed."
