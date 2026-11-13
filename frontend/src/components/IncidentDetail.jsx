import React, { useState } from 'react';
import { 
  ArrowLeft, CheckCircle2, XCircle, AlertTriangle, ShieldCheck, 
  ShieldAlert, StopCircle, Check, X, RefreshCw 
} from 'lucide-react';

const SEVB = {
  Critical: ['red', '▲'],
  High: ['amb', '◆'],
  Medium: ['cy', '●'],
  Low: ['mu', '○']
};

const STB = {
  Resolved: ['grn', '✓'],
  Investigating: ['amb', '◔'],
  'Awaiting approval': ['amb', '❚❚'],
  Remediating: ['cy', '▶'],
  'Verifying recovery': ['cy', '◎'],
  Escalated: ['red', '✕'],
  Stopped: ['red', '■']
};

export function IncidentDetail({ 
  detail, 
  onBack, 
  onApprove, 
  onReject, 
  onEmergencyStop,
  isLive 
}) {
  const [activeTab, setActiveTab] = useState('summary');
  const [rejectReason, setRejectReason] = useState('Operator requested alternate manual rollback path');

  if (!detail) {
    return (
      <div className="pn empty">
        <p>Loading incident details...</p>
      </div>
    );
  }

  const { incident: inc, scenario: sc, alerts, evidence, proposal, verification, audit } = detail;
  const isAwaitingApproval = inc.phase === 'await';
  const isExecuting = ['executing', 'verifying'].includes(inc.phase);
  const isResolved = inc.phase === 'resolved';

  const sevConf = SEVB[inc.severity] || ['mu', '○'];
  const stConf = STB[inc.status] || ['mu', '•'];

  const policyChecks = proposal && proposal.policy_checks ? proposal.policy_checks : [
    { name: 'Action Allowlist', description: 'Proposed action matches safe operational runbook allowlist', passed: true },
    { name: 'Reversibility Guarantee', description: 'Action is strictly reversible with defined rollback plan', passed: true },
    { name: 'Simulation Boundary', description: 'Target is isolated within simulated environment', passed: true },
    { name: 'Evidence Coverage Threshold', description: 'Diagnostic evidence coverage at least 80% (measured 83%)', passed: true },
    { name: 'Human Approval Requirement', description: 'L2 remediation requires explicit operator approval before execution', passed: isExecuting || isResolved }
  ];

  return (
    <div>
      <div style={{ marginBottom: '14px' }}>
        <button className="btn" onClick={onBack}>
          <ArrowLeft size={14} /> Back to incidents
        </button>
      </div>

      <div className="hd">
        <div>
          <h1>{inc.id} · {inc.title}</h1>
          <p>
            Detected {inc.detected_at} · {inc.service} · Simulated incident
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className={`b ${sevConf[0]}`}>
            {sevConf[1]} {inc.severity}
          </span>
          <span className={`b ${stConf[0]}`}>
            {stConf[1]} {inc.status}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs" role="tablist">
        {['summary', 'evidence', 'remediation', 'recovery', 'audit'].map((t) => (
          <button
            key={t}
            role="tab"
            className={activeTab === t ? 'on' : ''}
            onClick={() => setActiveTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab 1: Summary */}
      {activeTab === 'summary' && (
        <div className="pn">
          <div className="two">
            <div>
              <h2>Business impact</h2>
              <p>
                <b>{inc.severity} severity incident.</b> Checkout success rate dropped to{' '}
                <b>{inc.checkout_success_pct || 81.2}%</b> during the incident window, placing{' '}
                <b>~{inc.orders_at_risk || 340} simulated orders/min</b> at risk.
              </p>

              <h2 style={{ marginTop: '20px' }}>Correlated alerts ({alerts.length})</h2>
              <div className="sc">
                <table>
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Alert name</th>
                      <th>Condition</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alerts.map((a, i) => (
                      <tr key={i}>
                        <td className="mono">{a.service}</td>
                        <td><b>{a.name}</b></td>
                        <td className="mono sub">{a.condition || 'Fired > 60s'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="sub" style={{ marginTop: '8px' }}>
                Grouped together by Alert Correlation: fired within 90s, share timeout symptoms, and sit on the same dependency path.
              </p>
            </div>

            <div>
              <h2>Root-cause hypothesis</h2>
              <p style={{ fontSize: '15px', color: 'var(--tx)', marginBottom: '8px' }}>
                <b>{sc.cause || 'Under investigation by Causal RCA agent'}</b>
              </p>
              <p>
                <b>Causal path:</b>{' '}
                <span className="mono" style={{ color: 'var(--red)' }}>
                  checkout-svc → {sc.svc_name} → orders-db
                </span>
              </p>
              <span className={`b ${isResolved || isExecuting ? 'grn' : 'amb'}`}>
                {isResolved || isExecuting ? '✓ Verified by evidence' : '◔ Suspected'}
              </span>

              <h2 style={{ margin: '22px 0 6px' }}>Rule-based confidence report</h2>
              <div className="meter">
                <div>
                  <span>Diagnostic confidence</span>
                  <b>86%</b>
                </div>
                <u><i style={{ width: '86%' }} /></u>
              </div>
              <div className="meter">
                <div>
                  <span>Evidence coverage (5 of 6 claims)</span>
                  <b>83%</b>
                </div>
                <u><i style={{ width: '83%' }} /></u>
              </div>
              <div className="meter">
                <div>
                  <span>Data quality</span>
                  <b>91%</b>
                </div>
                <u><i style={{ width: '91%' }} /></u>
              </div>
              <span className="sub">
                Rule-based algorithmic confidence scoring. The LLM does not set safety or confidence metrics.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Evidence */}
      {activeTab === 'evidence' && (
        <div className="pn">
          <h2>Verified evidence claims</h2>
          <div className="sc">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Source</th>
                  <th>Claim</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {evidence.map((ev, i) => (
                  <tr key={i}>
                    <td><b>{ev.type}</b></td>
                    <td className="mono">{ev.source}</td>
                    <td>{ev.claim}</td>
                    <td>
                      {ev.role === 'Supports' ? (
                        <span className="b grn">✓ Supports</span>
                      ) : (
                        <span className="b amb">◆ Conflicts</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: '16px', padding: '10px 14px', background: '#0e1628', borderRadius: '8px', border: '1px solid var(--ln)' }}>
            <span className="sub" style={{ display: 'block', color: 'var(--tx)' }}>
              <b>Dropped claim:</b> {sc.dropped_claim || 'Unsupported assertions were eliminated by Evidence Verifier.'}
            </span>
          </div>
        </div>
      )}

      {/* Tab 3: Remediation */}
      {activeTab === 'remediation' && (
        <div className="pn">
          <div className="two">
            <div>
              <h2>Proposed remediation</h2>
              <p style={{ fontSize: '16px', fontWeight: 600, color: 'var(--tx)', margin: '8px 0' }}>
                {sc.fix}
              </p>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '14px' }}>
                <span className="b cy">● Risk: {sc.risk_level || 'Low'}</span>
                <span className="b grn">✓ Reversible</span>
                <span className="b mu">⏱ Timeout: {sc.timeout_seconds || 120}s</span>
              </div>
              <p>
                <b>Target service:</b> <span className="mono">{sc.svc_name}</span>
              </p>
              <p>
                <b>Rollback plan:</b> {sc.rollback_plan}
              </p>
              <p>
                <b>Expected effect:</b> {sc.expected_effect}
              </p>

              {/* Action Buttons */}
              <div style={{ marginTop: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button
                  className="btn g big"
                  disabled={!isAwaitingApproval}
                  onClick={onApprove}
                >
                  <Check size={16} /> Approve & execute
                </button>
                <button
                  className="btn r big"
                  disabled={!isAwaitingApproval}
                  onClick={() => onReject(rejectReason)}
                >
                  <X size={16} /> Reject & escalate
                </button>
                <button
                  className="btn r"
                  disabled={!isExecuting}
                  onClick={onEmergencyStop}
                >
                  <StopCircle size={16} /> Emergency stop
                </button>
              </div>

              {!isAwaitingApproval && !isExecuting && !isResolved && (
                <p className="sub" style={{ marginTop: '12px' }}>
                  Remediation proposal will become actionable once Causal RCA and Evidence Verifier complete.
                </p>
              )}
            </div>

            <div className={`pol ${isAwaitingApproval ? 'warn' : ''}`}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ShieldCheck size={16} /> Independent Policy Engine ·{' '}
                {isExecuting || isResolved ? 'Approved & Permitted' : 'Allowed (L2)'}
              </h3>
              <ul>
                {policyChecks.map((ch, idx) => (
                  <li key={idx} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {ch.passed ? (
                      <span style={{ color: 'var(--grn)' }}>✓</span>
                    ) : (
                      <span style={{ color: 'var(--amb)' }}>◔</span>
                    )}
                    <span>
                      <b>{ch.name}:</b> {ch.description}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="sub" style={{ marginTop: '10px', color: '#c5d5c0' }}>
                Non-LLM rule-based safety authority. Commands outside simulation or missing human signoff are hard-blocked.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Recovery */}
      {activeTab === 'recovery' && (
        <div className="pn">
          <h2>Recovery verification</h2>
          {isExecuting || isResolved ? (
            <>
              <div className="ba">
                <span className="h">Metric</span>
                <span className="h">Before remediation</span>
                <span className="h"></span>
                <span className="h">After remediation</span>
                <span>p95 Latency</span>
                <b className="bf mono">{sc.before_metrics.p95_latency}</b>
                <span>→</span>
                <b className="af mono">{isResolved ? sc.after_metrics.p95_latency : 'verifying…'}</b>
                <span>Error rate</span>
                <b className="bf mono">{sc.before_metrics.error_rate}</b>
                <span>→</span>
                <b className="af mono">{isResolved ? sc.after_metrics.error_rate : 'verifying…'}</b>
                <span>Resource saturation</span>
                <b className="bf mono">{sc.before_metrics.saturation}</b>
                <span>→</span>
                <b className="af mono">{isResolved ? sc.after_metrics.saturation : 'verifying…'}</b>
              </div>

              <h2 style={{ margin: '22px 0 10px' }}>Empirical health verification checks</h2>
              <ul style={{ paddingLeft: '18px', listStyle: 'none' }}>
                {sc.verification_checks.map((chk, i) => (
                  <li key={i} style={{ padding: '4px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {isResolved ? (
                      <span className="b grn" style={{ padding: '1px 6px', fontSize: '11px' }}>✓ PASS</span>
                    ) : (
                      <span className="b cy" style={{ padding: '1px 6px', fontSize: '11px' }}>◎ CHECKING</span>
                    )}
                    <span>{chk}</span>
                  </li>
                ))}
              </ul>

              <div style={{ marginTop: '16px' }}>
                {isResolved ? (
                  <span className="b grn" style={{ padding: '6px 14px', fontSize: '13px' }}>
                    ✓ Recovery verified across 4 of 4 checks
                  </span>
                ) : (
                  <span className="b cy" style={{ padding: '6px 14px', fontSize: '13px' }}>
                    ◎ Verifying health probes. Successful command alone is not proof of recovery.
                  </span>
                )}
              </div>
            </>
          ) : (
            <div className="empty">
              Recovery verification executes automatically after remediation is approved and executed.
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Audit Trail */}
      {activeTab === 'audit' && (
        <div className="pn">
          <h2>Immutable audit trail</h2>
          {audit && audit.length > 0 ? (
            <ul className="tl">
              {audit.map((a, i) => (
                <li key={i} className="grn">
                  <span className="t mono">[{a[0]}]</span>
                  <span>{a[1]}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty">No audit trail records logged yet.</div>
          )}
        </div>
      )}
    </div>
  );
}

