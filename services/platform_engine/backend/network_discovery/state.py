from __future__ import annotations
from .service import VehicleNetworkDiscoveryService
from .active_service import ActiveNetworkDiscoveryService

passive_service = VehicleNetworkDiscoveryService()
active_service = ActiveNetworkDiscoveryService()
