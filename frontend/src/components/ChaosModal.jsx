import React, { useState } from 'react';
import { Zap, AlertTriangle, X } from 'lucide-react';

export function ChaosModal({ onClose, onConfirmRun, isSimBusy, scenarios = [] }) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [step, setStep] = useState(1); // 1: pick, 2: confirm

  const list = scenarios && scenarios.length > 0 ? scenarios : [
    {
      id: 'deploy',
      name: 'Faulty deployment',
      svc: 'payments',
      svc_name: 'payments-svc',
      sym: 'p95 latency up, 5xx on checkout, DB connection waits',
      desc: 'A new release shrinks a resource limit and requests start timing out.',
      cause: 'Deploy v3.8.1 cut the database pool from 40 to 5 connections',
      fix: 'Roll back payments-svc to v3.8.0',
      sev: 'Critical'
    },
    {
      id: 'db',
      name: 'Database connection failure',
      svc: 'orders-db',
      svc_name: 'orders-db',
      sym: 'Connection refused, write errors, retry storms',
      desc: 'The orders database stops accepting new connections after hitting limits.',
      cause: 'orders-db reached max_connections after a retry storm',
      fix: 'Restart the connection pooler and cycle idle connections',
      sev: 'Critical'
    },
    {
      id: 'crash',
      name: 'Service crash',
      svc: 'inventory',
      svc_name: 'inventory-svc',
      sym: 'Pod restarts, 503 on stock checks',
      desc: 'A service is killed repeatedly and stock lookups fail.',
      cause: 'inventory-svc is OOM-killed after a config change',
      fix: 'Restart inventory-svc with previous config',
      sev: 'High'
    },
    {
      id: 'net',
      name: 'Network latency',
      svc: 'payments',
      svc_name: 'payments-svc',
      sym: 'Slow cross-zone calls, timeouts at the gateway',
      desc: 'Network delay rises between two availability zones.',
      cause: 'Cross-zone latency rose by 400 ms on the payments path',
      fix: 'Shift traffic to the healthy zone (us-east-1a)',
      sev: 'High'
    },
    {
      id: 'cpu',
      name: 'CPU stress',
      svc: 'checkout',
      svc_name: 'checkout-svc',
      sym: 'CPU above 95%, queueing, slow responses',
      desc: 'A runaway retry loop pins the CPU of a service.',
      cause: 'A retry loop pins checkout-svc CPU at 97%',
      fix: 'Scale checkout-svc to 6 replicas & add circuit breaker',
      sev: 'Medium'
    },
    {
      id: 'mem',
      name: 'Memory stress',
      svc: 'cache',
      svc_name: 'cache',
      sym: 'Evictions spike, hit rate drops, DB load up',
      desc: 'A memory leak pushes the cache into constant eviction.',
      cause: 'cache node memory leak drove evictions to 4k/s',
      fix: 'Flush and restart the cache node',
      sev: 'Medium'
    }
  ];

  const selectedScenario = list[selectedIdx] || list[0];

  if (step === 2 && selectedScenario) {
    return (
      <div className="ov" onClick={(e) => e.target === e.currentTarget && onClose()}>
        <div className="md" style={{ width: 'min(480px, 100%)' }} role="alertdialog">
          <h2 style={{ fontSize: '20px', color: 'var(--tx)' }}>
            Run “{selectedScenario.name}”?
          </h2>
          <p style={{ margin: '12px 0 16px', lineHeight: 1.6 }}>
            This injects simulated faults into <b className="mono">{selectedScenario.svc_name}</b>.
            Nothing real is touched, and any remediation will strictly require your approval before running.
          </p>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <button className="btn" onClick={() => setStep(1)}>
              Back
            </button>
            <button
              className="btn p"
              onClick={() => {
                onClose();
                onConfirmRun(selectedScenario.id);
              }}
            >
              <Zap size={14} /> Confirm and run
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ov" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="md" role="dialog" aria-modal="true" aria-label="Chaos Mode">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
          <div>
            <h2 style={{ fontSize: '22px' }}>Chaos Mode ({list.length} Scenarios)</h2>
            <p className="sub" style={{ margin: '4px 0 0' }}>
              Pick a fault scenario to inject. The run is simulated, reproducible, and safety-gated.
            </p>
          </div>
          <button className="btn" onClick={onClose} style={{ padding: '6px' }}>
            <X size={16} />
          </button>
        </div>

        <div className="cards" style={{ maxHeight: '55vh', overflowY: 'auto', paddingRight: '4px' }}>
          {list.map((c, i) => {
            const isSelected = selectedIdx === i;
            return (
              <button
                key={c.id}
                className="opt"
                aria-pressed={isSelected}
                onClick={() => setSelectedIdx(i)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3>{c.name}</h3>
                  <span className={`b ${c.sev === 'Critical' ? 'red' : c.sev === 'High' ? 'amb' : 'cy'}`} style={{ fontSize: '10px' }}>
                    {c.sev}
                  </span>
                </div>
                <p>{c.desc}</p>
                <p>
                  <b>Affects:</b> <span className="mono">{c.svc_name}</span>
                </p>
                <p style={{ fontSize: '12px' }}>
                  <b>Symptoms:</b> {c.sym}
                </p>
              </button>
            );
          })}
        </div>

        <div
          style={{
            display: 'flex',
            gap: '10px',
            justifyContent: 'flex-end',
            marginTop: '20px',
            alignItems: 'center',
            flexWrap: 'wrap'
          }}
        >
          {isSimBusy && (
            <span className="b amb" style={{ marginRight: 'auto' }}>
              <AlertTriangle size={13} /> A simulation is already running
            </span>
          )}
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn p"
            disabled={selectedIdx === null || isSimBusy}
            onClick={() => setStep(2)}
          >
            <Zap size={14} /> Run simulation
          </button>
        </div>
      </div>
    </div>
  );
}
