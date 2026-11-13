import React, { useState } from 'react';
import { Network, Info, Server, Activity, ArrowRight, X } from 'lucide-react';

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
          <h1>Service map</h1>
          <p>NetworkX dependency graph showing service call hierarchy and failure propagation.</p>
        </div>
      </div>

      <div className="pn sc" style={{ background: '#070b14', overflow: 'hidden' }}>
        <svg
          viewBox="0 0 780 340"
          width="100%"
          style={{ minWidth: '640px', height: '340px' }}
          role="img"
          aria-label="Service dependency graph"
        >
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#445782" />
            </marker>
            <marker
              id="arrow-red"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--red)" />
            </marker>
          </defs>

          {/* Dependency Edges */}
          {data.edges && data.edges.map((e, idx) => {
            const isPath = e.is_path;
            return (
              <line
                key={idx}
                x1={e.from_x + 60}
                y1={e.from_y}
                x2={e.to_x - 60}
                y2={e.to_y}
                stroke={isPath ? 'var(--red)' : '#2d3e63'}
                strokeWidth={isPath ? 3.5 : 1.6}
                markerEnd={isPath ? 'url(#arrow-red)' : 'url(#arrow)'}
              />
            );
          })}

          {/* Service Nodes */}
          {data.nodes && data.nodes.map((node) => {
            const isRoot = node.is_root;
            const strokeColor =
              node.color === 'red'
                ? 'var(--red)'
                : node.color === 'amb'
                ? 'var(--amb)'
                : 'var(--grn)';

            const rx = isRoot && node.is_verified ? 22 : 8;
            const isDashed = isRoot && !node.is_verified;
            const isSelected = selectedNode && selectedNode.id === node.id;

            return (
              <g
                key={node.id}
                onClick={() => setSelectedNode(node)}
                style={{ cursor: 'pointer' }}
                tabIndex={0}
                onKeyDown={(ev) => ev.key === 'Enter' && setSelectedNode(node)}
              >
                <rect
                  x={node.x - 62}
                  y={node.y - 24}
                  width="124"
                  height="48"
                  rx={rx}
                  fill={isSelected ? '#182b4a' : 'var(--s2)'}
                  stroke={isSelected ? 'var(--cy)' : strokeColor}
                  strokeWidth={isSelected ? '3' : '2.2'}
                  strokeDasharray={isDashed ? '5 4' : undefined}
                />
                <text
                  x={node.x}
                  y={node.y - 4}
                  textAnchor="middle"
                  fill="var(--tx)"
                  fontSize="12"
                  fontFamily="'JetBrains Mono', monospace"
                  fontWeight="600"
                >
                  {node.name}
                </text>
                <text
                  x={node.x}
                  y={node.y + 13}
                  textAnchor="middle"
                  fill={strokeColor}
                  fontSize="11"
                  fontWeight="500"
                >
                  {node.badge}
                  {isRoot ? (node.is_verified ? ' · verified cause' : ' · suspected') : ''}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <div className="pn" style={{ borderColor: 'var(--cy)', background: '#0e1828', position: 'relative' }}>
          <button
            className="btn"
            onClick={() => setSelectedNode(null)}
            style={{ position: 'absolute', right: '14px', top: '14px', padding: '4px 8px' }}
          >
            <X size={14} /> Close
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Server size={18} style={{ color: 'var(--cy)' }} />
            <h2 style={{ margin: 0 }}>{selectedNode.display || selectedNode.name} (<span className="mono">{selectedNode.name}</span>)</h2>
            <span className={`b ${selectedNode.color}`}>{selectedNode.badge}</span>
          </div>
          <p className="sub" style={{ margin: '4px 0 10px' }}>
            Tier: <b>{selectedNode.tier ? selectedNode.tier.toUpperCase() : 'BACKEND'}</b> · NetworkX Node ID: <span className="mono">{selectedNode.id}</span>
          </p>
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '13px', color: 'var(--tx)' }}>
            <div>
              <b>Status:</b> {selectedNode.status} {selectedNode.is_root ? (selectedNode.is_verified ? '(Verified Root Cause)' : '(Suspected Cause)') : ''}
            </div>
            <div>
              <b>Health Probe:</b> Synthetic SLI checks responding within nominal bounds
            </div>
          </div>
        </div>
      )}

      <div className="two">
        <div className="pn">
          <h2>Propagation analysis</h2>
          <p>
            {hasIncident ? (
              <>
                Failure originated at <b className="mono">{data.root_service_name || rootSvc}</b> and
                propagated upstream to the customer-facing <b className="mono">checkout-svc</b> along{' '}
                <span className="mono" style={{ color: 'var(--red)' }}>
                  {(data.propagation_path || []).join(' → ')}
                </span>
                . {isVerified ? 'Root cause has been verified against telemetry evidence.' : 'Causal root is currently suspected.'}
              </>
            ) : isResolved ? (
              'All services are operational. No cascading latency or failure propagation detected.'
            ) : (
              'No active incident. Start Chaos Mode to trigger failure propagation.'
            )}
          </p>
        </div>

        <div className="pn">
          <h2>Map legend</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
            <div>
              <span className="b grn" style={{ marginRight: '8px' }}> Healthy</span>
              Normal latency SLI and 0% error rate
            </div>
            <div>
              <span className="b amb" style={{ marginRight: '8px' }}> Degraded</span>
              Cascaded latency impact or queueing
            </div>
            <div>
              <span className="b red" style={{ marginRight: '8px' }}> Failing</span>
              Primary origin / root-cause component
            </div>
            <div style={{ color: 'var(--mu)', marginTop: '4px' }}>
              • <b>Click any node:</b> View service tier and health diagnostics.<br />
              • <b>Dashed border:</b> Suspected cause awaiting Evidence Verifier confirmation.<br />
              • <b>Solid pill border:</b> Verified root cause confirmed by telemetry.<br />
              • <b>Thick red arrow:</b> Failure propagation path.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
