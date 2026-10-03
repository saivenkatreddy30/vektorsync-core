from typing import Dict, Any, Tuple
from vektorsync.engine.semantic_arbiter import LatentSemanticConvergenceArbiter

class TripartiteStructuralDiffer:
    @staticmethod
    def execute_3way_reconciliation(
        data_base: Dict[str, Any],
        data_server: Dict[str, Any],
        data_client: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], Dict[str, Any], bool]:
        reconciled = dict(data_server)
        conflicts = {}
        all_fields = set(data_base.keys()).union(set(data_server.keys())).union(set(data_client.keys()))
        ai_invoked = False

        for field in all_fields:
            val_base = data_base.get(field)
            val_server = data_server.get(field)
            val_client = data_client.get(field)

            if val_client == val_base:
                continue

            if val_server == val_base:
                reconciled[field] = val_client
                continue

            if val_server == val_client:
                reconciled[field] = val_client
                continue

            if isinstance(val_server, str) and isinstance(val_client, str):
                arbiter_verdict = LatentSemanticConvergenceArbiter.evaluate_semantic_alignment(val_server, val_client)
                ai_invoked = True
                if arbiter_verdict["aligned"]:
                    reconciled[field] = arbiter_verdict["resolved_text"]
                    continue
                else:
                    conflicts[field] = {
                        "base_origin": val_base,
                        "server_branch": val_server,
                        "client_branch": val_client,
                        "ai_evaluation": arbiter_verdict["diagnostic"],
                        "cosine_similarity": arbiter_verdict["similarity_score"]
                    }
            else:
                conflicts[field] = {
                    "base_origin": val_base,
                    "server_branch": val_server,
                    "client_branch": val_client,
                    "reason": "Discrete scalar collision"
                }

        is_clean = len(conflicts) == 0
        return is_clean, reconciled, conflicts, ai_invoked