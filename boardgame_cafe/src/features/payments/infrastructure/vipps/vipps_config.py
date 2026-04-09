from dataclasses import dataclass
import os
from typing import Optional


@dataclass
class VippsConfig:
    base_url: str
    subscription_key: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]
    merchant_serial_number: Optional[str]
    callback_prefix: Optional[str]

    @classmethod
    def from_env(cls) -> "VippsConfig":
        return cls(
            base_url=os.getenv("VIPPS_API_BASE", "https://api.vipps.no"),
            subscription_key=os.getenv("VIPPS_SUBSCRIPTION_KEY"),
            client_id=os.getenv("VIPPS_CLIENT_ID"),
            client_secret=os.getenv("VIPPS_CLIENT_SECRET"),
            merchant_serial_number=os.getenv("VIPPS_MERCHANT_SERIAL_NUMBER"),
            callback_prefix=os.getenv("VIPPS_CALLBACK_PREFIX"),
        )
