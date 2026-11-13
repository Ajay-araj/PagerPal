from typing import Dict, Any, List

FAULT_PROFILES: Dict[str, Dict[str, Any]] = {
    "faulty_deployment": {
        "name": "Faulty deployment",
        "default_service": "payments",
        "root_cause_template": "Deploy {version} to {service_name} cut connection pool limits from 40 to 5, inducing resource exhaustion timeouts",
        "recommended_action": "rollback_deployment",
        "fix_description_template": "Roll back {service_name} to {previous_version}",
        "severity": "Critical",
        "has_deployment": True,
        "primary_symptom": "p95 latency spike, 5xx rate elevation, resource pool wait timeouts",
        "metric_impact": {
            "p95_latency_mult": 28.0,
            "error_rate_spike": 18.4,
            "saturation_pct": 98.0
        },
        "log_signatures": [
            "timeout waiting for database connection pool: acquired 0/5",
            "HTTP 504 Gateway Timeout while awaiting downstream {service_name}",
            "Connection acquire timeout after 2500ms in thread worker"
        ]
    },
    "database_connection_failure": {
        "name": "Database connection failure",
        "default_service": "orders-db",
        "root_cause_template": "{service_name} reached max_connections (500/500) following an unthrottled client retry storm",
        "recommended_action": "reset_connection_pooler",
        "fix_description_template": "Restart connection pooler on {service_name} & cycle idle connections",
        "severity": "Critical",
        "has_deployment": False,
        "primary_symptom": "Connection refused, socket write errors, client retry storms",
        "metric_impact": {
            "p95_latency_mult": 35.0,
            "error_rate_spike": 24.1,
            "saturation_pct": 100.0
        },
        "log_signatures": [
            "FATAL: remaining connection slots are reserved for non-replication superuser connections",
            "could not connect to server: Connection refused on port 5432",
            "server closed the connection unexpectedly (client connection limit reached)"
        ]
    },
    "service_crash": {
        "name": "Service crash",
        "default_service": "inventory",
        "root_cause_template": "{service_name} pod OOM-killed (exit code 137) due to memory limit reduction in recent pod spec",
        "recommended_action": "restart_service_container",
        "fix_description_template": "Restart {service_name} with previous memory limit configuration",
        "severity": "High",
        "has_deployment": True,
        "primary_symptom": "Pod CrashLoopBackOff, 503 Service Unavailable on stock/data checks",
        "metric_impact": {
            "p95_latency_mult": 18.0,
            "error_rate_spike": 14.2,
            "saturation_pct": 95.0
        },
        "log_signatures": [
            "Container {service_name} terminated with exit code 137 (OOMKilled)",
            "readiness probe failed: connection refused on port 8080",
            "Back-off restarting failed container {service_name} in pod"
        ]
    },
    "network_latency": {
        "name": "Network latency",
        "default_service": "payments",
        "root_cause_template": "Degraded transit link between availability zones added +400ms RTT on cross-zone {service_name} traffic",
        "recommended_action": "shift_traffic_zone",
        "fix_description_template": "Shift traffic to healthy availability zone for {service_name}",
        "severity": "High",
        "has_deployment": False,
        "primary_symptom": "Elevated cross-zone RTT, TCP retransmission bursts, gateway timeouts",
        "metric_impact": {
            "p95_latency_mult": 16.0,
            "error_rate_spike": 8.5,
            "saturation_pct": 75.0
        },
        "log_signatures": [
            "upstream request timed out after 3000ms connecting to {service_name}",
            "TCP retransmission rate rose to 14.2% across AZ boundary",
            "client connection dropped during chunked transfer from {service_name}"
        ]
    },
    "cpu_stress": {
        "name": "CPU stress",
        "default_service": "checkout",
        "root_cause_template": "Runaway algorithmic loop in {service_name} calculation logic pinned CPU at 97%",
        "recommended_action": "scale_service_replicas",
        "fix_description_template": "Scale {service_name} to 6 replicas and enable rate-limiting filter",
        "severity": "Medium",
        "has_deployment": False,
        "primary_symptom": "CPU utilization above 95%, worker thread queuing, elevated response times",
        "metric_impact": {
            "p95_latency_mult": 12.0,
            "error_rate_spike": 5.1,
            "saturation_pct": 97.0
        },
        "log_signatures": [
            "CPU utilization threshold exceeded: 97.4% over 120s window",
            "worker queue backlog reached 500 items in {service_name}",
            "event loop lag 1420ms detected in {service_name}"
        ]
    },
    "memory_stress": {
        "name": "Memory stress",
        "default_service": "cache",
        "root_cause_template": "Memory leak in {service_name} drove volatile key eviction rate to 4,000 keys/sec, dropping hit rate to 31%",
        "recommended_action": "flush_and_restart_cache",
        "fix_description_template": "Flush volatile keys and restart {service_name}",
        "severity": "Medium",
        "has_deployment": False,
        "primary_symptom": "Eviction spike, cache hit rate plunge, elevated read load on backend stores",
        "metric_impact": {
            "p95_latency_mult": 10.0,
            "error_rate_spike": 4.8,
            "saturation_pct": 99.0
        },
        "log_signatures": [
            "maxmemory threshold 4096MB reached in {service_name}; eviction active",
            "cache hit ratio dropped from 94% to 31% over 5m window",
            "eviction rate spiked to 4,200 keys/sec in {service_name}"
        ]
    }
}

