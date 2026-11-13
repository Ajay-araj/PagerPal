import React from 'react';
import { Zap, Clock, ShieldAlert, ArrowRight, CheckCircle2, AlertOctagon } from 'lucide-react';

const STB = {
  Resolved: ['grn', ''],
  Investigating: ['amb', ''],
  'Awaiting approval': ['amb', 'PAUSED'],
  Remediating: ['cy', ''],
  'Verifying recovery': ['cy', ''],
  Escalated: ['red', ''],
  Stopped: ['red', '']
};

const STAGE_LABELS = {
  waiting: 'Waiting',
  running: 'Running',
  completed: 'Completed',
  review: 'Needs review',
  failed: 'Failed'
};

export function LiveInvestigation({ simData, onOpenChaos, onOpenApproval }) {
  if (!simData || !simData.active || !simData.sim) {
    return (
      <div>
        <div className="hd">
          <div>
            <h1>Live investigation</h1>
            <p>Watch seven autonomous agents collaborate through an active incident.</p>
          </div>
        </div>
        <div className="pn empty">
          <AlertOctagon size={40} style={{ color: 'var(--mu)', margin: '0 auto 12px' }} />
          <b style={{ fontSize: '16px', display: 'block', color: 'var(--tx)' }}>No Active Simulation Running</b>
          <p style={{ maxWidth: '420px', margin: '8px auto 20px', color: 'var(--mu)' }}>
            Start Chaos Mode to inject a reproducible failure scenario and observe the agents correlate alerts, rank causes, verify evidence, evaluate safety policies, and verify recovery.
          </p>
          <button className="btn p big" onClick={onOpenChaos}>
            <Zap size={16} /> Start Chaos Mode
          </button>
        </div>
      </div>
    );
  }

  const s = simData.sim;
  const sc = s.scenario || {};
  const phaseLabel = {
    running: 'Investigating',
    await: 'Awaiting approval',
    executing: 'Remediating',
    verifying: 'Verifying recovery',
    resolved: 'Resolved',
    rejected: 'Escalated',
    stopped: 'Stopped'
  }[s.phase] || s.phase;

  const stConf = STB[phaseLabel] || ['mu', '•'];

  return (
    <div>
      <div className="hd">
        <div>
          <h1>Live investigation</h1>
          <p>
            <span className="id">{s.id}</span> · {sc.name || 'Simulated Incident'} ·{' '}
            <span className="mono" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <Clock size={13} /> elapsed {s.elapsed}
            </span>
          </p>
        </div>
        <div>
          <span className={`b ${stConf[0]}`}>
            {stConf[1]} {phaseLabel}
          </span>
        </div>
      </div>

      {/* 7-Stage Workflow Rail */}
      <div className="pn">
        <h2 style={{ marginBottom: '16px' }}>Autonomous agent stages</h2>
        <div className="rail">
          {s.stages && s.stages.map((stg, i) => {
            const isCompleted = stg.status === 'completed';
            const isRunning = stg.status === 'running';
            const isReview = stg.status === 'review';
            const isFailed = stg.status === 'failed';

            const badgeColor = isCompleted
              ? 'grn'
              : isRunning
              ? 'cy'
              : isReview
              ? 'amb'
              : isFailed
              ? 'red'
              : 'mu';

            return (
              <div key={stg.agent} className={`stg ${stg.status}`}>
                <i>
                  {isCompleted ? '' : isFailed ? '' : isReview ? '!' : i + 1}
                </i>
                <h3>{stg.agent}</h3>
                <span className={`b ${badgeColor}`}>
                  {STAGE_LABELS[stg.status] || stg.status}
                </span>
                <p>{stg.task}</p>
                {stg.result && (
                  <p style={{ color: 'var(--tx)', marginTop: '6px', fontWeight: 500 }}>
                    {stg.result}
                  </p>
                )}
                {stg.timestamp && <p className="mono sub">{stg.timestamp}</p>}
              </div>
            );
          })}
        </div>
      </div>

      {/* Awaiting human approval alert card */}
      {s.phase === 'await' && (
        <div className="pn" style={{ borderColor: 'var(--amb)', background: '#1c170d' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
            <div>
              <span className="b amb" style={{ marginBottom: '8px' }}>
                <ShieldAlert size={13} /> Human Approval Required
              </span>
              <h2 style={{ fontSize: '18px', margin: '6px 0 4px', color: '#ffdfa0' }}>
                {sc.fix}
              </h2>
              <p style={{ margin: 0, color: 'var(--mu)', fontSize: '13px' }}>
                Policy Engine evaluated Level 2 reversible preconditions: <b>PASS</b>. Target: <span className="mono">{sc.svc_name}</span>.
              </p>
            </div>
            <button className="btn p big" onClick={onOpenApproval}>
              Review & Approve Remediation <ArrowRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* Real-time agent event stream log */}
      <div className="pn">
        <h2>Live event stream</h2>
        <div className="log mono">
          {s.log && s.log.map((l, i) => (
            <div key={i}>
              <span className="m">[{l.t}]</span> <span className="a">{l.a}:</span>{' '}
              <span style={{ color: l.c === 'grn' ? 'var(--grn)' : l.c === 'red' ? 'var(--red)' : l.c === 'amb' ? 'var(--amb)' : 'var(--tx)' }}>
                {l.m}
              </span>
            </div>
          ))}
        </div>
        <span className="sub" style={{ marginTop: '8px', display: 'block' }}>
          Event stream displays explicit actions, tool calls, verified claims, and policy outputs only. Untrusted internal reasoning is omitted.
        </span>
      </div>
    </div>
  );
}

