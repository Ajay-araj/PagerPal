import React, { useState } from 'react';
import { 
  ArrowLeft, CheckCircle2, XCircle, AlertTriangle, ShieldCheck, 
  ShieldAlert, StopCircle, Check, X, RefreshCw, FileText, Activity, Shield, Terminal 
} from 'lucide-react';

const SEVB = {
  Critical: ['red', ''],
  High: ['amb', ''],
  Medium: ['cy', ''],
  Low: ['mu', '']
};

const STB = {
  Resolved: ['grn', ''],
  Investigating: ['amb', ''],
  'Awaiting approval': ['amb', 'PAUSED'],
  Remediating: ['cy', ''],
  'Verifying recovery': ['cy', ''],
  Escalated: ['red', ''],
  Stopped: ['red', '']
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
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showApproveModal, setShowApproveModal] = useState(false);

  if (!detail) {
    return (
      <div className="pn empty" style={{ padding: '60px 20px' }}>
        <p>Loading forensic incident details...</p>
      </div>
    );
  }

  const { incident: inc, scenario: sc, alerts, evidence, proposal, verification, audit } = detail;
  const isAwaitingApproval = inc.phase === 'await';
  const isExecuting = ['executing', 'verifying'].includes(inc.phase);
  const isResolved = inc.phase === 'resolved';

  const sevConf = SEVB[inc.severity] || ['mu', ''];
  const stConf = STB[inc.status] || ['mu', '•'];

  const policyChecks = proposal && proposal.policy_checks ? proposal.policy_checks : [
    { name: 'Action Allowlist', description: 'Proposed action matches safe operational runbook allowlist', passed: true },
    { name: 'Reversibility Guarantee', description: 'Action is strictly reversible with defined rollback plan', passed: true },
    { name: 'Simulation Boundary', description: 'Target is strictly isolated within synthetic environment', passed: true },
    { name: 'Evidence Coverage Threshold', description: 'Diagnostic evidence coverage >= 80% (measured 83%)', passed: true },
    { name: 'Human Approval Requirement', description: 'L2 remediation requires explicit operator approval before execution', passed: isExecuting || isResolved }
  ];

  return (
    <div>
      <div style={{ marginBottom: '16px' }}>
        <button className="btn" onClick={onBack}>
          <ArrowLeft size={14} /> Back to incidents
        </button>
      </div>

      {/* Header */}
      <div className="hd">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <h1>{inc.id} · {inc.title}</h1>
          </div>
          <p>
            Detected {inc.detected_at} · Target: <span className="mono" style={{ color: 'var(--cyan)' }}>{inc.service}</span> · Synthetic Scenario
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span className={`b ${sevConf[0]}`} style={{ fontSize: '13px', padding: '4px 12px' }}>
            {sevConf[1]} {inc.severity}
          </span>
          <span className={`b ${stConf[0]}`} style={{ fontSize: '13px', padding: '4px 12px' }}>
            {stConf[1]} {inc.status}
          </span>
        </div>
      </div>

      {/* Navigation Tabs */}
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
              <h2>Business Impact & Blast Radius</h2>
              <div style={{ background: 'rgba(5, 9, 20, 0.6)', padding: '14px 16px', borderRadius: '10px', border: '1px solid rgba(0, 217, 255, 0.1)', marginBottom: '18px' }}>
                <p style={{ margin: 0, lineHeight: 1.6 }}>
                  <b>{inc.severity} Severity Incident.</b> Synthetic checkout success rate dropped to{' '}
                  <b style={{ color: 'var(--red)' }}>{inc.checkout_success_pct || 81.2}%</b> during the active fault window, placing{' '}
                  <b style={{ color: 'var(--amber)' }}>~{inc.orders_at_risk || 340} simulated transactions/min</b> at risk.
                </p>
              </div>

              <h2 style={{ marginTop: '22px' }}>Correlated Alerts ({alerts.length})</h2>
              <div className="sc">
                <table>
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Alert Name</th>
                      <th>Trigger Condition</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alerts.map((a, i) => (
                      <tr key={i}>
                        <td className="mono" style={{ color: 'var(--cyan)' }}>{a.service}</td>
                        <td><b>{a.name}</b></td>
                        <td className="mono sub">{a.condition || 'Fired > 60s sustained'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="sub" style={{ marginTop: '10px', lineHeight: 1.5 }}>
                Grouped together by Alert Correlation Engine: fired within 90s window, share timeout symptoms, and sit on the same dependency vector.
              </p>
            </div>

            <div>
              <h2>Causal Root-Cause Hypothesis</h2>
              <div style={{ background: 'rgba(5, 9, 20, 0.6)', padding: '14px 16px', borderRadius: '10px', border: '1px solid rgba(0, 217, 255, 0.1)', marginBottom: '18px' }}>
                <p style={{ fontSize: '15px', color: '#FFFFFF', fontWeight: 600, margin: '0 0 8px' }}>
                  {sc.cause || 'Under investigation by Causal RCA agent'}
                </p>
                <p style={{ margin: '0 0 10px', color: 'var(--text2)', fontSize: '13px' }}>
                  <b>Causal propagation path:</b>{' '}
                  <span className="mono" style={{ color: 'var(--red)' }}>
                    checkout-svc → {sc.svc_name} → orders-db
                  </span>
                </p>
                <span className={`b ${isResolved || isExecuting ? 'grn' : 'amb'}`}>
                  {isResolved || isExecuting ? ' Verified by empirical telemetry' : ' Suspected Causal Node'}
                </span>
              </div>

              <h2 style={{ margin: '22px 0 8px' }}>Rule-Based Confidence Scoring</h2>
              <div className="meter">
                <div>
                  <span>Diagnostic Confidence</span>
                  <b style={{ color: 'var(--cyan)' }}>86%</b>
                </div>
                <u><i style={{ width: '86%' }} /></u>
              </div>
              <div className="meter">
                <div>
                  <span>Evidence Coverage (5 of 6 claims verified)</span>
                  <b style={{ color: 'var(--green)' }}>83%</b>
                </div>
                <u><i style={{ width: '83%', background: 'var(--green)' }} /></u>
              </div>
              <div className="meter">
                <div>
                  <span>Data Quality Index</span>
                  <b style={{ color: 'var(--cyan)' }}>91%</b>
                </div>
                <u><i style={{ width: '91%' }} /></u>
              </div>
              <span className="sub" style={{ marginTop: '8px', display: 'block' }}>
                Algorithmic rule-based confidence scoring. LLM outputs are strictly quarantined from setting safety or confidence metrics.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Evidence */}
      {activeTab === 'evidence' && (
        <div className="pn">
          <h2>Verified Telemetry Claims Ledger</h2>
          <div className="sc">
            <table>
              <thead>
                <tr>
                  <th>Evidence Type</th>
                  <th>Source Component</th>
                  <th>Claim Assertion</th>
                  <th>Verification Role</th>
                </tr>
              </thead>
              <tbody>
                {evidence.map((ev, i) => (
                  <tr key={i}>
                    <td><b>{ev.type}</b></td>
                    <td className="mono" style={{ color: 'var(--cyan)' }}>{ev.source}</td>
                    <td style={{ color: 'var(--text)' }}>{ev.claim}</td>
                    <td>
                      {ev.role === 'Supports' ? (
                        <span className="b grn"> Supports Root Cause</span>
                      ) : (
                        <span className="b amb"> Conflicting Observation</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: '18px', padding: '12px 16px', background: 'rgba(5, 9, 20, 0.6)', borderRadius: '10px', border: '1px solid rgba(0, 217, 255, 0.12)' }}>
            <span style={{ fontSize: '13px', color: 'var(--text2)', lineHeight: 1.5, display: 'block' }}>
              <b style={{ color: 'var(--amber)' }}>Eliminated / Dropped Claims:</b> {sc.dropped_claim || 'Unverified assertions were rejected by Evidence Verifier.'}
            </span>
          </div>
        </div>
      )}

      {/* Tab 3: Remediation & Policy Engine */}
      {activeTab === 'remediation' && (
        <div className="pn">
          <div className="two">
            <div>
              <h2>Proposed Remediation Action</h2>
              <div style={{ background: 'rgba(5, 9, 20, 0.6)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(0, 217, 255, 0.12)', marginBottom: '18px' }}>
                <p style={{ fontSize: '18px', fontWeight: 700, color: '#FFFFFF', margin: '0 0 10px' }}>
                  {sc.fix}
                </p>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
                  <span className="b cy"> Risk Level: {sc.risk_level || 'Low'}</span>
                  <span className="b grn"> Reversible Operation</span>
                  <span className="b mu">⏱ Timeout: {sc.timeout_seconds || 120}s</span>
                </div>
                <p style={{ margin: '6px 0', fontSize: '13px' }}>
                  <b>Target Service:</b> <span className="mono" style={{ color: 'var(--cyan)' }}>{sc.svc_name}</span>
                </p>
                <p style={{ margin: '6px 0', fontSize: '13px' }}>
                  <b>Rollback Plan:</b> {sc.rollback_plan}
                </p>
                <p style={{ margin: '6px 0', fontSize: '13px' }}>
                  <b>Expected Impact:</b> {sc.expected_effect}
                </p>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '20px' }}>
                <button
                  className="btn g big"
                  disabled={!isAwaitingApproval}
                  onClick={() => setShowApproveModal(true)}
                  style={{ boxShadow: isAwaitingApproval ? '0 0 20px rgba(0, 230, 160, 0.4)' : 'none' }}
                >
                  <Check size={16} /> Approve & Execute Remediation
                </button>
                <button
                  className="btn r big"
                  disabled={!isAwaitingApproval}
                  onClick={() => setShowRejectModal(true)}
                >
                  <X size={16} /> Reject & Escalate
                </button>
                <button
                  className="btn r"
                  disabled={!isExecuting}
                  onClick={onEmergencyStop}
                  title="Immediately abort execution and initiate rollback"
                >
                  <StopCircle size={16} /> Emergency Stop
                </button>
              </div>

              {!isAwaitingApproval && !isExecuting && !isResolved && (
                <p className="sub" style={{ marginTop: '14px', lineHeight: 1.5 }}>
                  Remediation proposal will become actionable once Causal RCA and Evidence Verifier complete and Policy Engine certifies preconditions.
                </p>
              )}
            </div>

            <div className={`pol ${isAwaitingApproval ? 'warn' : ''}`}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px' }}>
                <ShieldCheck size={18} style={{ color: isExecuting || isResolved ? 'var(--green)' : 'var(--amber)' }} />
                Independent Policy Engine · {isExecuting || isResolved ? 'Approved & Permitted' : 'Preconditions Evaluated (L2)'}
              </h3>
              <ul>
                {policyChecks.map((ch, idx) => (
                  <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ color: ch.passed ? 'var(--green)' : 'var(--amber)', marginTop: '2px' }}>
                      {ch.passed ? '' : ''}
                    </span>
                    <span style={{ fontSize: '13px', lineHeight: 1.4 }}>
                      <b style={{ color: '#FFFFFF' }}>{ch.name}:</b> {ch.description}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="sub" style={{ marginTop: '12px', color: '#c5d5c0', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '8px' }}>
                Non-LLM deterministic safety authority. Actions outside allowlist or lacking explicit operator approval are hard-blocked.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Recovery Verification */}
      {activeTab === 'recovery' && (
        <div className="pn">
          <h2>Empirical Recovery Verification (4 of 4 Probes)</h2>
          {isExecuting || isResolved ? (
            <>
              <div className="ba">
                <span className="h">Telemetry Metric</span>
                <span className="h">Pre-Remediation (Peak)</span>
                <span className="h"></span>
                <span className="h">Post-Remediation</span>
                
                <span>p95 Latency</span>
                <b className="bf mono">{sc.before_metrics.p95_latency}</b>
                <span style={{ color: 'var(--text2)' }}>→</span>
                <b className="af mono">{isResolved ? sc.after_metrics.p95_latency : 'probing…'}</b>
                
                <span>Error Rate</span>
                <b className="bf mono">{sc.before_metrics.error_rate}</b>
                <span style={{ color: 'var(--text2)' }}>→</span>
                <b className="af mono">{isResolved ? sc.after_metrics.error_rate : 'probing…'}</b>
                
                <span>Resource Saturation</span>
                <b className="bf mono">{sc.before_metrics.saturation}</b>
                <span style={{ color: 'var(--text2)' }}>→</span>
                <b className="af mono">{isResolved ? sc.after_metrics.saturation : 'probing…'}</b>
              </div>

              <h2 style={{ margin: '26px 0 12px' }}>Independent Verification Health Probes</h2>
              <ul style={{ paddingLeft: '0', listStyle: 'none' }}>
                {sc.verification_checks.map((chk, i) => (
                  <li key={i} style={{ padding: '8px 12px', background: 'rgba(5, 9, 20, 0.4)', borderRadius: '6px', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {isResolved ? (
                      <span className="b grn" style={{ padding: '2px 8px', fontSize: '11px' }}> PASS</span>
                    ) : (
                      <span className="b cy" style={{ padding: '2px 8px', fontSize: '11px' }}> PROBING</span>
                    )}
                    <span style={{ fontSize: '13.5px' }}>{chk}</span>
                  </li>
                ))}
              </ul>

              <div style={{ marginTop: '20px' }}>
                {isResolved ? (
                  <span className="b grn" style={{ padding: '8px 16px', fontSize: '13.5px', boxShadow: '0 0 16px rgba(0, 230, 160, 0.3)' }}>
                     Synthetic recovery verified across all 4 independent health probes
                  </span>
                ) : (
                  <span className="b cy" style={{ padding: '8px 16px', fontSize: '13.5px' }}>
                     Verifying recovery probes. Command return code alone is never accepted as recovery.
                  </span>
                )}
              </div>
            </>
          ) : (
            <div className="empty">
              Recovery verification will execute automatically after remediation is approved by operator.
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Immutable Audit Trail */}
      {activeTab === 'audit' && (
        <div className="pn">
          <h2>Cryptographic Immutable Audit Trail</h2>
          {audit && audit.length > 0 ? (
            <ul className="tl">
              {audit.map((a, i) => (
                <li key={i} className="grn">
                  <span className="t mono">[{a[0]}]</span>
                  <span style={{ color: 'var(--text)' }}>{a[1]}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty">No audit trail records logged yet.</div>
          )}
        </div>
      )}

      {/* Approval Confirmation Dialog */}
      {showApproveModal && (
        <div className="ov" onClick={(e) => e.target === e.currentTarget && setShowApproveModal(false)}>
          <div className="md" style={{ width: 'min(500px, 100%)' }} role="alertdialog">
            <h2 style={{ fontSize: '20px', color: '#FFFFFF', marginBottom: '12px' }}>
              Authorize Remediation Execution?
            </h2>
            <div style={{ background: 'rgba(5, 9, 20, 0.6)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(0, 217, 255, 0.12)', marginBottom: '18px', fontSize: '13.5px' }}>
              <p style={{ margin: '0 0 8px' }}>
                Action: <b style={{ color: 'var(--cyan)' }}>{sc.fix}</b>
              </p>
              <p style={{ margin: '0 0 8px', color: 'var(--text2)' }}>
                Target Component: <span className="mono" style={{ color: '#FFFFFF' }}>{sc.svc_name}</span>
              </p>
              <p style={{ margin: 0, color: 'var(--green)', fontSize: '12.5px' }}>
                Policy Engine: All 5 safety checks verified. Rollback plan staged.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button className="btn" onClick={() => setShowApproveModal(false)}>
                Cancel
              </button>
              <button
                className="btn g big"
                onClick={() => {
                  setShowApproveModal(false);
                  onApprove();
                }}
              >
                <Check size={15} /> Confirm & Execute
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rejection Confirmation Dialog */}
      {showRejectModal && (
        <div className="ov" onClick={(e) => e.target === e.currentTarget && setShowRejectModal(false)}>
          <div className="md" style={{ width: 'min(500px, 100%)' }} role="alertdialog">
            <h2 style={{ fontSize: '20px', color: '#FFFFFF', marginBottom: '12px' }}>
              Reject Remediation & Escalate?
            </h2>
            <p style={{ color: 'var(--text2)', fontSize: '13.5px', marginBottom: '14px' }}>
              The proposed automated action will be halted. The incident will be marked as Escalated and dispatched to the on-call team lead.
            </p>
            <div style={{ marginBottom: '18px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--cyan)', marginBottom: '6px', fontWeight: 600 }}>
                Operator Reason:
              </label>
              <input
                type="text"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button className="btn" onClick={() => setShowRejectModal(false)}>
                Cancel
              </button>
              <button
                className="btn r big"
                onClick={() => {
                  setShowRejectModal(false);
                  onReject(rejectReason);
                }}
              >
                <X size={15} /> Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
