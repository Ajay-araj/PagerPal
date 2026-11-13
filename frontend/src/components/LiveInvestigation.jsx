import React from 'react';
import { 
  Zap, Clock, ShieldAlert, ArrowRight, CheckCircle2, AlertOctagon, 
  Brain, FileSearch, ShieldCheck, Terminal, Cpu 
} from 'lucide-react';
import { Topology3D } from './Topology3D';

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
  waiting: 'Queued',
  running: 'Executing',
  completed: 'Verified',
  review: 'Needs Review',
  failed: 'Interrupted'
};

export function LiveInvestigation({ simData, onOpenChaos, onOpenApproval }) {
  if (!simData || !simData.active || !simData.sim) {
    return (
      <div>
        <div className="hd">
          <div>
            <h1>Autonomous Investigation Console</h1>
            <p>Collaborative multi-agent reasoning, evidence verification, and safety-gated remediation.</p>
          </div>
        </div>
        <div className="pn empty" style={{ padding: '60px 20px', background: 'rgba(11, 20, 36, 0.7)' }}>
          <AlertOctagon size={48} style={{ color: 'var(--text2)', margin: '0 auto 16px', opacity: 0.6 }} />
          <b style={{ fontSize: '18px', display: 'block', color: '#FFFFFF', marginBottom: '8px' }}>
            No Active Incident In Flight
          </b>
          <p style={{ maxWidth: '480px', margin: '0 auto 24px', color: 'var(--text2)', lineHeight: 1.6 }}>
            Initiate Chaos Mode to inject a fault scenario into the simulated microservice topology and watch the 7 autonomous agents triage, trace causal roots, verify evidence, check safety policies, and verify recovery.
          </p>
          <button className="btn p big" onClick={onOpenChaos}>
            <Zap size={16} /> Launch Chaos Mode
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
      {/* Header */}
      <div className="hd">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <h1>Live Autonomous Investigation</h1>
            <span className="id">{s.id}</span>
          </div>
          <p>
            Scenario: <b style={{ color: '#FFFFFF' }}>{sc.name || 'Simulated Incident'}</b> · Target Service: <span className="mono" style={{ color: 'var(--cyan)' }}>{sc.svc_name}</span> ·{' '}
            <span className="mono" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: 'var(--text2)' }}>
              <Clock size={13} /> elapsed {s.elapsed || 'in-progress'}
            </span>
          </p>
        </div>
        <div>
          <span className={`b ${stConf[0]}`} style={{ fontSize: '13px', padding: '5px 14px' }}>
            {stConf[1]} {phaseLabel.toUpperCase()}
          </span>
        </div>
      </div>

      {/* 7-Stage Multi-Agent Workflow Rail */}
      <div className="pn" style={{ marginBottom: '22px' }}>
        <h2 style={{ marginBottom: '18px' }}>
          <Brain size={17} style={{ color: 'var(--cyan)' }} />
          Autonomous Multi-Agent Workflow Pipeline
        </h2>
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
                <span className={`b ${badgeColor}`} style={{ fontSize: '10.5px' }}>
                  {STAGE_LABELS[stg.status] || stg.status}
                </span>
                <p>{stg.task}</p>
                {stg.result && (
                  <p style={{ color: '#FFFFFF', marginTop: '6px', fontWeight: 600, fontSize: '12px' }}>
                    {stg.result}
                  </p>
                )}
                {stg.timestamp && <p className="mono sub" style={{ marginTop: '4px' }}>{stg.timestamp}</p>}
              </div>
            );
          })}
        </div>
      </div>

      {/* Awaiting Human Approval Alert Card */}
      {s.phase === 'await' && (
        <div 
          className="pn" 
          style={{ 
            borderColor: 'var(--amber)', 
            background: 'linear-gradient(135deg, rgba(35, 27, 14, 0.95) 0%, rgba(20, 15, 8, 0.95) 100%)',
            boxShadow: '0 0 30px rgba(255, 174, 66, 0.25)',
            marginBottom: '22px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <span className="b amb" style={{ marginBottom: '10px' }}>
                <ShieldAlert size={14} /> Level 2 Reversible Action · Human Gate Required
              </span>
              <h2 style={{ fontSize: '20px', margin: '8px 0 6px', color: '#ffeaad' }}>
                {sc.fix}
              </h2>
              <p style={{ margin: 0, color: 'var(--text2)', fontSize: '13.5px' }}>
                Policy Engine evaluated preconditions: <b>PASS</b>. Target component: <span className="mono" style={{ color: 'var(--cyan)' }}>{sc.svc_name}</span>.
                Zero autonomous changes are made without operator approval.
              </p>
            </div>
            <button className="btn p big" onClick={onOpenApproval} style={{ boxShadow: '0 0 20px rgba(0, 217, 255, 0.4)' }}>
              Review & Authorize Remediation <ArrowRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* 2-Column Detective Workstation Layout */}
      <div className="two">
        {/* Left Column: Real-time Event Stream */}
        <div className="pn">
          <h2>
            <Terminal size={17} style={{ color: 'var(--cyan)' }} />
            Live Agent Event Telemetry
          </h2>
          <div className="log mono">
            {s.log && s.log.map((l, i) => (
              <div key={i}>
                <span className="m">[{l.t}]</span> <span className="a">{l.a}:</span>{' '}
                <span style={{ color: l.c === 'grn' ? 'var(--green)' : l.c === 'red' ? 'var(--red)' : l.c === 'amb' ? 'var(--amber)' : 'var(--text)' }}>
                  {l.m}
                </span>
              </div>
            ))}
          </div>
          <span className="sub" style={{ marginTop: '10px', display: 'block', lineHeight: 1.5 }}>
            Telemetry stream displays deterministic tool calls, verified claims, and policy outputs only. Untrusted internal reasoning is isolated.
          </span>
        </div>

        {/* Right Column: Mini Topology & Causal Root Hypotheses */}
        <div className="pn">
          <h2>
            <FileSearch size={17} style={{ color: 'var(--cyan)' }} />
            Causal Root Cause & Confidence Meter
          </h2>
          
          <div style={{ background: 'rgba(5, 9, 20, 0.6)', padding: '14px 16px', borderRadius: '10px', border: '1px solid rgba(0, 217, 255, 0.1)', marginBottom: '16px' }}>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text2)', fontWeight: 600 }}>Identified Root Cause</div>
            <div style={{ fontSize: '15px', color: '#FFFFFF', fontWeight: 600, margin: '6px 0' }}>
              {sc.cause || 'Under investigation by Causal RCA agent'}
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--text2)' }}>
              <b>Causal Propagation:</b>{' '}
              <span className="mono" style={{ color: 'var(--red)' }}>
                checkout-svc → {sc.svc_name} → orders-db
              </span>
            </div>
          </div>

          <div style={{ marginTop: '12px' }}>
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
          </div>

          <div style={{ marginTop: '16px', padding: '10px 14px', background: 'rgba(0, 217, 255, 0.04)', borderRadius: '8px', border: '1px solid rgba(0, 217, 255, 0.12)' }}>
            <span style={{ fontSize: '12px', color: 'var(--text2)' }}>
              <b>Evidence Verifier:</b> {sc.dropped_claim || 'Unverified or hallucinated assertions eliminated by algorithmic claim checks.'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
