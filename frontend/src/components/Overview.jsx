import React from 'react';
import { Zap, AlertTriangle, ShieldCheck, CheckCircle2, AlertCircle, Activity, ArrowUpRight } from 'lucide-react';
import { Topology3D } from './Topology3D';

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

export function Overview({ dashboard, onOpenChaos, onOpenIncident, isSimBusy, activeSim, onNavigate }) {
  const d = dashboard || {
    is_simulation_active: false,
    active_incidents: 0,
    critical_alerts: 0,
    services_affected: 0,
    mttr: '6m 40s (sample)',
    service_health: [],
    recent_incidents: [],
    recent_logs: [],
    trend_data: [
      { day: 'Fri', count: 3 },
      { day: 'Sat', count: 5 },
      { day: 'Sun', count: 2 },
      { day: 'Mon', count: 6 },
      { day: 'Tue', count: 4 },
      { day: 'Wed', count: 3 },
      { day: 'Today', count: 3 }
    ]
  };

  const trendData = d.trend_data || [];
  const maxVal = Math.max(...trendData.map((t) => t.count), 1) + 1;

  return (
    <div>
      {/* Header */}
      <div className="hd">
        <div>
          <h1>Operations Command Centre</h1>
          <p>
            {isSimBusy
              ? 'Multi-agent orchestration in progress. Active incident under autonomous investigation.'
              : 'Autonomous telemetry nominal. 7 core microservices monitored across availability zones.'}
          </p>
        </div>
        <button className="btn p big" onClick={onOpenChaos}>
          <Zap size={16} /> Start Chaos Mode
        </button>
      </div>

      {/* Simulation Notice Banner */}
      <div className="note">
        <AlertTriangle size={16} style={{ flexShrink: 0, color: 'var(--amber)' }} />
        <span>
          <b>SIMULATION ENVIRONMENT</b> · Sandboxed telemetry generator active. All metrics, logs, and spans are synthetic; no production infrastructure is affected.
        </span>
      </div>

      {/* Top HUD Metrics Strip */}
      <div className="strip">
        <div>
          <b>{d.active_incidents}</b>
          <span>Active incidents</span>
        </div>
        <div>
          <b style={{ color: d.critical_alerts > 0 ? 'var(--red)' : '#FFFFFF' }}>{d.critical_alerts}</b>
          <span>Critical alerts</span>
        </div>
        <div>
          <b>{d.services_affected}</b>
          <span>Services affected</span>
        </div>
        <div>
          <b style={{ color: 'var(--cyan)' }}>{d.mttr}</b>
          <span>MTTR · measured</span>
        </div>
      </div>

      {/* Central 3D Service Topology Centerpiece */}
      <div className="pn" style={{ padding: '16px', marginBottom: '24px', background: 'var(--card)' }}>
        <Topology3D 
          activeSim={activeSim}
          height="380px"
          title="Live Service Topology & Failure Propagation Mesh"
          onSelectNode={(node) => {
            if (onNavigate) onNavigate('map');
          }}
        />
      </div>

      {/* Analytics & Service Health Grid */}
      <div className="grid">
        <div className="pn">
          <h2>
            <Activity size={16} style={{ color: 'var(--cyan)' }} />
            Incidents Per Day (7-Day Trend)
          </h2>
          <svg viewBox="0 0 400 150" width="100%" role="img" aria-label="Incidents per day trend chart">
            <defs>
              <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00D9FF" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#0D0D0D" stopOpacity="0.4" />
              </linearGradient>
              <linearGradient id="barGradActive" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#FFAA36" stopOpacity="0.95" />
                <stop offset="100%" stopColor="#0D0D0D" stopOpacity="0.4" />
              </linearGradient>
            </defs>
            {trendData.map((v, i) => {
              const h = (v.count / maxVal) * 95;
              const x = 32 + i * 50;
              const isToday = i === trendData.length - 1;
              return (
                <g key={v.day}>
                  <rect
                    x={x}
                    y={120 - h}
                    width={32}
                    height={h}
                    rx={5}
                    fill={isToday ? 'url(#barGradActive)' : 'url(#barGrad)'}
                    stroke={isToday ? 'rgba(255, 174, 66, 0.5)' : 'rgba(0, 217, 255, 0.3)'}
                    strokeWidth={1}
                  />
                  <text
                    x={x + 16}
                    y={112 - h}
                    textAnchor="middle"
                    fill={isToday ? 'var(--amber)' : '#FFFFFF'}
                    fontSize="11"
                    fontFamily="'JetBrains Mono', monospace"
                    fontWeight="600"
                  >
                    {v.count}
                  </text>
                  <text
                    x={x + 16}
                    y={140}
                    textAnchor="middle"
                    fill="var(--text2)"
                    fontSize="11"
                  >
                    {v.day}
                  </text>
                </g>
              );
            })}
            <line x1="16" x2="384" y1="120" y2="120" stroke="var(--border)" />
          </svg>
          <span className="sub" style={{ marginTop: '8px', display: 'block' }}>
            Daily incident aggregation. Today's figure updates in real time with active chaos injection cycles.
          </span>
        </div>

        <div className="pn">
          <h2>Service Fleet Health Matrix</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {d.service_health && d.service_health.map((svc) => (
              <div key={svc.id} className="svc">
                <span className="mono" style={{ fontWeight: 600 }}>{svc.name}</span>
                <span className={`b ${svc.color}`}>
                  {svc.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Incidents & Agent Stream Grid */}
      <div className="grid">
        <div className="pn">
          <h2>Recent Incident Ledger</h2>
          <div className="sc">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Title</th>
                  <th>Service</th>
                  <th>Severity</th>
                  <th>Detected</th>
                  <th>Status</th>
                  <th>Active Agent</th>
                </tr>
              </thead>
              <tbody>
                {d.recent_incidents && d.recent_incidents.map((r) => {
                  const sevConf = SEVB[r.severity] || ['mu', ''];
                  const stConf = STB[r.status] || ['mu', '•'];
                  return (
                    <tr
                      key={r.id}
                      tabIndex={0}
                      onClick={() => onOpenIncident(r.id, r.is_live)}
                      onKeyDown={(e) => e.key === 'Enter' && onOpenIncident(r.id, r.is_live)}
                    >
                      <td className="id">{r.id}</td>
                      <td><b>{r.title}</b></td>
                      <td className="mono" style={{ color: 'var(--text2)' }}>{r.service}</td>
                      <td>
                        <span className={`b ${sevConf[0]}`}>
                          {sevConf[1]} {r.severity}
                        </span>
                      </td>
                      <td style={{ fontSize: '12px', color: 'var(--text2)' }}>{r.detected_at}</td>
                      <td>
                        <span className={`b ${stConf[0]}`}>
                          {stConf[1]} {r.status}
                        </span>
                      </td>
                      <td>
                        {r.status === 'Resolved' ? (
                          <span className="sub">none</span>
                        ) : (
                          <span style={{ color: 'var(--cyan)', fontWeight: 600 }}>{r.active_agent}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="pn">
          <h2>Autonomous Agent Activity Stream</h2>
          <ul className="tl">
            {d.recent_logs && d.recent_logs.map((l, idx) => (
              <li key={idx} className={l.c || 'cy'}>
                <span className="t mono">[{l.t}]</span>
                <b>{l.a}:</b> <span>{l.m}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
