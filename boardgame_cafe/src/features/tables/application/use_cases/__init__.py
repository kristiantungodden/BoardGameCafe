"""Exports for table use cases.

The table-admin use case module is optional in this branch. Keep imports resilient
so app startup and scripts (like seeders) still work when that module is absent.
"""

__all__ = []

try:
	from .admin_table_use_cases import (
		CreateZoneCommand,
		CreateZoneUseCase,
		CreateFloorCommand,
		CreateFloorUseCase,
		CreateTableCommand,
		CreateTableUseCase,
		DeleteFloorUseCase,
		DeleteTableUseCase,
		DeleteZoneUseCase,
		ListFloorsUseCase,
		ListTablesUseCase,
		ListZonesUseCase,
		UpdateFloorCommand,
		UpdateFloorUseCase,
		UpdateTableCommand,
		UpdateTableUseCase,
		UpdateZoneCommand,
		UpdateZoneUseCase,
	)

	__all__.extend([
		"CreateZoneCommand",
		"CreateZoneUseCase",
		"CreateFloorCommand",
		"CreateFloorUseCase",
		"CreateTableCommand",
		"CreateTableUseCase",
		"DeleteFloorUseCase",
		"DeleteTableUseCase",
		"DeleteZoneUseCase",
		"ListFloorsUseCase",
		"ListTablesUseCase",
		"ListZonesUseCase",
		"UpdateFloorCommand",
		"UpdateFloorUseCase",
		"UpdateTableCommand",
		"UpdateTableUseCase",
		"UpdateZoneCommand",
		"UpdateZoneUseCase",
	])
except ModuleNotFoundError:
	pass

