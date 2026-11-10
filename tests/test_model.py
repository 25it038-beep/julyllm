"""
HS AI SOLUTIONS - JULY MODEL INSPECTION & INTEGRITY TESTS
Founder: Harshan Seliyan
"""

import os
import struct
import tempfile
import pytest
from app.gguf_inspector import (
    GGUFInspector,
    GGUFInspectionError,
    GGUFValueType,
    inspect_gguf_file
)
from app.model_loader import ModelManager


def create_synthetic_gguf(path: str, arch: str = "llama", param_count: int = 3000000000):
    """Generates a valid binary GGUF header for testing without needing 2GB disk space."""
    with open(path, "wb") as f:
        # 1. Magic
        f.write(b"GGUF")
        # 2. Version (3), tensor count (1), metadata kv count (3)
        f.write(struct.pack("<IQQ", 3, 1, 3))

        # Helper to write string
        def write_str(s: str):
            encoded = s.encode("utf-8")
            f.write(struct.pack("<Q", len(encoded)))
            f.write(encoded)

        # KV 1: general.architecture (string)
        write_str("general.architecture")
        f.write(struct.pack("<I", GGUFValueType.STRING))
        write_str(arch)

        # KV 2: general.file_type (uint32) -> 15 = Q4_K_M
        write_str("general.file_type")
        f.write(struct.pack("<I", GGUFValueType.UINT32))
        f.write(struct.pack("<I", 15))

        # KV 3: llama.context_length (uint32)
        write_str(f"{arch}.context_length")
        f.write(struct.pack("<I", GGUFValueType.UINT32))
        f.write(struct.pack("<I", 4096))

        # Tensor 1: token_embd.weight
        write_str("token_embd.weight")
        f.write(struct.pack("<I", 2))  # 2 dims
        f.write(struct.pack("<QQ", 3072, 1000))
        f.write(struct.pack("<I", 12))  # Q4_K
        f.write(struct.pack("<Q", 0))   # offset


def test_gguf_synthetic_valid():
    with tempfile.NamedTemporaryFile(suffix=".gguf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        create_synthetic_gguf(tmp_path, arch="llama")
        info = inspect_gguf_file(tmp_path)

        assert info["status"] == "valid"
        assert info["architecture"] == "llama"
        assert info["quantization"] == "MOSTLY_Q4_K_M"
        assert info["context_length"] == 4096
        assert info["tensor_count"] == 1
        assert info["is_compatible"] is True
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_gguf_invalid_magic():
    with tempfile.NamedTemporaryFile(suffix=".gguf", delete=False) as tmp:
        tmp.write(b"NOT_GGUF_HEADER_BYTES")
        tmp_path = tmp.name

    try:
        with pytest.raises(GGUFInspectionError) as exc_info:
            inspect_gguf_file(tmp_path)
        assert "Invalid GGUF magic bytes" in str(exc_info.value)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_gguf_corrupted_file():
    with tempfile.NamedTemporaryFile(suffix=".gguf", delete=False) as tmp:
        tmp.write(b"GGUF")  # truncated after magic
        tmp_path = tmp.name

    try:
        with pytest.raises(Exception):
            inspect_gguf_file(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_model_manager_mock_mode():
    mgr = ModelManager()
    mgr.is_mock = True
    mgr.load()
    assert mgr.is_loaded is True
    assert mgr.model_metadata.get("is_mock") is True
    mgr.unload()
    assert mgr.is_loaded is False
