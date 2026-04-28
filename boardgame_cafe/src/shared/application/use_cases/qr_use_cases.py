"""Application-layer use cases for QR code operations.

These use cases wrap the infrastructure QR code functions so that the
presentation layer never imports directly from the infrastructure layer.
The concrete implementations are injected by the composition factories.
"""
from __future__ import annotations

from typing import Callable


class ReservationQrUseCase:
    """Application-layer use case for reservation QR code operations."""

    def __init__(
        self,
        *,
        get_or_create_token_fn: Callable,
        decode_token_fn: Callable,
        generate_svg_fn: Callable,
    ):
        self._get_or_create = get_or_create_token_fn
        self._decode = decode_token_fn
        self._generate_svg = generate_svg_fn

    def get_or_create_token(
        self, secret_key: str, *, user_id: int, reservation_id: int
    ) -> str:
        return self._get_or_create(
            secret_key, user_id=user_id, reservation_id=reservation_id
        )

    def decode_token(self, secret_key: str, token: str) -> int:
        return self._decode(secret_key, token)

    def generate_svg(self, data: str) -> str:
        return self._generate_svg(data)


class GameCopyQrUseCase:
    """Application-layer use case for game copy QR code operations."""

    def __init__(
        self,
        *,
        get_or_create_token_fn: Callable,
        get_copy_id_by_token_fn: Callable,
        generate_svg_fn: Callable,
    ):
        self._get_or_create = get_or_create_token_fn
        self._get_copy_id = get_copy_id_by_token_fn
        self._generate_svg = generate_svg_fn

    def get_or_create_token(self, copy_id: int) -> str:
        return self._get_or_create(copy_id)

    def get_copy_id_by_token(self, token: str) -> int | None:
        return self._get_copy_id(token)

    def generate_svg(self, data: str) -> str:
        return self._generate_svg(data)
