"""
HS AI SOLUTIONS - GGUF BINARY INSPECTOR
Independent, Zero-Corruption GGUF Metadata & Tensor Inspector
Founder: Harshan Seliyan
"""

import os
import struct
from typing import Dict, Any, List, Optional, Tuple


class GGUFValueType:
    UINT8 = 0
    INT8 = 1
    UINT16 = 2
    INT16 = 3
    UINT32 = 4
    INT32 = 5
    FLOAT32 = 6
    BOOL = 7
    STRING = 8
    ARRAY = 9
    UINT64 = 10
    INT64 = 11
    FLOAT64 = 12


FILE_TYPE_MAP = {
    0: "ALL_F32",
    1: "MOSTLY_F16",
    2: "MOSTLY_Q4_0",
    3: "MOSTLY_Q4_1",
    7: "MOSTLY_Q8_0",
    8: "MOSTLY_Q5_0",
    9: "MOSTLY_Q5_1",
    10: "MOSTLY_Q2_K",
    11: "MOSTLY_Q3_K_S",
    12: "MOSTLY_Q3_K_M",
    13: "MOSTLY_Q3_K_L",
    14: "MOSTLY_Q4_K_S",
    15: "MOSTLY_Q4_K_M",
    16: "MOSTLY_Q5_K_S",
    17: "MOSTLY_Q5_K_M",
    18: "MOSTLY_Q6_K",
    19: "MOSTLY_IQ2_XXS",
    20: "MOSTLY_IQ2_XS",
    21: "MOSTLY_Q2_K_S",
    22: "MOSTLY_IQ3_XS",
    23: "MOSTLY_IQ3_XXS",
    24: "MOSTLY_IQ1_S",
    25: "MOSTLY_IQ4_NL",
    26: "MOSTLY_IQ3_S",
    27: "MOSTLY_IQ3_M",
    28: "MOSTLY_IQ2_S",
    29: "MOSTLY_IQ2_M",
    30: "MOSTLY_IQ4_XS",
    31: "MOSTLY_IQ1_M",
    32: "MOSTLY_BF16",
    33: "MOSTLY_Q4_0_4_4",
    34: "MOSTLY_Q4_0_4_8",
    35: "MOSTLY_Q4_0_8_8",
}

GGML_TYPE_MAP = {
    0: "F32",
    1: "F16",
    2: "Q4_0",
    3: "Q4_1",
    6: "Q5_0",
    7: "Q5_1",
    8: "Q8_0",
    9: "Q8_1",
    10: "Q2_K",
    11: "Q3_K",
    12: "Q4_K",
    13: "Q5_K",
    14: "Q6_K",
    15: "Q8_K",
    16: "IQ2_XXS",
    17: "IQ2_XS",
    18: "IQ3_XXS",
    19: "IQ1_S",
    20: "IQ4_NL",
    21: "IQ3_S",
    22: "IQ2_S",
    23: "IQ4_XS",
    24: "I8",
    25: "I16",
    26: "I32",
    27: "I64",
    28: "F64",
    29: "IQ1_M",
    30: "BF16",
    31: "Q4_0_4_4",
    32: "Q4_0_4_8",
    33: "Q4_0_8_8",
}

SUPPORTED_ARCHITECTURES = {
    "llama", "qwen2", "mistral", "phi3", "phi2", "gemma", "gemma2",
    "falcon", "starcoder2", "bert", "nomic-bert", "bloom", "mpt", "gptneox"
}


class GGUFInspectionError(Exception):
    """Raised when GGUF validation or inspection fails."""
    pass


class GGUFInspector:
    """
    High-performance, memory-safe GGUF inspector.
    Reads file headers without loading full tensors into memory.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Model file not found: {file_path}")
        self.file_size = os.path.getsize(file_path)

    def _read_string(self, f) -> str:
        length_bytes = f.read(8)
        if len(length_bytes) < 8:
            raise GGUFInspectionError("Unexpected EOF while reading string length")
        length = struct.unpack("<Q", length_bytes)[0]
        # Guard against absurd length values in corrupt files
        if length > 50 * 1024 * 1024:
            raise GGUFInspectionError(f"String length too large ({length} bytes), possible corruption")
        raw_str = f.read(length)
        if len(raw_str) < length:
            raise GGUFInspectionError("Unexpected EOF while reading string content")
        return raw_str.decode("utf-8", errors="replace")

    def _read_value(self, f, val_type: int) -> Any:
        if val_type == GGUFValueType.UINT8:
            return struct.unpack("<B", f.read(1))[0]
        elif val_type == GGUFValueType.INT8:
            return struct.unpack("<b", f.read(1))[0]
        elif val_type == GGUFValueType.UINT16:
            return struct.unpack("<H", f.read(2))[0]
        elif val_type == GGUFValueType.INT16:
            return struct.unpack("<h", f.read(2))[0]
        elif val_type == GGUFValueType.UINT32:
            return struct.unpack("<I", f.read(4))[0]
        elif val_type == GGUFValueType.INT32:
            return struct.unpack("<i", f.read(4))[0]
        elif val_type == GGUFValueType.FLOAT32:
            return struct.unpack("<f", f.read(4))[0]
        elif val_type == GGUFValueType.UINT64:
            return struct.unpack("<Q", f.read(8))[0]
        elif val_type == GGUFValueType.INT64:
            return struct.unpack("<q", f.read(8))[0]
        elif val_type == GGUFValueType.FLOAT64:
            return struct.unpack("<d", f.read(8))[0]
        elif val_type == GGUFValueType.BOOL:
            return struct.unpack("<?", f.read(1))[0]
        elif val_type == GGUFValueType.STRING:
            return self._read_string(f)
        elif val_type == GGUFValueType.ARRAY:
            sub_type = struct.unpack("<I", f.read(4))[0]
            arr_len = struct.unpack("<Q", f.read(8))[0]

            # Optimization: If it's a huge array (e.g. token list > 1000 items),
            # don't materialize all strings into memory to preserve RAM.
            if arr_len > 1000 and sub_type == GGUFValueType.STRING:
                # Read first few tokens and skip the rest
                sample = []
                for i in range(arr_len):
                    if i < 5:
                        sample.append(self._read_string(f))
                    else:
                        s_len = struct.unpack("<Q", f.read(8))[0]
                        f.seek(s_len, os.SEEK_CUR)
                return {"_array_type": "string", "_array_length": arr_len, "sample": sample}
            elif arr_len > 10000:
                # Large numerical array (e.g. token scores)
                # Calculate byte size to skip
                size_map = {
                    GGUFValueType.UINT8: 1, GGUFValueType.INT8: 1,
                    GGUFValueType.UINT16: 2, GGUFValueType.INT16: 2,
                    GGUFValueType.UINT32: 4, GGUFValueType.INT32: 4,
                    GGUFValueType.FLOAT32: 4, GGUFValueType.UINT64: 8,
                    GGUFValueType.INT64: 8, GGUFValueType.FLOAT64: 8,
                    GGUFValueType.BOOL: 1
                }
                item_size = size_map.get(sub_type, 1)
                f.seek(arr_len * item_size, os.SEEK_CUR)
                return {"_array_type": sub_type, "_array_length": arr_len}
            else:
                items = [self._read_value(f, sub_type) for _ in range(arr_len)]
                return items
        else:
            raise GGUFInspectionError(f"Unknown GGUF value type ID: {val_type}")

    def inspect(self) -> Dict[str, Any]:
        """Performs a thorough inspection of the GGUF file header and metadata."""
        with open(self.file_path, "rb") as f:
            magic = f.read(4)
            if magic != b"GGUF":
                raise GGUFInspectionError(
                    f"Invalid GGUF magic bytes: expected b'GGUF', got {magic!r}. "
                    "This file is either corrupt or not a valid GGUF model checkpoint."
                )

            version = struct.unpack("<I", f.read(4))[0]
            if version not in (2, 3):
                raise GGUFInspectionError(
                    f"Unsupported GGUF version {version}. llama.cpp requires GGUF v2 or v3."
                )

            tensor_count = struct.unpack("<Q", f.read(8))[0]
            metadata_kv_count = struct.unpack("<Q", f.read(8))[0]

            metadata: Dict[str, Any] = {}
            for _ in range(metadata_kv_count):
                key = self._read_string(f)
                val_type = struct.unpack("<I", f.read(4))[0]
                val = self._read_value(f, val_type)
                metadata[key] = val

            # Read tensor metadata summaries
            tensors_summary = []
            total_elements = 0
            for i in range(tensor_count):
                tensor_name = self._read_string(f)
                n_dims = struct.unpack("<I", f.read(4))[0]
                dims = [struct.unpack("<Q", f.read(8))[0] for _ in range(n_dims)]
                ggml_type = struct.unpack("<I", f.read(4))[0]
                offset = struct.unpack("<Q", f.read(8))[0]

                elements = 1
                for d in dims:
                    elements *= d
                total_elements += elements

                if i < 10:  # store first 10 for diagnostics
                    tensors_summary.append({
                        "name": tensor_name,
                        "dims": dims,
                        "type": GGML_TYPE_MAP.get(ggml_type, f"TYPE_{ggml_type}"),
                        "offset": offset
                    })

        # Process metadata into structured output
        arch = metadata.get("general.architecture", "unknown")
        file_type_id = metadata.get("general.file_type", None)
        quantization = FILE_TYPE_MAP.get(file_type_id, "Unknown/Custom") if file_type_id is not None else "Unknown"

        # Parameter count estimation
        param_count_est = total_elements
        param_label = f"{round(param_count_est / 1e9, 2)}B" if param_count_est > 0 else "Unknown"

        context_length = (
            metadata.get(f"{arch}.context_length") or
            metadata.get("general.context_length") or
            metadata.get("context_length") or
            2048
        )

        embedding_length = (
            metadata.get(f"{arch}.embedding_length") or
            metadata.get("general.embedding_length") or
            metadata.get("embedding_length") or
            None
        )

        block_count = (
            metadata.get(f"{arch}.block_count") or
            metadata.get("general.block_count") or
            None
        )

        head_count = metadata.get(f"{arch}.attention.head_count", None)
        head_count_kv = metadata.get(f"{arch}.attention.head_count_kv", None)

        vocab_size = None
        tokens_meta = metadata.get("tokenizer.ggml.tokens")
        if isinstance(tokens_meta, dict) and "_array_length" in tokens_meta:
            vocab_size = tokens_meta["_array_length"]
        elif isinstance(tokens_meta, list):
            vocab_size = len(tokens_meta)

        # Check for model compatibility
        is_compatible = True
        compatibility_notes = []
        if arch != "unknown" and arch not in SUPPORTED_ARCHITECTURES:
            is_compatible = False
            compatibility_notes.append(f"Architecture '{arch}' may not be natively supported by llama.cpp.")
        if version not in (2, 3):
            is_compatible = False
            compatibility_notes.append(f"GGUF version {version} is deprecated or invalid.")

        return {
            "status": "valid" if is_compatible else "warning",
            "file_name": os.path.basename(self.file_path),
            "file_size_bytes": self.file_size,
            "file_size_gb": round(self.file_size / (1024 ** 3), 3),
            "gguf_version": version,
            "tensor_count": tensor_count,
            "metadata_kv_count": metadata_kv_count,
            "architecture": arch,
            "model_name": metadata.get("general.name", "JULY"),
            "quantization": quantization,
            "quantization_id": file_type_id,
            "estimated_parameters": param_count_est,
            "parameter_label": metadata.get("general.size_label", param_label),
            "context_length": context_length,
            "embedding_length": embedding_length,
            "block_count": block_count,
            "head_count": head_count,
            "head_count_kv": head_count_kv,
            "vocabulary_size": vocab_size,
            "tokenizer_model": metadata.get("tokenizer.ggml.model", "unknown"),
            "bos_token_id": metadata.get("tokenizer.ggml.bos_token_id"),
            "eos_token_id": metadata.get("tokenizer.ggml.eos_token_id"),
            "is_compatible": is_compatible,
            "compatibility_notes": compatibility_notes,
            "sample_tensors": tensors_summary
        }


def inspect_gguf_file(path: str) -> Dict[str, Any]:
    """Convenience wrapper to inspect a GGUF file."""
    inspector = GGUFInspector(path)
    return inspector.inspect()


if __name__ == "__main__":
    import sys
    import json
    target = sys.argv[1] if len(sys.argv) > 1 else "models/july-final.gguf"
    try:
        info = inspect_gguf_file(target)
        print(json.dumps(info, indent=2))
    except Exception as e:
        print(f"Error inspecting {target}: {e}", file=sys.stderr)
        sys.exit(1)
