"""Execution engine and admin configurations."""

NODE_EXECUTION_CONFIG = {
    "stream_timeout": 10.0,
    "stream_poll_timeout": 0.1,
    "max_tokens_default": 128000,
    "score_decay_factor": 0.1
}

ADMIN_CONFIG = {
    "chunk_size_min": 512,
    "chunk_size_max": 8192,
    "chunk_size_default": 2048,
    "chunk_overlap_ratio": 0.25
}
