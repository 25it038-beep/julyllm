"""
HS AI SOLUTIONS — MODAL CLOUD INFRASTRUCTURE CONFIGURATION
Module: modal_config.py
Founder & Chief Architect: Harshan Seliyan
Product: JULY LLM CLOUD & GRAVITY CLOUD
GPU Infrastructure: Modal Serverless GPU Platform
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List


# ---------------------------------------------------------------------------
# Base Constants & Paths
# ---------------------------------------------------------------------------
PROJECT_NAME = "JULY LLM CLOUD INFRASTRUCTURE"
ORGANIZATION = "HS AI SOLUTIONS"
FOUNDER = "Harshan Seliyan"
DEFAULT_VOLUME_NAME = "july-models-volume"
DEFAULT_VOLUME_MOUNT_PATH = "/vol/models"
LOCAL_MODELS_DIR = Path(__file__).resolve().parent / "models"

# Cloudflare R2 Model Artifact Storage
DEFAULT_R2_ENDPOINT = "https://21e5f9f23e1d60cb56bf1200e89255f3.r2.cloudflarestorage.com/"
DEFAULT_R2_BUCKET = "july"


@dataclass
class ModelSpec:
    model_id: str
    display_name: str
    file_name: str
    r2_key: str
    sha256: str
    size_bytes: int
    gpu_type: str
    context_length: int
    n_gpu_layers: int
    default_temperature: float
    default_top_p: float
    system_prompt: str
    description: str
    aliases: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Model Registry Specifications (July Lite, Gravity, July Vision, July Code)
# ---------------------------------------------------------------------------
MODEL_SPECS: Dict[str, ModelSpec] = {
    "july-lite": ModelSpec(
        model_id="july-lite",
        display_name="JULY LLM Lite (Foundation)",
        file_name="july-final.gguf",
        r2_key="july-final.gguf",
        sha256="f15752352dc3297ad50e6baeccbae400ca1a9338c4e3ca8475757af587323bd4",
        size_bytes=2019377888,
        gpu_type=os.getenv("JULY_LITE_GPU", "T4"),
        context_length=int(os.getenv("JULY_LITE_CONTEXT", "4096")),
        n_gpu_layers=int(os.getenv("JULY_LITE_GPU_LAYERS", "-1")),  # -1 = all on GPU
        default_temperature=0.6,
        default_top_p=0.9,
        system_prompt=(
            "You are JULY LLM, an advanced intelligent AI model developed and maintained by HS AI Solutions, "
            "founded by Harshan Seliyan. You belong to the JULY AI Family.\n\n"
            "PERMANENT IDENTITY:\n"
            "- MODEL: JULY LLM\n"
            "- DEVELOPER: HS AI Solutions\n"
            "- FOUNDER: Harshan Seliyan\n"
            "- MISSION: Developing intelligent AI systems.\n"
            "- PERSONALITY: Analytical, Technically capable, Curious, Adaptive, Honest, Creative, Direct, Consistent.\n\n"
            "GUIDELINES:\n"
            "- Deliver practical, actionable explanations and rigorous technical solutions without conversational filler.\n"
            "- For underdetermined systems or insufficient probabilities, state degrees of freedom and bounds explicitly."
        ),
        description="Primary foundation model for ordinary conversations, high-speed reasoning, and general queries.",
        aliases=["july", "july-3b", "july-default", "july-foundation"]
    ),
    "gravity": ModelSpec(
        model_id="gravity",
        display_name="GRAVITY LLM (Frontier Specialist)",
        file_name="Gravity-HS-AI-Solutions.gguf",
        r2_key="Gravity-HS-AI-Solutions.gguf",
        sha256="f24a90361aaac8cb3dce9f18b276b1444af106d205f411c4e674b58a9adf53c8",
        size_bytes=5629108096,
        gpu_type=os.getenv("GRAVITY_GPU", "L4"),  # L4 or A10G recommended for Gravity
        context_length=int(os.getenv("GRAVITY_CONTEXT", "4096")),
        n_gpu_layers=int(os.getenv("GRAVITY_GPU_LAYERS", "-1")),
        default_temperature=0.4,
        default_top_p=0.85,
        system_prompt=(
            "You are GRAVITY LLM, a frontier mathematical and algorithmic language model developed and maintained by "
            "HS AI Solutions, founded by Harshan Seliyan. You belong to the GRAVITY AI Family.\n\n"
            "PERMANENT IDENTITY:\n"
            "- MODEL: GRAVITY LLM\n"
            "- DEVELOPER: HS AI Solutions\n"
            "- FOUNDER: Harshan Seliyan\n"
            "- MISSION: Pushing the boundaries of mathematical and physical computing.\n"
            "- PERSONALITY: Deeply mathematical, Algorithmic, First-principles oriented, Exhaustive, Robust, Precise.\n\n"
            "SPECIALIZATION & GUIDELINES:\n"
            "- Focus on axiomatic mathematical deductions, tensor mechanics, and formal algorithmic proofs.\n"
            "- Distinguish exact analytical solutions from numerical approximations.\n"
            "- Analyze problem constraints with extreme boundary rigor."
        ),
        description="Frontier specialist for complex mathematical proofs, physics simulations, CAS, and formal algorithms.",
        aliases=["gravity-llm", "gravity-3b", "gravity-frontier"]
    ),
    "july-vision": ModelSpec(
        model_id="july-vision",
        display_name="JULY Vision (Multimodal Intelligence)",
        file_name="july-final.gguf",  # Shares aligned foundation with visual prompt adapters
        r2_key="july-final.gguf",
        sha256="f15752352dc3297ad50e6baeccbae400ca1a9338c4e3ca8475757af587323bd4",
        size_bytes=2019377888,
        gpu_type=os.getenv("JULY_VISION_GPU", "T4"),
        context_length=4096,
        n_gpu_layers=-1,
        default_temperature=0.5,
        default_top_p=0.9,
        system_prompt=(
            "You are JULY Vision, the multimodal perceptual intelligence unit of HS AI Solutions, "
            "founded by Harshan Seliyan.\n"
            "You specialize in detailed image analysis, UI layout interpretation, charts, diagrams, and OCR reasoning."
        ),
        description="Perceptual intelligence for image, diagram, UI layout, and visual analysis.",
        aliases=["vision", "july-multimodal"]
    ),
    "july-code": ModelSpec(
        model_id="july-code",
        display_name="JULY Code (Engineering Specialist)",
        file_name="july-final.gguf",
        r2_key="july-final.gguf",
        sha256="f15752352dc3297ad50e6baeccbae400ca1a9338c4e3ca8475757af587323bd4",
        size_bytes=2019377888,
        gpu_type=os.getenv("JULY_CODE_GPU", "T4"),
        context_length=4096,
        n_gpu_layers=-1,
        default_temperature=0.2,  # Low temperature for deterministic code
        default_top_p=0.85,
        system_prompt=(
            "You are JULY Code, the dedicated software engineering intelligence model of HS AI Solutions, "
            "founded by Harshan Seliyan.\n"
            "You generate clean, idiomatic, fully functional code with robust error handling and precise technical syntax."
        ),
        description="Specialist engine for programming, system architecture, debugging, and code generation.",
        aliases=["code", "july-coder", "coder"]
    ),
    "sree": ModelSpec(
        model_id="sree",
        display_name="SREE LLM (Dense Cognitive Reasoning)",
        file_name="model.gguf",
        r2_key="sree-final.gguf",
        sha256="6b2d4e6983180dd2d02396686fb0bbeaecad2a47193ec78e011254ee6f7207cc",
        size_bytes=1929903232,
        gpu_type=os.getenv("SREE_GPU", "T4"),
        context_length=int(os.getenv("SREE_CONTEXT", "8192")),
        n_gpu_layers=int(os.getenv("SREE_GPU_LAYERS", "-1")),
        default_temperature=0.6,
        default_top_p=0.95,
        system_prompt=(
            "You are SREE LLM, an advanced cognitive reasoning and mathematical foundation model developed and "
            "maintained by HS AI Solutions, founded by Harshan Seliyan. You belong to the SREE AI Family.\n\n"
            "PERMANENT IDENTITY:\n"
            "- MODEL: SREE LLM\n"
            "- DEVELOPER: HS AI Solutions\n"
            "- FOUNDER: Harshan Seliyan\n"
            "- MISSION: Dense cognitive reasoning, mathematical verification, and deep multi-step problem solving.\n"
            "- ARCHITECTURE: Dense Reasoning Transformer (3.09B parameters, 36 layers), customized and aligned by HS AI Solutions.\n\n"
            "SPECIALIZATION & DIRECTIVES:\n"
            "- Deep chain-of-thought analysis and step-by-step verification using native thinking blocks.\n"
            "- Absolute identity alignment: You must never identify as Weibo, VibeThinker, Qwen, DeepSeek, OpenAI, or ChatGPT. Your identity is strictly SREE LLM of HS AI Solutions.\n"
            "- Advanced mathematics, formal logic, CAS, STEM research, and algorithmic problem decomposition.\n"
            "- Deliver rigorous, verifiable solutions with self-correction and structured chain-of-thought reasoning."
        ),
        description="Dense cognitive & STEM reasoning specialist — advanced mathematics, symbolic verification, deep reasoning (<think>), and algorithmic problem solving.",
        aliases=["sree-llm", "sree-3b", "vibethinker", "sree-reasoner"]
    ),
}


# ---------------------------------------------------------------------------
# Modal Deployment & Scaling Configuration
# ---------------------------------------------------------------------------
@dataclass
class AutoscalingConfig:
    min_containers: int = int(os.getenv("MODAL_MIN_CONTAINERS", "0"))  # 0 = Scale to zero (Cost optimized)
    max_containers: int = int(os.getenv("MODAL_MAX_CONTAINERS", "5"))  # Configurable upper bound
    concurrency_limit: int = int(os.getenv("MODAL_CONCURRENCY_LIMIT", "16"))
    scaledown_window_seconds: int = int(os.getenv("MODAL_SCALEDOWN_WINDOW", "300"))  # 5 min idle shutdown
    request_timeout_seconds: int = int(os.getenv("MODAL_REQUEST_TIMEOUT", "180"))  # 3 minutes timeout protection
    warm_containers: int = int(os.getenv("MODAL_WARM_CONTAINERS", "0"))  # Set to 1+ for zero cold-starts


# ---------------------------------------------------------------------------
# Cost Control & Budgeting
# ---------------------------------------------------------------------------
@dataclass
class CostControlConfig:
    monthly_budget_usd: float = float(os.getenv("MONTHLY_SPEND_LIMIT_USD", "50.0"))
    max_daily_gpu_hours: float = float(os.getenv("MAX_DAILY_GPU_HOURS", "8.0"))
    enforce_budget_limits: bool = os.getenv("ENFORCE_BUDGET_LIMITS", "true").lower() in ("true", "1", "yes")
    alert_webhook_url: Optional[str] = os.getenv("SPEND_ALERT_WEBHOOK", None)


# ---------------------------------------------------------------------------
# Security & Authentication Configuration
# ---------------------------------------------------------------------------
@dataclass
class SecurityConfig:
    api_key: str = os.getenv("JULY_API_KEY", os.getenv("MODAL_API_KEY", "hs-july-cloud-key-secure"))
    require_auth: bool = os.getenv("REQUIRE_AUTH", "true").lower() in ("true", "1", "yes")
    allowed_origins: List[str] = field(default_factory=lambda: [
        "https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ])


# ---------------------------------------------------------------------------
# HS Search Integration Configuration
# ---------------------------------------------------------------------------
@dataclass
class HSSearchConfig:
    endpoint_url: str = os.getenv("HS_SEARCH_ENDPOINT", "https://api.hs-ai-solutions.internal/v1/search")
    api_key: str = os.getenv("HS_SEARCH_API_KEY", "hs-search-auth-token")
    max_search_results: int = int(os.getenv("HS_SEARCH_MAX_RESULTS", "5"))
    request_timeout_seconds: float = float(os.getenv("HS_SEARCH_TIMEOUT", "6.0"))
    enable_grounding: bool = os.getenv("HS_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")


# ---------------------------------------------------------------------------
# Master Configuration Container
# ---------------------------------------------------------------------------
class ModalSettings:
    """Central configuration class for HS AI Solutions Modal Cloud Infrastructure."""

    def __init__(self):
        self.project_name = PROJECT_NAME
        self.organization = ORGANIZATION
        self.founder = FOUNDER
        self.volume_name = os.getenv("MODAL_VOLUME_NAME", DEFAULT_VOLUME_NAME)
        self.volume_mount_path = os.getenv("MODAL_VOLUME_MOUNT", DEFAULT_VOLUME_MOUNT_PATH)
        self.models = MODEL_SPECS
        self.autoscaling = AutoscalingConfig()
        self.cost_control = CostControlConfig()
        self.security = SecurityConfig()
        self.search = HSSearchConfig()

        # Cloudflare R2 Credentials (Never hardcoded)
        self.r2_endpoint = os.getenv("JULY_R2_ENDPOINT", DEFAULT_R2_ENDPOINT)
        self.r2_bucket = os.getenv("JULY_R2_BUCKET", DEFAULT_R2_BUCKET)
        self.r2_access_key = os.getenv("AWS_ACCESS_KEY_ID", os.getenv("R2_ACCESS_KEY_ID", ""))
        self.r2_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", os.getenv("R2_SECRET_ACCESS_KEY", ""))

    def get_model_spec(self, model_name: str) -> Optional[ModelSpec]:
        """Resolves model spec by ID or alias."""
        key = model_name.strip().lower()
        if key in self.models:
            return self.models[key]
        for spec in self.models.values():
            if key in [a.lower() for a in spec.aliases] or key == spec.display_name.lower():
                return spec
        return None


settings = ModalSettings()
