"""Application-layer use case for managing booking drafts.

Wraps the infrastructure draft store so the presentation layer never
imports directly from the infrastructure layer.
The concrete get/save/clear functions are injected by the composition factory.
"""
from __future__ import annotations

from typing import Callable


class BookingDraftUseCase:
    """Application-layer use case for managing booking drafts."""

    def __init__(
        self,
        *,
        get_fn: Callable,
        save_fn: Callable,
        clear_fn: Callable,
    ):
        self._get = get_fn
        self._save = save_fn
        self._clear = clear_fn

    def get(self, user_id: int) -> dict:
        return self._get(user_id)

    def save(self, user_id: int, data: dict) -> None:
        self._save(user_id, data)

    def clear(self, user_id: int) -> None:
        self._clear(user_id)
