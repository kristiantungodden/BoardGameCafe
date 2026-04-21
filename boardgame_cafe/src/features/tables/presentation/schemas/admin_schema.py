from __future__ import annotations

from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ZoneStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class FloorRequest(BaseModel):
    number: int = Field(gt=0)
    name: NameStr
    active: bool = True
    notes: Optional[str] = None


class TableRequest(BaseModel):
    number: int = Field(gt=0)
    capacity: int = Field(gt=0)
    floor: int = Field(gt=0)
    zone: ZoneStr
    status: str = "available"
    features: dict[str, bool] = Field(default_factory=dict)
    width: Optional[int] = Field(default=None, gt=0)
    height: Optional[int] = Field(default=None, gt=0)
    rotation: Optional[int] = Field(default=None, ge=0)


class FloorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    name: str
    active: bool
    notes: Optional[str] = None


class TableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    capacity: int
    floor: int
    zone: str
    features: dict[str, bool]
    width: Optional[int] = None
    height: Optional[int] = None
    rotation: Optional[int] = None
    status: str


class ZoneRequest(BaseModel):
    floor: int = Field(gt=0)
    name: ZoneStr
    active: bool = True
    notes: Optional[str] = None


class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    floor: int
    name: str
    active: bool
    notes: Optional[str] = None