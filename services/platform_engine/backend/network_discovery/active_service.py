from __future__ import annotations
from collections import defaultdict
from uuid import UUID
from vehicle.network.active_discovery import ActiveEcuDiscoveryEngine, ActiveProbePolicy, ActiveProbeResult, ActiveProbeTarget
from vehicle.network.discovery import VehicleNetworkDiscoveryResult
from vehicle.network.models import VehicleNetworkTopology

class ActiveNetworkDiscoveryService:
    def __init__(self):
        self._engine = ActiveEcuDiscoveryEngine()
        self._results: dict[str, list[ActiveProbeResult]] = defaultdict(list)

    async def probe_candidates(self, session_id: UUID, passive: VehicleNetworkDiscoveryResult,
                               buses: dict, topology: VehicleNetworkTopology | None = None,
                               candidate_ids: list[str] | None = None,
                               policy: ActiveProbePolicy | None = None) -> list[ActiveProbeResult]:
        engine = ActiveEcuDiscoveryEngine(policy or self._engine.policy)
        allowed = set(candidate_ids) if candidate_ids else None
        targets: list[ActiveProbeTarget] = []
        for candidate in passive.ecu_candidates:
            if allowed is not None and candidate.candidate_id not in allowed: continue
            if candidate.request_id is None or candidate.response_id is None: continue
            access_bus = candidate.bus
            gateway_id = None
            if topology:
                for route in topology.routes:
                    try: ecu = topology.ecu(route.target_ecu_id)
                    except KeyError: continue
                    if ecu.request_id == candidate.request_id and ecu.response_id == candidate.response_id and ecu.bus == candidate.bus:
                        access_bus, gateway_id = route.source_bus, route.gateway_id
                        break
            if access_bus not in buses: continue
            targets.append(ActiveProbeTarget(candidate.candidate_id, access_bus, candidate.request_id, candidate.response_id, gateway_id))
        results = await engine.probe_many(targets, buses)
        self._results[str(session_id)] = results
        return results

    def results(self, session_id: UUID) -> list[ActiveProbeResult]:
        return list(self._results.get(str(session_id), ()))

    def correlate(self, session_id: UUID, passive: VehicleNetworkDiscoveryResult, topology: VehicleNetworkTopology | None = None) -> dict:
        results = self.results(session_id)
        by_id = {r.candidate_id: r for r in results}
        candidates = []
        for c in passive.ecu_candidates:
            result = by_id.get(c.candidate_id)
            if result is None:
                candidates.append({'candidate_id': c.candidate_id, 'status': 'PASSIVE_ONLY', 'classification': c.classification, 'confidence': c.confidence})
                continue
            if result.classification == 'CONFIRMED_UDS_ECU':
                status = 'CONFIRMED'
            elif result.classification == 'ACTIVE_UDS_RESPONDER':
                status = 'ACTIVE_RESPONDER'
            else:
                status = 'NO_RESPONSE'
            item = {'candidate_id': c.candidate_id, 'status': status, 'passive': c.to_dict(), 'active': result.to_dict()}
            if result.gateway_id: item['gateway_correlation'] = {'gateway_id': result.gateway_id, 'access_bus': result.bus, 'target_bus': c.bus, 'status': 'CORRELATED'}
            candidates.append(item)
        passive_ids = {c.candidate_id for c in passive.ecu_candidates}
        unmatched_active = [r.to_dict() for r in results if r.candidate_id not in passive_ids]
        return {'candidates': candidates, 'active_probe_count': len(results), 'confirmed_count': sum(x['status'] == 'CONFIRMED' for x in candidates), 'gateway_correlations': sum(1 for x in candidates if x.get('gateway_correlation')), 'unmatched_active': unmatched_active}
