import os
import yaml
import networkx as nx
from typing import Dict, List, Any, Optional

YAML_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services.yaml"))

class ServiceTopology:
    def __init__(self, yaml_path: str = YAML_PATH):
        self.yaml_path = yaml_path
        self.config: Dict[str, Any] = {}
        self.g = nx.DiGraph()
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.yaml_path):
            raise FileNotFoundError(f"services.yaml not found at {self.yaml_path}")
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.g.clear()
        for svc_id, svc_data in self.config.get("services", {}).items():
            self.g.add_node(svc_id, **svc_data)

        for dep in self.config.get("dependencies", []):
            self.g.add_edge(dep["from"], dep["to"])

    def get_services(self) -> Dict[str, Dict[str, Any]]:
        return self.config.get("services", {})

    def get_service(self, svc_id: str) -> Optional[Dict[str, Any]]:
        services = self.config.get("services", {})
        if svc_id in services:
            return services[svc_id]
        # Search by service name if id not matched
        for k, v in services.items():
            if v.get("name") == svc_id:
                return v
        return None

    def get_sli(self, svc_id: str) -> Dict[str, float]:
        svc = self.get_service(svc_id)
        if svc and "sli" in svc:
            return svc["sli"]
        return {"p95_latency_ms": 50.0, "error_rate_pct": 0.1, "cpu_pct": 30.0, "mem_pct": 40.0}

    def get_downstream_dependencies(self, svc_id: str) -> List[str]:
        """Services that svc_id directly calls/depends on."""
        canonical_id = self._canonical_id(svc_id)
        if canonical_id in self.g:
            return list(self.g.successors(canonical_id))
        return []

    def get_upstream_callers(self, svc_id: str) -> List[str]:
        """Services that call svc_id directly."""
        canonical_id = self._canonical_id(svc_id)
        if canonical_id in self.g:
            return list(self.g.predecessors(canonical_id))
        return []

    def _canonical_id(self, svc_id: str) -> str:
        if svc_id in self.g:
            return svc_id
        for k, v in self.get_services().items():
            if v.get("name") == svc_id:
                return k
        return svc_id

    def find_propagation_path(self, root_service: str, target: str = "checkout") -> List[str]:
        """
        Failure in root_service propagates upstream to target service (e.g. checkout or gateway).
        Returns dependency path from target to root_service.
        """
        root_c = self._canonical_id(root_service)
        target_c = self._canonical_id(target)

        if root_c == target_c:
            return [root_c]

        try:
            # Shortest path from caller to callee in dependency graph: e.g. checkout -> payments -> orders-db
            path = nx.shortest_path(self.g, source=target_c, target=root_c)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            try:
                path = nx.shortest_path(self.g, source="gateway", target=root_c)
                return path
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return [root_c]

    def calculate_health(self, active_incident_service: Optional[str] = None, is_resolved: bool = True) -> Dict[str, Dict[str, Any]]:
        health_map = {}
        services = self.get_services()

        if not active_incident_service or is_resolved:
            for node_id, meta in services.items():
                health_map[node_id] = {
                    "id": node_id,
                    "name": meta["name"],
                    "display": meta["display"],
                    "status": "Healthy",
                    "color": "grn",
                    "badge": "Healthy",
                    "is_root": False
                }
            return health_map

        root_c = self._canonical_id(active_incident_service)
        path = self.find_propagation_path(root_c, "checkout")

        for node_id, meta in services.items():
            if node_id == root_c:
                status, color, badge, is_root = "Failing", "red", "Failing", True
            elif node_id in path or node_id == "checkout":
                status, color, badge, is_root = "Degraded", "amb", "Degraded", False
            else:
                status, color, badge, is_root = "Healthy", "grn", "Healthy", False

            health_map[node_id] = {
                "id": node_id,
                "name": meta["name"],
                "display": meta["display"],
                "status": status,
                "color": color,
                "badge": badge,
                "is_root": is_root
            }
        return health_map

    def get_graph_data(self, active_incident_service: Optional[str] = None, is_resolved: bool = True, is_verified: bool = False):
        health_map = self.calculate_health(active_incident_service, is_resolved)
        root_c = self._canonical_id(active_incident_service) if active_incident_service else None
        prop_path = self.find_propagation_path(root_c, "checkout") if root_c and not is_resolved else []

        services = self.get_services()
        nodes = []
        for node_id, meta in services.items():
            h = health_map[node_id]
            nodes.append({
                "id": node_id,
                "name": meta["name"],
                "display": meta["display"],
                "x": meta["coords"]["x"],
                "y": meta["coords"]["y"],
                "tier": meta["tier"],
                "status": h["status"],
                "color": h["color"],
                "badge": h["badge"],
                "is_root": h["is_root"],
                "is_verified": is_verified if h["is_root"] else False
            })

        edges = []
        for dep in self.config.get("dependencies", []):
            u, v = dep["from"], dep["to"]
            is_active_path = (u in prop_path and v in prop_path) if prop_path else False
            edges.append({
                "from": u,
                "to": v,
                "from_x": services[u]["coords"]["x"],
                "from_y": services[u]["coords"]["y"],
                "to_x": services[v]["coords"]["x"],
                "to_y": services[v]["coords"]["y"],
                "is_path": is_active_path
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "propagation_path": [services[n]["name"] for n in prop_path],
            "root_service": root_c,
            "root_service_name": services[root_c]["name"] if root_c in services else None
        }

topology = ServiceTopology()

