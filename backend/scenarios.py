from typing import Dict, List, Any

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "deploy": {
        "id": "deploy",
        "name": "Faulty deployment",
        "svc": "payments",
        "svc_name": "payments-svc",
        "sym": "p95 latency up, 5xx on checkout, DB connection waits",
        "desc": "A new release shrinks a resource limit and requests start timing out.",
        "cause": "Deploy v3.8.1 cut the database pool from 40 to 5 connections",
        "fix": "Roll back payments-svc to v3.8.0",
        "sev": "Critical",
        "orders_at_risk": 340,
        "success_rate": 81.2,
        "preconditions": [
            "Target is within simulated payments-svc boundary",
            "Rollback artifact v3.8.0 verified in registry",
            "Canary traffic drain completed safely",
            "Evidence coverage exceeds policy threshold (>= 80%)"
        ],
        "risk_level": "Low",
        "timeout_seconds": 120,
        "rollback_plan": "Restore previous container image tag v3.8.1 if rollback fails health probes",
        "expected_effect": "Database connection waits drop to 0ms; checkout p95 latency recovers under 250ms",
        "evidence": [
            {"type": "Deploy", "source": "deploy-log #2041", "claim": "Deploy v3.8.1 cut the database pool from 40 to 5 connections", "role": "Supports"},
            {"type": "Metric", "source": "metrics/payments-svc", "claim": "Error rate rose from 0.4% to 18.4% two minutes after the change", "role": "Supports"},
            {"type": "Log", "source": "logs/payments-svc", "claim": "Repeated 'timeout waiting for database connection pool' (212 lines)", "role": "Supports"},
            {"type": "Trace", "source": "span 7f3a9e2...", "claim": "Checkout to payments spans take 2.1s; 91% spent waiting on connection acquire", "role": "Supports"},
            {"type": "Commit", "source": "github a41f9c2", "claim": "Config change touching pool size limit committed in the same release window", "role": "Supports"},
            {"type": "Metric", "source": "metrics/orders-db", "claim": "Database CPU is normal at 34%, which rules out datastore hardware saturation", "role": "Conflicts"}
        ],
        "dropped_claim": "Network partition between us-east-1a and us-east-1b (No telemetry evidence found; dropped by Evidence Verifier)",
        "alerts": [
            {"service": "checkout-svc", "name": "p95 latency above 1.5s", "severity": "Critical", "condition": "p95 > 1500ms for 60s"},
            {"service": "checkout-svc", "name": "5xx error rate above 5%", "severity": "Critical", "condition": "error_rate > 5% for 45s"},
            {"service": "payments-svc", "name": "DB pool timeout rate above 10%", "severity": "Critical", "condition": "pool_timeout > 10% for 30s"},
            {"service": "orders-db", "name": "Connection wait above 800ms", "severity": "High", "condition": "wait_time > 800ms for 60s"},
            {"service": "api-gateway", "name": "Upstream 502 Bad Gateway responses", "severity": "High", "condition": "502_count > 50 in 1m"}
        ],
        "correlation_reason": "Grouped 5 alerts: occurred within 90s window, share timeout symptoms, and lie strictly along checkout -> payments -> orders-db dependency chain.",
        "before_metrics": {"p95_latency": "2,840 ms", "error_rate": "18.4%", "saturation": "98%"},
        "after_metrics": {"p95_latency": "212 ms", "error_rate": "0.6%", "saturation": "41%"},
        "verification_checks": [
            "Healthy on 3 consecutive synthetic probes",
            "Error rate below 1.0% (measured 0.6%)",
            "Latency within 20% of baseline (< 250ms, measured 212ms)",
            "No correlated timeout alerts fired for 5 minutes"
        ]
    },
    "db": {
        "id": "db",
        "name": "Database connection failure",
        "svc": "orders-db",
        "svc_name": "orders-db",
        "sym": "Connection refused, write errors, retry storms",
        "desc": "The orders database stops accepting new connections after hitting limits.",
        "cause": "orders-db reached max_connections (500/500) after an unthrottled retry storm",
        "fix": "Restart connection pooler & cycle idle connections",
        "sev": "Critical",
        "orders_at_risk": 420,
        "success_rate": 74.5,
        "preconditions": [
            "orders-db replica is synchronized in read-only standby",
            "Connection pooler drain timeout configured to 30s",
            "Evidence coverage meets threshold"
        ],
        "risk_level": "Medium",
        "timeout_seconds": 120,
        "rollback_plan": "Failover to hot standby replica if pooler restart does not restore connection pool",
        "expected_effect": "Active connections reset to baseline 85; 5xx errors cease",
        "evidence": [
            {"type": "Metric", "source": "metrics/orders-db", "claim": "Active connections spiked to 500 (max allowed limit)", "role": "Supports"},
            {"type": "Log", "source": "logs/orders-db", "claim": "FATAL: remaining connection slots are reserved for non-replication superuser connections", "role": "Supports"},
            {"type": "Trace", "source": "trace c81d9f...", "claim": "Payment worker retry storm generating 4,200 reconnection attempts/sec", "role": "Supports"},
            {"type": "Deploy", "source": "deploy-history", "claim": "No recent schema migrations or database releases in last 48 hours", "role": "Conflicts"}
        ],
        "dropped_claim": "Disk space exhaustion on db volume (Disk free is 64%; dropped by Verifier)",
        "alerts": [
            {"service": "orders-db", "name": "Connection limit reached (100%)", "severity": "Critical", "condition": "conn >= 500"},
            {"service": "payments-svc", "name": "DB write error rate above 20%", "severity": "Critical", "condition": "db_err > 20%"},
            {"service": "checkout-svc", "name": "Payment processing timeout", "severity": "High", "condition": "pay_timeout > 5%"}
        ],
        "correlation_reason": "Grouped 3 alerts: synchronized connection exhaustion across payments and orders-db datastore.",
        "before_metrics": {"p95_latency": "3,400 ms", "error_rate": "24.1%", "saturation": "100%"},
        "after_metrics": {"p95_latency": "180 ms", "error_rate": "0.2%", "saturation": "35%"},
        "verification_checks": [
            "DB active connection count below 150/500",
            "Synthetic checkout write queries succeed within 25ms",
            "Zero rejected client sockets on port 5432",
            "Pooler queue latency normalized below 10ms"
        ]
    },
    "crash": {
        "id": "crash",
        "name": "Service crash",
        "svc": "inventory",
        "svc_name": "inventory-svc",
        "sym": "Pod restarts, 503 on stock checks",
        "desc": "A service is killed repeatedly and stock lookups fail.",
        "cause": "inventory-svc is OOM-killed repeatedly after a memory limit reduction config change",
        "fix": "Restart inventory-svc with previous memory limit (1024MB)",
        "sev": "High",
        "orders_at_risk": 190,
        "success_rate": 86.4,
        "preconditions": [
            "Node group has sufficient free memory capacity (min 2GB)",
            "Config revision v2.4.1 available for rollback"
        ],
        "risk_level": "Low",
        "timeout_seconds": 90,
        "rollback_plan": "Re-apply configmap revision v2.4.1 if container restart fails",
        "expected_effect": "inventory-svc pods stabilize at 0 restarts; stock verification latency < 40ms",
        "evidence": [
            {"type": "Log", "source": "k8s-events/inventory", "claim": "Container inventory-svc terminated with exit code 137 (OOMKilled)", "role": "Supports"},
            {"type": "Metric", "source": "metrics/inventory-svc", "claim": "Memory usage hit 256MB hard limit immediately preceding each crash", "role": "Supports"},
            {"type": "Commit", "source": "github 82cd71b", "claim": "Helm chart updated memory limit from 1Gi to 256Mi 12 minutes ago", "role": "Supports"}
        ],
        "dropped_claim": "Corrupted Redis inventory cache key (Cache query returned valid schema; dropped)",
        "alerts": [
            {"service": "inventory-svc", "name": "Pod CrashLoopBackOff", "severity": "High", "condition": "restarts > 4 in 5m"},
            {"service": "checkout-svc", "name": "Stock reservation 503", "severity": "High", "condition": "stock_503 > 8%"}
        ],
        "correlation_reason": "Grouped 2 alerts: direct cascade from crashing inventory pod to checkout stock reservation failures.",
        "before_metrics": {"p95_latency": "1,920 ms", "error_rate": "14.2%", "saturation": "95%"},
        "after_metrics": {"p95_latency": "145 ms", "error_rate": "0.4%", "saturation": "28%"},
        "verification_checks": [
            "inventory-svc pod running continuously for 120s with 0 restarts",
            "Memory utilization stable at 380MB (< 40% of 1GB limit)",
            "Stock check RPC success rate at 99.8%",
            "Readiness and liveness probes passing consistently"
        ]
    },
    "net": {
        "id": "net",
        "name": "Network latency",
        "svc": "payments",
        "svc_name": "payments-svc",
        "sym": "Slow cross-zone calls, timeouts at the gateway",
        "desc": "Network delay rises between two availability zones.",
        "cause": "Cross-zone latency rose by 400 ms on the payments path due to degraded transit link",
        "fix": "Shift traffic to healthy availability zone (us-east-1a)",
        "sev": "High",
        "orders_at_risk": 210,
        "success_rate": 88.0,
        "preconditions": [
            "Target zone us-east-1a has >= 60% spare capacity",
            "Global load balancer DNS TTL set to 30s"
        ],
        "risk_level": "Low",
        "timeout_seconds": 60,
        "rollback_plan": "Revert DNS weight distribution back to 50/50 round-robin",
        "expected_effect": "Cross-zone latency drops from 420ms to 4ms; gateway timeout eliminated",
        "evidence": [
            {"type": "Metric", "source": "cloudwatch/vpc-rtt", "claim": "RTT between AZ-1b and AZ-1a jumped from 2ms to 418ms", "role": "Supports"},
            {"type": "Trace", "source": "trace b31f82...", "claim": "Gateway-to-payments segment contributes 89% of overall transaction latency", "role": "Supports"}
        ],
        "dropped_claim": "Payments-svc application thread starvation (CPU & thread counts normal; dropped)",
        "alerts": [
            {"service": "api-gateway", "name": "P99 upstream timeout to payments", "severity": "High", "condition": "p99 > 2000ms"},
            {"service": "payments-svc", "name": "Cross-zone packet retransmission spike", "severity": "Medium", "condition": "retrans > 12%"}
        ],
        "correlation_reason": "Grouped 2 alerts: correlated network transit delay isolated to cross-zone payments traffic.",
        "before_metrics": {"p95_latency": "1,450 ms", "error_rate": "8.5%", "saturation": "75%"},
        "after_metrics": {"p95_latency": "195 ms", "error_rate": "0.3%", "saturation": "30%"},
        "verification_checks": [
            "Synthetic RTT probes between gateway and payments < 8ms",
            "Gateway upstream response time below 200ms",
            "AZ-1a instance health 100% with no queue buildup",
            "Zero dropped SYN packets in last 3 minutes"
        ]
    },
    "cpu": {
        "id": "cpu",
        "name": "CPU stress",
        "svc": "checkout",
        "svc_name": "checkout-svc",
        "sym": "CPU above 95%, queueing, slow responses",
        "desc": "A runaway retry loop pins the CPU of a service.",
        "cause": "A runaway retry loop in cart calculation pins checkout-svc CPU at 97%",
        "fix": "Scale checkout-svc to 6 replicas & apply circuit breaker rate-limiting",
        "sev": "Medium",
        "orders_at_risk": 150,
        "success_rate": 91.5,
        "preconditions": [
            "HPA / cluster autoscaler has available node capacity",
            "Rate limiter config validated"
        ],
        "risk_level": "Low",
        "timeout_seconds": 90,
        "rollback_plan": "Scale back down to 3 replicas if CPU fails to drop below 60%",
        "expected_effect": "Per-instance CPU drops to 32%; queue depth clears to 0",
        "evidence": [
            {"type": "Metric", "source": "metrics/checkout-svc", "claim": "CPU utilization pinned at 97% across all active pods", "role": "Supports"},
            {"type": "Log", "source": "logs/checkout-svc", "claim": "Infinite retry loop in calculate_cart_totals without exponential backoff", "role": "Supports"}
        ],
        "dropped_claim": "DDoS attack from external IP block (WAF shows uniform domestic traffic; dropped)",
        "alerts": [
            {"service": "checkout-svc", "name": "Node CPU > 95%", "severity": "High", "condition": "cpu > 95% for 2m"},
            {"service": "api-gateway", "name": "Request queue backlog > 500", "severity": "Medium", "condition": "queue > 500"}
        ],
        "correlation_reason": "Grouped 2 alerts: checkout CPU saturation causing synchronous upstream gateway queueing.",
        "before_metrics": {"p95_latency": "1,100 ms", "error_rate": "5.1%", "saturation": "97%"},
        "after_metrics": {"p95_latency": "160 ms", "error_rate": "0.1%", "saturation": "32%"},
        "verification_checks": [
            "Average CPU across replicas below 45%",
            "P95 response time stabilized under 180ms",
            "HTTP queue length at 0 requests",
            "Circuit breaker state reporting Closed / Normal"
        ]
    },
    "mem": {
        "id": "mem",
        "name": "Memory stress",
        "svc": "cache",
        "svc_name": "cache",
        "sym": "Evictions spike, hit rate drops, DB load up",
        "desc": "A memory leak pushes the cache into constant eviction.",
        "cause": "cache node memory leak drove eviction rate to 4,000 keys/sec",
        "fix": "Flush volatile keys and restart the cache node",
        "sev": "Medium",
        "orders_at_risk": 130,
        "success_rate": 93.2,
        "preconditions": [
            "Target cache node is Redis volatile-lru",
            "Datastore handles fallback read queries safely"
        ],
        "risk_level": "Low",
        "timeout_seconds": 60,
        "rollback_plan": "Restore snapshot backup if redis service fails to rebind port 6379",
        "expected_effect": "Evictions drop to 0/s; cache hit rate recovers to > 92%",
        "evidence": [
            {"type": "Metric", "source": "metrics/cache", "claim": "Eviction rate spiked to 4k/s; hit rate plunged from 94% to 31%", "role": "Supports"},
            {"type": "Log", "source": "logs/cache", "claim": "maxmemory limit 4GB reached; active key eviction cycle taking 85ms", "role": "Supports"}
        ],
        "dropped_claim": "Network interface buffer overflow (NIC metrics completely nominal; dropped)",
        "alerts": [
            {"service": "cache", "name": "Cache eviction rate high", "severity": "Medium", "condition": "evictions > 1000/s"},
            {"service": "orders-db", "name": "Database read IOPS elevated", "severity": "Medium", "condition": "iops > 2000"}
        ],
        "correlation_reason": "Grouped 2 alerts: cache key churn causing downstream database read load spike.",
        "before_metrics": {"p95_latency": "980 ms", "error_rate": "4.8%", "saturation": "99%"},
        "after_metrics": {"p95_latency": "85 ms", "error_rate": "0.05%", "saturation": "22%"},
        "verification_checks": [
            "Eviction rate at 0 keys/sec",
            "Cache hit ratio above 90%",
            "Redis memory usage below 50% of maxmemory",
            "Downstream DB read IOPS returned to baseline"
        ]
    },
    "cert": {
        "id": "cert",
        "name": "TLS Certificate expiration",
        "svc": "gateway",
        "svc_name": "api-gateway",
        "sym": "SSL handshake drops, 525 SSL Handshake Failed errors",
        "desc": "Edge ingress SSL certificate expired without automated renewal.",
        "cause": "api-gateway ingress TLS certificate expired at 00:00 UTC due to cert-manager renewal webhook failure",
        "fix": "Rotate TLS certificate secret and reload edge ingress",
        "sev": "Critical",
        "orders_at_risk": 510,
        "success_rate": 65.0,
        "preconditions": [
            "New signed TLS secret available in Vault/SecretsManager",
            "Gateway ingress reload has zero-downtime graceful drain"
        ],
        "risk_level": "Low",
        "timeout_seconds": 60,
        "rollback_plan": "Revert to fallback wildcard certificate if new certificate verification fails",
        "expected_effect": "SSL handshake success returns to 100%; edge 525 errors drop to 0",
        "evidence": [
            {"type": "Log", "source": "logs/api-gateway", "claim": "SSL_do_handshake() failed: certificate has expired (x509)", "role": "Supports"},
            {"type": "Metric", "source": "metrics/api-gateway", "claim": "TLS handshake failure rate jumped from 0.01% to 35.8%", "role": "Supports"}
        ],
        "dropped_claim": "Upstream origin DNS failure (DNS queries resolved accurately; dropped)",
        "alerts": [
            {"service": "api-gateway", "name": "Edge TLS handshake error rate > 20%", "severity": "Critical", "condition": "tls_fail > 20%"},
            {"service": "checkout-svc", "name": "Ingress drop rate high", "severity": "High", "condition": "drop_rate > 15%"}
        ],
        "correlation_reason": "Grouped 2 alerts: edge TLS expiration directly dropping incoming customer traffic.",
        "before_metrics": {"p95_latency": "2,100 ms", "error_rate": "35.8%", "saturation": "85%"},
        "after_metrics": {"p95_latency": "42 ms", "error_rate": "0.01%", "saturation": "18%"},
        "verification_checks": [
            "Synthetic TLS handshake validity probe returning 200 OK",
            "Certificate expiry window verified valid for > 89 days",
            "Zero SSL handshake failure logs in trailing 2 minutes",
            "Gateway request throughput back to expected baseline"
        ]
    },
    "queue": {
        "id": "queue",
        "name": "Dead-letter queue blockage",
        "svc": "checkout",
        "svc_name": "checkout-svc",
        "sym": "Backlog > 50,000, worker consumer thread blocked",
        "desc": "An unhandled message format stalled asynchronous order dispatchers.",
        "cause": "Malformed JSON payload in cart event stream caused poison pill unhandled exception in message consumer",
        "fix": "Flush poison message to DLQ and scale consumer workers to 4",
        "sev": "High",
        "orders_at_risk": 230,
        "success_rate": 84.1,
        "preconditions": [
            "Dead-letter storage queue initialized",
            "Consumer autoscaling policy enabled"
        ],
        "risk_level": "Low",
        "timeout_seconds": 90,
        "rollback_plan": "Restore message ack state from replica queue if purge fails",
        "expected_effect": "Queue lag clears to zero in 45s; order dispatch latency returns to < 200ms",
        "evidence": [
            {"type": "Log", "source": "logs/checkout-svc", "claim": "SerializationException: unexpected byte 0x00 at offset 12 in order stream", "role": "Supports"},
            {"type": "Metric", "source": "metrics/rabbitmq", "claim": "Consumer queue depth surged to 54,200 unacknowledged messages", "role": "Supports"}
        ],
        "dropped_claim": "RabbitMQ broker node disk saturation (Broker disk at 22% usage; dropped)",
        "alerts": [
            {"service": "checkout-svc", "name": "Queue consumer lag > 10,000 msgs", "severity": "High", "condition": "lag > 10000"},
            {"service": "payments-svc", "name": "Async payment job starvation", "severity": "Medium", "condition": "job_wait > 30s"}
        ],
        "correlation_reason": "Grouped 2 alerts: consumer exception blocking async payment order dispatch.",
        "before_metrics": {"p95_latency": "4,200 ms", "error_rate": "11.2%", "saturation": "94%"},
        "after_metrics": {"p95_latency": "120 ms", "error_rate": "0.05%", "saturation": "25%"},
        "verification_checks": [
            "Queue consumer depth below 100 messages",
            "Consumer message consumption rate > 1,500 msg/sec",
            "Zero unhandled SerializationException events in log stream",
            "End-to-end checkout completion latency < 250ms"
        ]
    },
    "disk": {
        "id": "disk",
        "name": "Database WAL disk pressure",
        "svc": "orders-db",
        "svc_name": "orders-db",
        "sym": "Write IO latency > 1,200ms, WAL disk space at 96%",
        "desc": "Uncheckpointed write-ahead logs fill the orders-db volume.",
        "cause": "orders-db WAL disk space reached 96% due to stalled archival replica snapshot",
        "fix": "Restart WAL archiver and cycle temporary checkpoint logs",
        "sev": "High",
        "orders_at_risk": 290,
        "success_rate": 79.4,
        "preconditions": [
            "Storage subsystem supports online volume expansion",
            "Replica WAL stream is intact"
        ],
        "risk_level": "Medium",
        "timeout_seconds": 120,
        "rollback_plan": "Restore previous checkpoint target if archiver restart halts replication",
        "expected_effect": "Disk utilization drops from 96% to 48%; write IO latency normalizes under 15ms",
        "evidence": [
            {"type": "Metric", "source": "metrics/orders-db", "claim": "WAL volume utilization reached 96.4% of total capacity", "role": "Supports"},
            {"type": "Log", "source": "logs/orders-db", "claim": "WARNING: archive command failed for WAL segment 00000001000000AB00000034", "role": "Supports"}
        ],
        "dropped_claim": "Corrupted database block indexes (Integrity check passed; dropped)",
        "alerts": [
            {"service": "orders-db", "name": "WAL Disk Space Critical (>95%)", "severity": "Critical", "condition": "disk_pct > 95"},
            {"service": "payments-svc", "name": "Order write transaction queueing", "severity": "High", "condition": "tx_wait > 500ms"}
        ],
        "correlation_reason": "Grouped 2 alerts: WAL storage bottleneck stalling payment transaction commitments.",
        "before_metrics": {"p95_latency": "2,950 ms", "error_rate": "15.9%", "saturation": "96%"},
        "after_metrics": {"p95_latency": "140 ms", "error_rate": "0.1%", "saturation": "48%"},
        "verification_checks": [
            "Database WAL volume utilization below 50%",
            "WAL archival lag reduced to 0 segments",
            "Order transaction write commit latency < 20ms",
            "Database engine operating in full Read/Write mode"
        ]
    },
    "dns": {
        "id": "dns",
        "name": "Internal DNS resolution failure",
        "svc": "auth",
        "svc_name": "auth-svc",
        "sym": "NXDOMAIN on auth.cluster.local, login timeouts",
        "desc": "CoreDNS upstream config drift dropped internal cluster domains.",
        "cause": "CoreDNS config drift dropped the upstream resolver stub domain for internal auth services",
        "fix": "Restart CoreDNS deployment and revert stub domain config",
        "sev": "High",
        "orders_at_risk": 260,
        "success_rate": 82.5,
        "preconditions": [
            "Kubernetes CoreDNS ConfigMap backup available",
            "Cluster DNS service IP reachable"
        ],
        "risk_level": "Low",
        "timeout_seconds": 60,
        "rollback_plan": "Re-apply configmap.backup.yaml if DNS resolution does not restore within 30s",
        "expected_effect": "DNS resolution latency drops to < 2ms; auth service discovery restored",
        "evidence": [
            {"type": "Log", "source": "logs/checkout-svc", "claim": "dial tcp: lookup auth-svc.default.svc.cluster.local: no such host", "role": "Supports"},
            {"type": "Metric", "source": "metrics/coredns", "claim": "DNS SERVFAIL response count spiked to 8,400/min", "role": "Supports"}
        ],
        "dropped_claim": "Auth service pod crash (Pods are running and healthy; dropped)",
        "alerts": [
            {"service": "auth-svc", "name": "DNS resolution error rate > 10%", "severity": "High", "condition": "dns_err > 10%"},
            {"service": "checkout-svc", "name": "User authorization timeout", "severity": "High", "condition": "auth_timeout > 5%"}
        ],
        "correlation_reason": "Grouped 2 alerts: cluster DNS failure preventing checkout from reaching auth service.",
        "before_metrics": {"p95_latency": "1,850 ms", "error_rate": "12.8%", "saturation": "88%"},
        "after_metrics": {"p95_latency": "65 ms", "error_rate": "0.02%", "saturation": "20%"},
        "verification_checks": [
            "Cluster DNS resolution for auth-svc succeeding with < 3ms RTT",
            "Zero NXDOMAIN/SERVFAIL queries in trailing 2 minutes",
            "User JWT authorization success rate at 99.9%",
            "CoreDNS pods healthy with 0 restarts"
        ]
    },
    "thread": {
        "id": "thread",
        "name": "Worker thread pool starvation",
        "svc": "payments",
        "svc_name": "payments-svc",
        "sym": "100% active threads, HTTP queue backlog growing",
        "desc": "Synchronous gateway call without timeout pinned payments worker pool.",
        "cause": "Unbounded third-party payment provider call without socket timeout saturated the worker thread pool",
        "fix": "Shift traffic to async payment fallback worker pool and restart",
        "sev": "Medium",
        "orders_at_risk": 170,
        "success_rate": 89.0,
        "preconditions": [
            "Async fallback circuit breaker configured with 1000ms timeout",
            "Healthy replica set running in standby"
        ],
        "risk_level": "Low",
        "timeout_seconds": 60,
        "rollback_plan": "Revert to primary synchronous gateway once external provider latency clears",
        "expected_effect": "Worker thread utilization drops from 100% to 28%; queue depth drops to 0",
        "evidence": [
            {"type": "Metric", "source": "metrics/payments-svc", "claim": "Active worker threads pinned at 200/200 (100% saturation)", "role": "Supports"},
            {"type": "Trace", "source": "trace d41a8c...", "claim": "Outbound third-party credit card gateway call hung for 45s without socket timeout", "role": "Supports"}
        ],
        "dropped_claim": "Database connection pool exhaustion (Database connections nominal at 18; dropped)",
        "alerts": [
            {"service": "payments-svc", "name": "Thread pool saturation 100%", "severity": "High", "condition": "threads >= 200"},
            {"service": "checkout-svc", "name": "Payment processing latency high", "severity": "Medium", "condition": "pay_latency > 3s"}
        ],
        "correlation_reason": "Grouped 2 alerts: thread exhaustion in payments cascading upstream to checkout response times.",
        "before_metrics": {"p95_latency": "1,600 ms", "error_rate": "7.4%", "saturation": "100%"},
        "after_metrics": {"p95_latency": "175 ms", "error_rate": "0.2%", "saturation": "28%"},
        "verification_checks": [
            "Worker thread utilization normalized below 40%",
            "HTTP request queue length at 0",
            "Payment processing p95 response time < 250ms",
            "Zero dropped client requests in last 3 minutes"
        ]
    },
    "drift": {
        "id": "drift",
        "name": "Configuration drift",
        "svc": "inventory",
        "svc_name": "inventory-svc",
        "sym": "Schema mismatch 500s on inventory checks",
        "desc": "An unannounced feature flag enabled unsupported schema fields.",
        "cause": "Dynamic feature flag 'enable_v2_stock_allocation' enabled experimental schema fields unsupported by checkout-svc",
        "fix": "Roll back feature flag enable_v2_stock_allocation to false",
        "sev": "Medium",
        "orders_at_risk": 140,
        "success_rate": 91.0,
        "preconditions": [
            "Feature flag management console API reachable",
            "Flag audit log verified"
        ],
        "risk_level": "Low",
        "timeout_seconds": 30,
        "rollback_plan": "Re-enable flag if contract regression is verified false positive",
        "expected_effect": "JSON serialization errors drop to 0%; inventory verification succeeds instantly",
        "evidence": [
            {"type": "Log", "source": "logs/checkout-svc", "claim": "JsonMappingException: unknown property 'warehouse_sub_zone_id' on StockItem", "role": "Supports"},
            {"type": "Deploy", "source": "launchdarkly/audit", "claim": "Flag 'enable_v2_stock_allocation' toggled ON 8 minutes ago by admin", "role": "Supports"}
        ],
        "dropped_claim": "Inventory database disk corruption (Datastore checksums 100% valid; dropped)",
        "alerts": [
            {"service": "inventory-svc", "name": "Schema deserialization 500 spike", "severity": "Medium", "condition": "500_rate > 5%"},
            {"service": "checkout-svc", "name": "Item reservation failure", "severity": "Medium", "condition": "reserve_fail > 3%"}
        ],
        "correlation_reason": "Grouped 2 alerts: schema incompatibility between inventory-svc v2 payload and checkout-svc.",
        "before_metrics": {"p95_latency": "920 ms", "error_rate": "6.2%", "saturation": "55%"},
        "after_metrics": {"p95_latency": "78 ms", "error_rate": "0.01%", "saturation": "18%"},
        "verification_checks": [
            "Stock reservation RPC 100% success rate",
            "Zero JsonMappingException occurrences in logs",
            "Feature flag state verified as false",
            "Latency within 15% of pre-incident baseline"
        ]
    }
}
