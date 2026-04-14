"""Shared content hashing utility."""

import hashlib


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of text content for cache invalidation."""
    return hashlib.sha256(content.encode()).hexdigest()
