import React, { useState, useMemo } from 'react';
import { 
  Zap, Clock, ShieldAlert, ArrowRight, CheckCircle2, AlertOctagon, 
  Brain, FileSearch, ShieldCheck, Terminal, Cpu, Sparkles, Server, Check, AlertTriangle, Layers
} from 'lucide-react';
import { AgentOrchestration3D, AGENTS_SPEC } from './AgentOrchestration3D';
import { PagerPalLogoIcon } from './PagerPalLogo';

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
  const [selectedAgent, setSelectedAgent] = useState(null);

  if (!simData || !simData.active || !simData.sim) {
    return (
      <div>
        <div className="hd">
          <div>
            <h1>Autonomous Investigation Console</h1>
            <p>Collaborative multi-agent reasoning, evidence verification, and safety-gated remediation.</p>
          </div>
        </div>
        <div className="pn empty" style={{ padding: '60px 20px', background: 'var(--card)' }}>
          <AlertOctagon size={48} style={{ color: 'var(--text2)', margin: '0 auto 16px', opacity: 0.6 }} />
          <b style={{ fontSize: '18px', display: 'block', color: '#FFFFFF', marginBottom: '8px' }}>
            No Active Incident In Flight
          </b>
          <p style={{ maxWidth: '480px', margin: '0 auto 24px', color: 'var(--text2)', lineHeight: 1.6 }}>
            Initiate Chaos Mode to inject a fault scenario into the simulated microservice topology and watch the 8 autonomous agents triage, trace causal roots, verify evidence, check safety policies, and verify recovery in 3D.
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

  // Current active agent from stages
  const activeStage = s.stages?.find(stg => stg.status === 'running') 
    || s.stages?.slice().reverse().find(stg => stg.status === 'completed')
    || s.stages?.[0];

  const currentInspectedAgent = selectedAgent || (activeStage ? AGENTS_SPEC.find(a => a.id === activeStage.agent) || AGENTS_SPEC[0] : AGENTS_SPEC[0]);

  // Find inspected agent's execution details
  const inspectedStageInfo = s.stages?.find(stg => stg.agent === currentInspectedAgent.id);

  return (
    <div>
      {/* Top Incident Status Banner */}
      <div className="hd">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <PagerPalLogoIcon size={26} />
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
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span className={`b ${stConf[0]}`} style={{ fontSize: '13px', padding: '5px 14px' }}>
            {stConf[1]} {phaseLabel.toUpperCase()}
          </span>
        </div>
      </div>

      {/* SIGNATURE 3D MULTI-AGENT ORCHESTRATION CANVAS */}
      <div className="pn" style={{ padding: '14px', marginBottom: '22px', background: 'var(--card)' }}>
        <AgentOrchestration3D 
          simData={simData}
          selectedAgentId={currentInspectedAgent?.id}
          onSelectAgent={(spec) => setSelectedAgent(spec)}
          height="480px"
        />
      </div>

      {/* Awaiting Human Approval Alert Card (Prominent When Paused) */}
      {s.phase === 'await' && (
        <div 
          className="pn" 
          style={{ 
            borderColor: 'var(--amber)', 
            background: 'var(--elevated)',
            boxShadow: '0 0 24px rgba(255, 170, 54, 0.25)',
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
      <div className="grid">
        {/* Left Column: Pipeline Timeline & Real-Time Event Stream */}
        <div>
          {/* Agent Workflow Execution Rail */}
          <div className="pn" style={{ marginBottom: '22px' }}>
            <h2 style={{ marginBottom: '16px' }}>
              <Brain size={17} style={{ color: 'var(--cyan)' }} />
              Autonomous Agent Pipeline Execution
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

                const isSelected = currentInspectedAgent?.id === stg.agent;

                return (
                  <div 
                    key={stg.agent} 
                    className={`stg ${stg.status}`}
                    style={{ cursor: 'pointer', opacity: isSelected ? 1 : 0.85 }}
                    onClick={() => {
                      const found = AGENTS_SPEC.find(a => a.id === stg.agent);
                      if (found) setSelectedAgent(found);
                    }}
                  >
                    <i>
                      {isCompleted ? '' : isFailed ? '' : isReview ? '!' : i + 1}
                    </i>
                    <h3 style={{ color: isSelected ? 'var(--cyan)' : 'var(--text)' }}>{stg.agent}</h3>
                    <span className={`b ${badgeColor}`} style={{ fontSize: '10px' }}>
                      {STAGE_LABELS[stg.status] || stg.status}
                    </span>
                    <p>{stg.task}</p>
                    {stg.result && (
                      <p style={{ color: '#FFFFFF', marginTop: '6px', fontWeight: 600, fontSize: '11.5px' }}>
                        {stg.result}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Real-Time Agent Telemetry Terminal */}
          <div className="pn">
            <h2>
              <Terminal size={17} style={{ color: 'var(--cyan)' }} />
              Live Agent Telemetry Stream
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
              Deterministic tool calls, verified claims, and policy outputs only. Untrusted internal reasoning is isolated.
            </span>
          </div>
        </div>

        {/* Right Column: Selected Agent Inspector & Causal Findings */}
        <div>
          {/* Selected Agent Inspector Card */}
          <div className="pn" style={{ borderColor: currentInspectedAgent.color, marginBottom: '22px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: currentInspectedAgent.color }} />
                <h2 style={{ margin: 0, fontSize: '16px' }}>{currentInspectedAgent.name}</h2>
              </div>
              <span className={`b ${inspectedStageInfo?.status === 'completed' ? 'grn' : inspectedStageInfo?.status === 'running' ? 'cy' : 'mu'}`}>
                {inspectedStageInfo ? (STAGE_LABELS[inspectedStageInfo.status] || inspectedStageInfo.status) : 'Queued'}
              </span>
            </div>

            <div style={{ fontSize: '12px', color: 'var(--cyan)', fontWeight: 600, marginBottom: '6px' }}>
              Role: {currentInspectedAgent.role}
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text2)', margin: '0 0 14px', lineHeight: 1.45 }}>
              {currentInspectedAgent.description}
            </p>

            {inspectedStageInfo?.result && (
              <div style={{ background: 'var(--elevated)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border)', marginBottom: '12px' }}>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text2)', fontWeight: 600, marginBottom: '4px' }}>
                  Execution Result / Artifact
                </div>
                <div style={{ color: '#FFFFFF', fontSize: '13px', fontWeight: 600 }}>
                  {inspectedStageInfo.result}
                </div>
              </div>
            )}

            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Selected from 3D Orchestration Scene · Real-time LangGraph sync
            </div>
          </div>

          {/* Causal Root Cause & Confidence Scoring */}
          <div className="pn">
            <h2>
              <FileSearch size={17} style={{ color: 'var(--cyan)' }} />
              Causal Root Cause & Confidence Index
            </h2>
            
            <div style={{ background: 'var(--elevated)', padding: '14px 16px', borderRadius: '8px', border: '1px solid var(--border)', marginBottom: '16px' }}>
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

            <div style={{ marginTop: '16px', padding: '10px 14px', background: 'var(--elevated)', borderRadius: '8px', border: '1px solid var(--border)' }}>
              <span style={{ fontSize: '12px', color: 'var(--text2)' }}>
                <b>Evidence Verifier:</b> {sc.dropped_claim || 'Unverified or hallucinated assertions eliminated by algorithmic claim checks.'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
