"""Vipps eCom adapter package for the payments feature.

Exports the feature-scoped `VippsAdapter` and the `vipps_callbacks` blueprint.
"""
from .vipps_adapter import VippsAdapter
from .vipps_webhook import vipps_callbacks

__all__ = ["VippsAdapter", "vipps_callbacks"]
