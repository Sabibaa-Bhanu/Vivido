"""Backward-compatible auth facade.

This module previously contained a separate login implementation.
To avoid divergence, it now re-exports the canonical implementation
from backend.user_management.
"""

from backend.user_management import login_user

__all__ = ["login_user"]
