"""
backend/memory/kb.py
SQLite-backed Knowledge Base for past incidents.
Hard Rule 8: NEVER auto-apply past fixes. All results are returned strictly
as suggestions for operator human review.
"""
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.database import get_connection


class KnowledgeBase:
    """Knowledge base repository storing incident histories and remediation records."""

    def __init__(self):
        self._init_table()

    def _init_table(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_incidents (
            incident_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            service TEXT NOT NULL,
            fault_type TEXT NOT NULL,
            root_cause TEXT NOT NULL,
            fix_action TEXT NOT NULL,
            resolution_time_sec REAL NOT NULL DEFAULT 0.0,
            verified_recovery INTEGER NOT NULL DEFAULT 1,
            symptoms TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """)
        cursor.execute("SELECT COUNT(*) FROM kb_incidents")
        if cursor.fetchone()[0] == 0:
            now = datetime.now(timezone.utc).isoformat()
            seed_kb = [
                ("INC-PAST-101", now, "payments", "faulty_deployment", "payments", "rollback_deployment", 112.0, 1, "checkout 5xx errors elevated", "Faulty canary deployment v2.4.1 rolled back"),
                ("INC-PAST-102", now, "orders-db", "database_connection_failure", "orders-db", "reset_connection_pooler", 95.0, 1, "connection timeout exhausted pool", "Connection pool leak flushed and restarted"),
                ("INC-PAST-103", now, "inventory", "service_crash", "inventory", "restart_service_container", 84.0, 1, "pod crashloop oomkilled", "Container memory limit increased and pod restarted"),
                ("INC-PAST-104", now, "gateway", "network_latency", "gateway", "shift_traffic_zone", 130.0, 1, "cross-zone rtt delay 504 timeouts", "Traffic shifted away from degraded availability zone"),
                ("INC-PAST-105", now, "checkout", "cpu_stress", "checkout", "scale_service_replicas", 105.0, 1, "cpu saturation above 90%", "Checkout service scaled to 6 replicas with rate limiter"),
                ("INC-PAST-106", now, "cache", "memory_stress", "cache", "flush_and_restart_cache", 78.0, 1, "eviction spike and hit rate collapse", "Volatile keys flushed and cache container restarted")
            ]
            for item in seed_kb:
                cursor.execute("""
                    INSERT OR REPLACE INTO kb_incidents (
                        incident_id, timestamp, service, fault_type, root_cause,
                        fix_action, resolution_time_sec, verified_recovery, symptoms, summary, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8], item[9], now))
        conn.commit()
        conn.close()

    def store_incident(
        self,
        incident_id: str,
        timestamp: str,
        service: str,
        fault_type: str,
        root_cause: str,
        fix_action: str,
        resolution_time_sec: float,
        verified_recovery: bool,
        symptoms: str = "",
        summary: str = ""
    ) -> Dict[str, Any]:
        """
        Stores an incident record into the Knowledge Base.
        Returns the stored record.
        """
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO kb_incidents (
                incident_id, timestamp, service, fault_type, root_cause,
                fix_action, resolution_time_sec, verified_recovery, symptoms, summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident_id, timestamp, service, fault_type, root_cause,
            fix_action, float(resolution_time_sec), 1 if verified_recovery else 0,
            symptoms, summary, now
        ))
        conn.commit()
        conn.close()

        return {
            "incident_id": incident_id,
            "timestamp": timestamp,
            "service": service,
            "fault_type": fault_type,
            "root_cause": root_cause,
            "fix_action": fix_action,
            "resolution_time_sec": resolution_time_sec,
            "verified_recovery": bool(verified_recovery),
            "symptoms": symptoms,
            "summary": summary
        }

    def search_similar(
        self,
        service: Optional[str] = None,
        fault_type: Optional[str] = None,
        symptoms: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Finds past incidents with matching service, fault type, or symptom keywords.
        CRITICAL: Hard Rule 8 - Every item has suggestion_only=True and auto_apply=False.
        """
        conn = get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM kb_incidents WHERE 1=1"
        params: List[Any] = []

        if service and isinstance(service, str):
            # Match canonical or prefixed service
            s_clean = service.lower().removesuffix("-svc")
            query += " AND (LOWER(service) LIKE ? OR LOWER(service) LIKE ?)"
            params.extend([f"%{s_clean}%", f"%{service.lower()}%"])

        if fault_type and isinstance(fault_type, str):
            query += " AND LOWER(fault_type) = ?"
            params.append(fault_type.lower())

        if symptoms and isinstance(symptoms, str):
            query += " AND (LOWER(symptoms) LIKE ? OR LOWER(summary) LIKE ?)"
            params.extend([f"%{symptoms.lower()}%", f"%{symptoms.lower()}%"])

        lim = limit if isinstance(limit, int) else 5
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(lim)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for r in rows:
            results.append({
                "incident_id": r["incident_id"],
                "timestamp": r["timestamp"],
                "service": r["service"],
                "fault_type": r["fault_type"],
                "root_cause": r["root_cause"],
                "fix_action": r["fix_action"],
                "resolution_time_sec": r["resolution_time_sec"],
                "verified_recovery": bool(r["verified_recovery"]),
                "symptoms": r["symptoms"],
                "summary": r["summary"],
                # Hard Rule 8 Enforcement
                "suggestion_only": True,
                "auto_apply": False,
                "review_required": True,
                "guidance": "Past remediation shown for reference only. Manual approval required before any execution."
            })

        return results

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM kb_incidents WHERE incident_id = ?", (incident_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "incident_id": row["incident_id"],
            "timestamp": row["timestamp"],
            "service": row["service"],
            "fault_type": row["fault_type"],
            "root_cause": row["root_cause"],
            "fix_action": row["fix_action"],
            "resolution_time_sec": row["resolution_time_sec"],
            "verified_recovery": bool(row["verified_recovery"]),
            "symptoms": row["symptoms"],
            "summary": row["summary"],
            "suggestion_only": True,
            "auto_apply": False
        }

    def count(self) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM kb_incidents")
        val = cursor.fetchone()[0]
        conn.close()
        return val


kb = KnowledgeBase()
