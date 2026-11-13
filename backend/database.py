import sqlite3
import os
import json
from datetime import datetime, timezone, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "pagerpal.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Services table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        display_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Healthy',
        coords_x INTEGER,
        coords_y INTEGER,
        last_health_check TEXT,
        health_details TEXT
    )
    """)

    # 2. Incidents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        scenario_id TEXT,
        service TEXT NOT NULL,
        severity TEXT NOT NULL,
        status TEXT NOT NULL,
        phase TEXT NOT NULL,
        detected_at TEXT NOT NULL,
        resolved_at TEXT,
        impact_summary TEXT,
        orders_at_risk INTEGER DEFAULT 0,
        checkout_success_pct REAL DEFAULT 100.0,
        active_agent TEXT DEFAULT 'Supervisor',
        created_at TEXT NOT NULL
    )
    """)

    # 3. Alerts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        incident_id TEXT NOT NULL,
        service TEXT NOT NULL,
        name TEXT NOT NULL,
        severity TEXT NOT NULL,
        condition TEXT,
        fired_at TEXT NOT NULL,
        correlation_reason TEXT,
        FOREIGN KEY(incident_id) REFERENCES incidents(id)
    )
    """)

    # 4. Evidence table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence (
        id TEXT PRIMARY KEY,
        incident_id TEXT NOT NULL,
        type TEXT NOT NULL,
        source TEXT NOT NULL,
        claim TEXT NOT NULL,
        role TEXT NOT NULL, -- 'Supports' or 'Conflicts'
        details TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY(incident_id) REFERENCES incidents(id)
    )
    """)

    # 5. Agent events table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        status TEXT NOT NULL, -- 'waiting', 'running', 'completed', 'review', 'failed'
        summary TEXT NOT NULL,
        details TEXT,
        color TEXT DEFAULT 'cy',
        created_at TEXT NOT NULL,
        elapsed_str TEXT,
        FOREIGN KEY(incident_id) REFERENCES incidents(id)
    )
    """)

    # 6. Remediation proposals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS remediation_proposals (
        id TEXT PRIMARY KEY,
        incident_id TEXT NOT NULL,
        action TEXT NOT NULL,
        target_service TEXT NOT NULL,
        risk_level TEXT NOT NULL DEFAULT 'Low',
        is_reversible INTEGER NOT NULL DEFAULT 1,
        timeout_seconds INTEGER NOT NULL DEFAULT 120,
        rollback_plan TEXT NOT NULL,
        expected_effect TEXT NOT NULL,
        policy_level TEXT NOT NULL DEFAULT 'L2',
        policy_allowed INTEGER NOT NULL DEFAULT 1,
        policy_checks_json TEXT NOT NULL,
        FOREIGN KEY(incident_id) REFERENCES incidents(id)
    )
    """)

    # 7. Approvals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS approvals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        decision TEXT NOT NULL, -- 'Approved', 'Rejected'
        decided_at TEXT NOT NULL,
        reviewer TEXT NOT NULL DEFAULT 'Operator (Human)',
        remarks TEXT,
        FOREIGN KEY(incident_id) REFERENCES incidents(id)
    )
    """)

    # 8. Remediation runs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS remediation_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        action TEXT NOT NULL,
        status TEXT NOT NULL, -- 'running', 'completed', 'stopped', 'failed'
        started_at TEXT NOT NULL,
        completed_at TEXT,
        rollback_triggered INTEGER NOT NULL DEFAULT 0,
        log TEXT,
        FOREIGN KEY(incident_id) REFERENCES incidents(id)
    )
    """)

    # 9. Verification results table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verification_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        is_verified INTEGER NOT NULL DEFAULT 0,
        checks_passed INTEGER NOT NULL DEFAULT 0,
        total_checks INTEGER NOT NULL DEFAULT 4,
        checks_json TEXT,
        before_metrics_json TEXT,
        after_metrics_json TEXT,
        verified_at TEXT,
        FOREIGN KEY(incident_id) REFERENCES incidents(id)
    )
    """)

    # 10. Postmortems table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS postmortems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        content_markdown TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(incident_id) REFERENCES incidents(id)
    )
    """)

    # 11. Knowledge items table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_items (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        service TEXT NOT NULL,
        symptoms TEXT NOT NULL,
        root_cause TEXT NOT NULL,
        fix TEXT NOT NULL,
        approval_status TEXT NOT NULL DEFAULT 'Approved',
        recovery_status TEXT NOT NULL DEFAULT 'Verified',
        created_at TEXT NOT NULL
    )
    """)

    # 12. Audit log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        FOREIGN KEY(incident_id) REFERENCES incidents(id)
    )
    """)

    conn.commit()

    # Seed services if empty
    cursor.execute("SELECT COUNT(*) FROM services")
    if cursor.fetchone()[0] == 0:
        seed_services = [
            ("gateway", "api-gateway", "API Gateway", "Healthy", 90, 170, "Healthy"),
            ("checkout", "checkout-svc", "Checkout Service", "Healthy", 290, 170, "Healthy"),
            ("payments", "payments-svc", "Payments Service", "Healthy", 490, 90, "Healthy"),
            ("inventory", "inventory-svc", "Inventory Service", "Healthy", 490, 250, "Healthy"),
            ("auth", "auth-svc", "Auth Service", "Healthy", 290, 60, "Healthy"),
            ("orders-db", "orders-db", "Orders Database", "Healthy", 690, 90, "Healthy"),
            ("cache", "cache", "Cache Node", "Healthy", 690, 250, "Healthy")
        ]
        now = datetime.now(timezone.utc).isoformat()
        for s in seed_services:
            cursor.execute(
                "INSERT INTO services (id, name, display_name, status, coords_x, coords_y, last_health_check, health_details) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (s[0], s[1], s[2], s[3], s[4], s[5], now, "Service responding within normal latency SLI (<15ms)")
            )

    # Seed past incidents if empty
    cursor.execute("SELECT COUNT(*) FROM incidents")
    if cursor.fetchone()[0] == 0:
        now = datetime.now(timezone.utc)
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d 14:12")
        two_days_ago = (now - timedelta(days=2)).strftime("%Y-%m-%d 09:40")
        four_days_ago = (now - timedelta(days=4)).strftime("%Y-%m-%d 22:05")

        seed_incidents = [
            ("INC-2037", "Checkout 5xx after cache restart", "mem", "checkout", "High", "Resolved", "resolved", yesterday, (now - timedelta(days=1, minutes=-15)).strftime("%Y-%m-%d 14:27"), "Checkout orders temporarily degraded during cache warm-up", 180, 89.2, "Comms", yesterday),
            ("INC-2034", "Inventory pod restarts", "crash", "inventory", "Medium", "Resolved", "resolved", two_days_ago, (now - timedelta(days=2, minutes=-12)).strftime("%Y-%m-%d 09:52"), "Stock availability checks experienced intermittent 503 errors", 90, 94.0, "Comms", two_days_ago),
            ("INC-2031", "Gateway latency from zone shift", "net", "api-gateway", "Medium", "Resolved", "resolved", four_days_ago, (now - timedelta(days=4, minutes=-20)).strftime("%Y-%m-%d 22:25"), "Inter-zone traffic routing induced 420ms gateway p95 latency spikes", 140, 92.5, "Comms", four_days_ago)
        ]

        for inc in seed_incidents:
            cursor.execute("""
                INSERT INTO incidents (id, title, scenario_id, service, severity, status, phase, detected_at, resolved_at, impact_summary, orders_at_risk, checkout_success_pct, active_agent, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, inc)

    # Seed knowledge items if empty
    cursor.execute("SELECT COUNT(*) FROM knowledge_items")
    if cursor.fetchone()[0] == 0:
        seed_kb = [
            ("INC-2037", "Checkout 5xx after cache restart", "cache", "Evictions spike, hit rate drops, DB load up", "Cache restart emptied hot keys, DB load spiked", "Flush and restart cache node", "Approved", "Verified", "Yesterday 14:27"),
            ("INC-2034", "Inventory pod restarts", "inventory", "Pod restarts, 503 on stock checks", "inventory-svc OOM-killed after a config change", "Restart inventory-svc with previous config", "Approved", "Verified", "2 days ago 09:52"),
            ("INC-2031", "Gateway latency from zone shift", "api-gateway", "Slow cross-zone calls, timeouts at the gateway", "Cross-zone latency rose by 400 ms on the payments path", "Shift traffic to the healthy zone", "Approved", "Verified", "4 days ago 22:25")
        ]
        for kb in seed_kb:
            cursor.execute("""
                INSERT INTO knowledge_items (id, title, service, symptoms, root_cause, fix, approval_status, recovery_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, kb)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)

