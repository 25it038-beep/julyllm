"""
HS AI SOLUTIONS — CONTROLLED SELF-IMPROVEMENT & EVOLUTION FRAMEWORK
Module: july_distribution.client.evolution_engine
Founder & Creator: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Family: JULY AI Family

Implements Phase 8 Continuous Self-Improvement:
1. User feedback collection and error logging.
2. Classification of observed failures into taxonomic categories.
3. Verified corrections dataset generation (JSONL).
4. Prompt variant A/B comparison.
5. Recurring weakness analysis and mitigation recommendations.
6. LoRA fine-tuning dataset preparation.
7. Strict separation of:
   - Type A: Memory-based improvement
   - Type B: Reasoning and orchestration improvement
   - Type C: Neural-network weight improvement
   (Never misrepresents A or B as C; preserves foundation model weights).
"""

from __future__ import annotations
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from .config import get_default_july_dir


@dataclass
class FeedbackEntry:
    timestamp: float
    query: str
    response: str
    rating: int  # 1 for positive, -1 for negative
    error_category: Optional[str]  # 'logic_contradiction', 'underdetermined_math', 'powershell_syntax', 'probability_unbounded', 'visual_mismatch', 'hallucination'
    user_comment: Optional[str]
    verified_correction: Optional[str]
    improvement_type_target: str  # 'TYPE_A_MEMORY', 'TYPE_B_ORCHESTRATION', 'TYPE_C_WEIGHTS'


class ContinuousEvolutionEngine:
    """
    Manages controlled self-improvement without unauthorized model weight tampering.
    """

    ERROR_TAXONOMY = [
        "logic_contradiction",
        "underdetermined_math",
        "powershell_syntax",
        "probability_unbounded",
        "visual_mismatch",
        "hallucination",
        "instruction_drift"
    ]

    def __init__(self):
        self.base_dir = get_default_july_dir()
        self.feedback_file = self.base_dir / "user_feedback.jsonl"
        self.corrections_dataset = self.base_dir / "evolution_corrections.jsonl"
        self.lora_training_dir = self.base_dir / "lora_dataset"
        self.lora_training_dir.mkdir(parents=True, exist_ok=True)

    def log_feedback(
        self,
        query: str,
        response: str,
        rating: int,
        error_category: Optional[str] = None,
        user_comment: Optional[str] = None,
        verified_correction: Optional[str] = None,
        improvement_type: str = "TYPE_B_ORCHESTRATION"
    ) -> Dict[str, Any]:
        """Logs user feedback with categorized failure analysis."""
        entry = {
            "timestamp": time.time(),
            "query": query,
            "response": response,
            "rating": rating,
            "error_category": error_category,
            "user_comment": user_comment,
            "verified_correction": verified_correction,
            "improvement_type_target": improvement_type
        }

        with open(self.feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # If verified correction provided, store in gold training dataset
        if verified_correction and verified_correction.strip():
            self.store_verified_correction(query, verified_correction, error_category or "general")

        return {"status": "recorded", "category": error_category, "target": improvement_type}

    def store_verified_correction(self, prompt: str, golden_response: str, category: str):
        """Appends verified correction sample for evaluation and supervised fine-tuning."""
        sample = {
            "instruction": prompt,
            "input": "",
            "output": golden_response,
            "category": category,
            "recorded_at": time.time()
        }
        with open(self.corrections_dataset, "a", encoding="utf-8") as f:
            f.write(json.dumps(sample) + "\n")

    def analyze_recurring_weaknesses(self) -> Dict[str, Any]:
        """Analyzes recorded feedback to identify top failure modes."""
        if not self.feedback_file.exists():
            return {
                "total_feedback": 0,
                "negative_count": 0,
                "category_breakdown": {},
                "recommendation": "No user failure reports logged."
            }

        counts = {cat: 0 for cat in self.ERROR_TAXONOMY}
        total = 0
        neg = 0

        with open(self.feedback_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    total += 1
                    if data.get("rating", 1) < 0:
                        neg += 1
                        cat = data.get("error_category", "other")
                        counts[cat] = counts.get(cat, 0) + 1
                except Exception:
                    continue

        sorted_cats = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top_weakness = sorted_cats[0] if sorted_cats else ("none", 0)

        return {
            "total_feedback": total,
            "negative_count": neg,
            "category_breakdown": dict(sorted_cats),
            "top_recurring_weakness": top_weakness[0],
            "recommendation": (
                f"Prioritize {top_weakness[0]} improvements in Type B Reasoning Orchestration before scheduling Type C LoRA training."
            )
        }

    def export_lora_dataset(self) -> Path:
        """
        Exports collected corrections into standard Alpaca SFT format
        ready for PyTorch / PEFT LoRA training on NVIDIA RTX 3050.
        """
        alpaca_file = self.lora_training_dir / "july_lora_sft_dataset.json"
        samples = []

        if self.corrections_dataset.exists():
            with open(self.corrections_dataset, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            item = json.loads(line)
                            samples.append({
                                "instruction": item["instruction"],
                                "input": item.get("input", ""),
                                "output": item["output"]
                            })
                        except Exception:
                            pass

        with open(alpaca_file, "w", encoding="utf-8") as f:
            json.dump(samples, f, indent=2)

        return alpaca_file
