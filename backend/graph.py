import networkx as nx
from typing import List, Dict, Tuple, Optional

# Nodes coordinates and friendly names
NODE_DEFINITIONS = {
    "gateway": {"x": 90, "y": 170, "name": "api-gateway", "display": "API Gateway", "tier": "edge"},
    "checkout": {"x": 290, "y": 170, "name": "checkout-svc", "display": "Checkout Service", "tier": "core"},
    "payments": {"x": 490, "y": 90, "name": "payments-svc", "display": "Payments Service", "tier": "backend"},
    "inventory": {"x": 490, "y": 250, "name": "inventory-svc", "display": "Inventory Service", "tier": "backend"},
    "auth": {"x": 290, "y": 60, "name": "auth-svc", "display": "Auth Service", "tier": "core"},
    "orders-db": {"x": 690, "y": 90, "name": "orders-db", "display": "Orders Database", "tier": "datastore"},
    "cache": {"x": 690, "y": 250, "name": "cache", "display": "Redis Cache", "tier": "datastore"}
}

# Directed dependency edges: A -> B means A calls/depends on B
DEPENDENCY_EDGES = [
    ("gateway", "checkout"),
    ("checkout", "payments"),
    ("checkout", "inventory"),
    ("checkout", "auth"),
    ("payments", "orders-db"),
    ("inventory", "cache")
]

class ServiceTopology:
    def __init__(self):
        self.g = nx.DiGraph()
        for node_id, data in NODE_DEFINITIONS.items():
            self.g.add_node(node_id, **data)
        for u, v in DEPENDENCY_EDGES:
            self.g.add_edge(u, v)

    def find_propagation_path(self, root_service: str, target: str = "checkout") -> List[str]:
        """
        Finds the failure propagation path from root cause service back to checkout or gateway.
        Since caller depends on callee, failure in callee propagates upstream against the edge direction!
        """
        if root_service == target:
            return [root_service]
        
        # Check downstream path in reverse or forward
        try:
            # Shortest path from caller to callee in dependency graph:
            # e.g., checkout -> payments -> orders-db
            path = nx.shortest_path(self.g, source=target, target=root_service)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # Check if root_service is reachable from gateway
            try:
                path = nx.shortest_path(self.g, source="gateway", target=root_service)
                return path
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return [root_service]

    def calculate_health(self, active_incident_service: Optional[str] = None, is_resolved: bool = True) -> Dict[str, Dict]:
        """
        Calculates the health of all nodes based on active incident and propagation path.
        """
        health_map = {}
        if not active_incident_service or is_resolved:
            for node_id, meta in NODE_DEFINITIONS.items():
                health_map[node_id] = {
                    "id": node_id,
                    "name": meta["name"],
                    "display": meta["display"],
                    "status": "Healthy",
                    "color": "grn",
                    "badge": "✓ Healthy",
                    "is_root": False
                }
            return health_map

        path = self.find_propagation_path(active_incident_service, "checkout")
        for node_id, meta in NODE_DEFINITIONS.items():
            if node_id == active_incident_service:
                status = "Failing"
                color = "red"
                badge = "▲ Failing"
                is_root = True
            elif node_id in path or node_id == "checkout":
                status = "Degraded"
                color = "amb"
                badge = "◆ Degraded"
                is_root = False
            else:
                status = "Healthy"
                color = "grn"
                badge = "✓ Healthy"
                is_root = False

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
        prop_path = self.find_propagation_path(active_incident_service, "checkout") if active_incident_service and not is_resolved else []
        
        nodes = []
        for node_id, meta in NODE_DEFINITIONS.items():
            h = health_map[node_id]
            nodes.append({
                "id": node_id,
                "name": meta["name"],
                "display": meta["display"],
                "x": meta["x"],
                "y": meta["y"],
                "tier": meta["tier"],
                "status": h["status"],
                "color": h["color"],
                "badge": h["badge"],
                "is_root": h["is_root"],
                "is_verified": is_verified if h["is_root"] else False
            })

        edges = []
        for u, v in DEPENDENCY_EDGES:
            is_active_path = (u in prop_path and v in prop_path) if prop_path else False
            edges.append({
                "from": u,
                "to": v,
                "from_x": NODE_DEFINITIONS[u]["x"],
                "from_y": NODE_DEFINITIONS[u]["y"],
                "to_x": NODE_DEFINITIONS[v]["x"],
                "to_y": NODE_DEFINITIONS[v]["y"],
                "is_path": is_active_path
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "propagation_path": [NODE_DEFINITIONS[n]["name"] for n in prop_path],
            "root_service": active_incident_service,
            "root_service_name": NODE_DEFINITIONS[active_incident_service]["name"] if active_incident_service in NODE_DEFINITIONS else None
        }

topology = ServiceTopology()

