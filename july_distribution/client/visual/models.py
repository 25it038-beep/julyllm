"""
HS AI SOLUTIONS — JULY VISUAL ENGINE DATA MODELS
Module: july_distribution.client.visual.models
Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Structured representation of on-demand visual requests inside July & Gravity.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json


@dataclass
class Component:
    id: str
    name: str
    type: str = "node"  # node, block, register, state, layer, neuron, gate
    properties: Dict[str, Any] = field(default_factory=dict)
    subcomponents: List[str] = field(default_factory=list)


@dataclass
class Connection:
    source: str
    target: str
    label: str = ""
    direction: str = "forward"  # forward, bidirectional, feedback, dashed
    style: str = "solid"


@dataclass
class AnimationStep:
    step_number: int
    title: str
    description: str
    state: Dict[str, Any] = field(default_factory=dict)
    highlighted_items: List[str] = field(default_factory=list)


@dataclass
class VisualRequest:
    visualization_type: str  # binary_search, phase_diagram, cpu_architecture, neural_network, electrical_circuit, os_scheduling, math_plot, flowchart, uml, data_chart
    title: str
    explanation: str = ""
    components: List[Dict[str, Any]] = field(default_factory=list)
    connections: List[Dict[str, Any]] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    coordinates: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    animation_steps: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> VisualRequest:
        return cls(
            visualization_type=str(d.get("visualization_type", "flowchart")).lower().strip(),
            title=str(d.get("title", "Visual Representation")),
            explanation=str(d.get("explanation", "")),
            components=list(d.get("components", [])),
            connections=list(d.get("connections", [])),
            labels=dict(d.get("labels", {})),
            coordinates=dict(d.get("coordinates", {})),
            data=dict(d.get("data", {})),
            animation_steps=list(d.get("animation_steps", []))
        )

    @classmethod
    def from_json(cls, raw: str) -> Optional[VisualRequest]:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return cls.from_dict(parsed)
        except Exception:
            pass
        return None
