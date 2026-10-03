from typing import Dict
from vektorsync.core.schemas import CausalRelation

class CausalHorizonArbiter:
    @staticmethod
    def inspect_causality(v_base: Dict[str, int], v_server: Dict[str, int]) -> CausalRelation:
        all_nodes = set(v_base.keys()).union(set(v_server.keys()))
        base_dominates = False
        server_dominates = False

        for node in all_nodes:
            clock_base = v_base.get(node, 0)
            clock_server = v_server.get(node, 0)
            if clock_base > clock_server:
                base_dominates = True
            elif clock_server > clock_base:
                server_dominates = True

        if not base_dominates and not server_dominates:
            return CausalRelation.COINCIDENT
        if base_dominates and not server_dominates:
            return CausalRelation.CAUSAL_DESCENDANT
        if server_dominates and not base_dominates:
            return CausalRelation.CAUSAL_ANCESTOR
        return CausalRelation.CONCURRENT_BRANCH

    @staticmethod
    def reconcile_vector_clocks(v_server: Dict[str, int], v_client: Dict[str, int], client_id: str) -> Dict[str, int]:
        all_nodes = set(v_server.keys()).union(set(v_client.keys()))
        merged = {node: max(v_server.get(node, 0), v_client.get(node, 0)) for node in all_nodes}
        merged[client_id] = merged.get(client_id, 0) + 1
        return merged