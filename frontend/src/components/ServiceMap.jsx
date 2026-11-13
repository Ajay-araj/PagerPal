import React, { useState } from 'react';
import { Network, Info, Server, Activity, ArrowRight, X, Cpu, HardDrive, ShieldCheck } from 'lucide-react';
import { Topology3D } from './Topology3D';

export function ServiceMap({ graphData, activeSim }) {
  const [selectedNode, setSelectedNode] = useState(null);

  const data = graphData || {
    nodes: [],
    edges: [],
    propagation_path: [],
    root_service: null
  };

  const hasIncident = activeSim && activeSim.active && activeSim.sim.phase !== 'resolved';
  const rootSvc = hasIncident ? activeSim.sim.scenario.svc : data.root_service;
  const isResolved = activeSim && activeSim.active ? activeSim.sim.phase === 'resolved' : true;
  const isVerified = activeSim && activeSim.active ? ['verifying', 'resolved', 'await', 'executing'].includes(activeSim.sim.phase) : false;

  return (
    <div>
      <div className="hd">
        <div>
          <h1>Immersive 3D Service Topology</h1>
          <p>Real-time microservice dependency architecture with failure propagation and live synthetic telemetry probes.</p>
        </div>
      </div>

      {/* Primary 3D Topology Canvas */}
      <div className="pn" style={{ padding: '16px', background: 'rgba(5, 9, 20, 0.95)', overflow: 'hidden', marginBottom: '22px' }}>
        <Topology3D 
          graphData={graphData}
          activeSim={activeSim}
          height="520px"
          title="Interactive Distributed Service Fabric"
          onSelectNode={(node) => setSelectedNode(node)}
        />
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <div 
          className="pn" 
          style={{ 
            borderColor: 'var(--cyan)', 
            background: 'linear-gradient(135deg, rgba(16, 29, 48, 0.96) 0%, rgba(11, 20, 36, 0.96) 100%)', 
            position: 'relative',
            boxShadow: '0 0 30px rgba(0, 217, 255, 0.18)' 
          }}
        >
          <button
            className="btn"
            onClick={() => setSelectedNode(null)}
            style={{ position: 'absolute', right: '16px', top: '16px', padding: '5px 10px' }}
          >
            <X size={14} /> Close
          </button>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <Server size={20} style={{ color: 'var(--cyan)' }} />
            <h2 style={{ margin: 0, fontSize: '18px' }}>
              {selectedNode.display || selectedNode.name} (<span className="mono">{selectedNode.name}</span>)
            </h2>
            <span className={`b ${selectedNode.color || 'grn'}`}>
              {selectedNode.computedStatus || selectedNode.badge || 'OPERATIONAL'}
            </span>
          </div>

          <p className="sub" style={{ margin: '4px 0 16px' }}>
            Architecture Tier: <b>{selectedNode.tier ? selectedNode.tier.toUpperCase() : 'BACKEND CLUSTER'}</b> · Topology Node Key: <span className="mono">{selectedNode.id}</span>
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', fontSize: '13px' }}>
            <div style={{ background: 'rgba(5, 9, 20, 0.6)', padding: '12px 14px', borderRadius: '8px', border: '1px solid rgba(0, 217, 255, 0.1)' }}>
              <div style={{ color: 'var(--text2)', fontSize: '11px', textTransform: 'uppercase', marginBottom: '4px' }}>Causal Status</div>
              <b style={{ color: selectedNode.isRoot ? 'var(--red)' : selectedNode.isPath ? 'var(--amber)' : 'var(--green)' }}>
                {selectedNode.isRoot ? 'Verified Fault Origin' : selectedNode.isPath ? 'Degraded In Propagation Chain' : 'Nominal Health'}
              </b>
            </div>

            <div style={{ background: 'rgba(5, 9, 20, 0.6)', padding: '12px 14px', borderRadius: '8px', border: '1px solid rgba(0, 217, 255, 0.1)' }}>
              <div style={{ color: 'var(--text2)', fontSize: '11px', textTransform: 'uppercase', marginBottom: '4px' }}>SLI Health Probes</div>
              <span style={{ color: 'var(--green)', display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                <ShieldCheck size={14} /> Synthetic probes passing nominal thresholds
              </span>
            </div>

            <div style={{ background: 'rgba(5, 9, 20, 0.6)', padding: '12px 14px', borderRadius: '8px', border: '1px solid rgba(0, 217, 255, 0.1)' }}>
              <div style={{ color: 'var(--text2)', fontSize: '11px', textTransform: 'uppercase', marginBottom: '4px' }}>Isolation Boundary</div>
              <span className="mono" style={{ color: 'var(--cyan)' }}>
                namespace: pagerpal-sim / isolated
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Propagation & Map Legend Grid */}
      <div className="two">
        <div className="pn">
          <h2>
            <Activity size={16} style={{ color: 'var(--red)' }} />
            Failure Propagation Analysis
          </h2>
          <p style={{ lineHeight: 1.65 }}>
            {hasIncident ? (
              <>
                Simulated fault originated in <b className="mono" style={{ color: 'var(--red)' }}>{data.root_service_name || rootSvc}</b> and
                propagated along downstream dependency vectors to <b className="mono">checkout-svc</b>:
                <br />
                <span className="mono" style={{ color: 'var(--red)', display: 'inline-block', margin: '8px 0', padding: '6px 12px', background: 'rgba(255, 61, 85, 0.1)', borderRadius: '6px', border: '1px solid rgba(255, 61, 85, 0.25)' }}>
                  {(data.propagation_path || []).join('  ')}
                </span>
                <br />
                {isVerified ? 'Root cause has been verified against telemetry evidence with 100% causal certainty.' : 'Causal root is currently suspected by RCA agents.'}
              </>
            ) : isResolved ? (
              'All microservices are operating nominally. Zero cascading latency or anomalous error rate detected across topology paths.'
            ) : (
              'No active incident in flight. Launch Chaos Mode to trigger simulated service failure propagation.'
            )}
          </p>
        </div>

        <div className="pn">
          <h2>Topology HUD Legend & Diagnostics</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span className="b grn" style={{ minWidth: '95px', marginRight: '10px' }}> Healthy</span>
              <span>p95 Latency &lt; 150ms · Error rate 0.0% · Probes nominal</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span className="b amb" style={{ minWidth: '95px', marginRight: '10px' }}> Degraded</span>
              <span>Downstream dependency delay · Queue backlog elevated</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span className="b red" style={{ minWidth: '95px', marginRight: '10px' }}> Failing</span>
              <span>Primary failure root cause · Injected chaos fault origin</span>
            </div>
            <div style={{ color: 'var(--text2)', marginTop: '6px', fontSize: '12px', lineHeight: 1.6, borderTop: '1px solid rgba(0, 217, 255, 0.08)', paddingTop: '8px' }}>
              • <b>3D Navigation:</b> Click and drag with mouse/pointer to rotate orbit; scroll to zoom.<br />
              • <b>Traveling Particles:</b> Directional telemetry packets flowing along active network edges.<br />
              • <b>Pulsing Shockwave:</b> Highlights the identified root-cause node in the 3D space.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
