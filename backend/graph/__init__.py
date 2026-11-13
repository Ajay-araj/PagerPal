"""
backend/graph package initialization.
Re-exports topology from backend.simulator.topology for backward compatibility.
"""
from backend.simulator.topology import topology

__all__ = ["topology"]
