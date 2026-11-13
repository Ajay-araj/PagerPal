import React, { useState } from 'react';
import { Zap, AlertTriangle, X, ShieldAlert, Check, Flame, Server, Cpu, Database, Network } from 'lucide-react';

export function ChaosModal({ onClose, onConfirmRun, isSimBusy, scenarios = [] }) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [step, setStep] = useState(1); // 1: pick, 2: confirm

  const list = scenarios && scenarios.length > 0 ? scenarios : [
    {
      id: 'deploy',
      name: 'Faulty deployment',
      svc: 'payments',
      svc_name: 'payments-svc',
      sym: 'p95 latency up, 5xx on checkout, DB connection pool starvation',
      desc: 'A newly deployed canary shrinks the connection pool from 40 to 5 connections, causing request backpressure.',
      cause: 'Deploy v3.8.1 cut database pool from 40 to 5 connections',
      fix: 'Roll back payments-svc to v3.8.0',
      sev: 'Critical'
    },
    {
      id: 'db',
      name: 'Database connection failure',
      svc: 'orders-db',
      svc_name: 'orders-db',
      sym: 'Connection refused, write errors, retry storms against Postgres',
      desc: 'The orders database hits max_connections threshold after an unthrottled retry wave.',
      cause: 'orders-db reached max_connections after a retry storm',
      fix: 'Restart the connection pooler and cycle idle connections',
      sev: 'Critical'
    },
    {
      id: 'crash',
      name: 'Service crash',
      svc: 'inventory',
      svc_name: 'inventory-svc',
      sym: 'Pod crashlooping, 503 on stock checks, inventory lookup failure',
      desc: 'A memory leak pushes the container into an OOMKill loop.',
      cause: 'inventory-svc is OOM-killed after a config change',
      fix: 'Restart inventory-svc with previous config',
      sev: 'High'
    },
    {
      id: 'net',
      name: 'Network latency',
      svc: 'payments',
      svc_name: 'payments-svc',
      sym: 'Slow cross-zone calls (+400ms), gateway timeout spikes',
      desc: 'Simulated cross-availability zone packet loss and routing degradation.',
      cause: 'Cross-zone latency rose by 400 ms on the payments path',
      fix: 'Shift traffic to the healthy zone (us-east-1a)',
      sev: 'High'
    },
    {
      id: 'cpu',
      name: 'CPU stress',
      svc: 'checkout',
      svc_name: 'checkout-svc',
      sym: 'CPU above 95%, worker thread starvation, slow checkout responses',
      desc: 'A runaway serialization loop pins CPU cores across all pod replicas.',
      cause: 'A retry loop pins checkout-svc CPU at 97%',
      fix: 'Scale checkout-svc to 6 replicas & add circuit breaker',
      sev: 'Medium'
    },
    {
      id: 'mem',
      name: 'Memory stress',
      svc: 'cache',
      svc_name: 'cache',
      sym: 'Key evictions spike, cache hit rate collapses, database IOPS surges',
      desc: 'Unbounded key growth drives Redis into constant evictions.',
      cause: 'cache node memory leak drove evictions to 4k/s',
      fix: 'Flush and restart the cache node',
      sev: 'Medium'
    }
  ];

  const selectedScenario = list[selectedIdx] || list[0];

  if (step === 2 && selectedScenario) {
    return (
      <div className="ov" onClick={(e) => e.target === e.currentTarget && onClose()}>
        <div className="md" style={{ width: 'min(520px, 100%)' }} role="alertdialog">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'rgba(255, 61, 85, 0.15)',
              border: '1px solid var(--red)',
              display: 'grid',
              placeItems: 'center',
              color: 'var(--red)'
            }}>
              <Flame size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '20px', color: '#FFFFFF', margin: 0 }}>
                Inject “{selectedScenario.name}”?
              </h2>
              <span className="sub">Autonomous Chaos Injection Gate</span>
            </div>
          </div>

          <div style={{
            background: 'var(--elevated)',
            padding: '16px',
            borderRadius: '8px',
            border: '1px solid var(--border)',
            margin: '16px 0',
            fontSize: '13.5px',
            lineHeight: 1.6
          }}>
            <p style={{ margin: '0 0 8px' }}>
              Fault injection target: <b className="mono" style={{ color: 'var(--cyan)' }}>{selectedScenario.svc_name}</b>.
            </p>
            <p style={{ margin: '0 0 8px', color: 'var(--text2)' }}>
              <b>Expected Blast Radius:</b> Latency degradation cascading upstream to <span className="mono">checkout-svc</span>.
            </p>
            <p style={{ margin: 0, color: 'var(--green)', fontSize: '12.5px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Check size={14} /> Strict sandbox guarantee: No real production infrastructure is affected. Level 2 remediation will require operator authorization.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button className="btn" onClick={() => setStep(1)}>
              Back
            </button>
            <button
              className="btn p big"
              onClick={() => {
                onClose();
                onConfirmRun(selectedScenario.id);
              }}
              style={{ boxShadow: '0 0 20px rgba(0, 217, 255, 0.4)' }}
            >
              <Zap size={15} /> Confirm & Launch Injection
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ov" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="md" role="dialog" aria-modal="true" aria-label="Chaos Mode">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '18px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap size={22} style={{ color: 'var(--cyan)' }} />
              <h2 style={{ fontSize: '24px', color: '#FFFFFF', margin: 0 }}>
                Chaos Mode <span style={{ fontSize: '15px', color: 'var(--cyan)', fontWeight: 500 }}>({list.length} Scenarios)</span>
              </h2>
            </div>
            <p className="sub" style={{ margin: '6px 0 0' }}>
              Select a reproducible fault scenario. The run is synthetic, deterministic, and strictly safety-controlled.
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h3 style={{ margin: 0 }}>{c.name}</h3>
                  <span className={`b ${c.sev === 'Critical' ? 'red' : c.sev === 'High' ? 'amb' : 'cy'}`} style={{ fontSize: '10.5px' }}>
                    {c.sev}
                  </span>
                </div>
                <p>{c.desc}</p>
                <div style={{ fontSize: '12.5px', marginTop: '8px', paddingTop: '6px', borderTop: '1px solid var(--border)' }}>
                  <div>
                    <span style={{ color: 'var(--text2)' }}>Target:</span>{' '}
                    <span className="mono" style={{ color: 'var(--cyan)' }}>{c.svc_name}</span>
                  </div>
                  <div style={{ color: 'var(--text2)', marginTop: '2px', fontSize: '11.5px' }}>
                    <b style={{ color: 'var(--text)' }}>Symptoms:</b> {c.sym}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div
          style={{
            display: 'flex',
            gap: '12px',
            justifyContent: 'flex-end',
            marginTop: '22px',
            alignItems: 'center',
            flexWrap: 'wrap'
          }}
        >
          {isSimBusy && (
            <span className="b amb" style={{ marginRight: 'auto' }}>
              <AlertTriangle size={13} /> Simulation currently in progress
            </span>
          )}
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn p"
            disabled={selectedIdx === null || isSimBusy}
            onClick={() => setStep(2)}
            style={{ padding: '9px 18px' }}
          >
            <Zap size={15} /> Select Scenario
          </button>
        </div>
      </div>
    </div>
  );
}
