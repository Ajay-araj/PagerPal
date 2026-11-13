import React from 'react';
import { Zap, AlertTriangle, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';

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

export function Overview({ dashboard, onOpenChaos, onOpenIncident, isSimBusy }) {
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
      <div className="hd">
        <div>
          <h1>Operations overview</h1>
          <p>
            {isSimBusy
              ? '1 incident is currently being handled by autonomous agents.'
              : 'All services healthy. No active incidents.'}
          </p>
        </div>
        <button className="btn p big" onClick={onOpenChaos}>
          <Zap size={16} /> Start Chaos Mode
        </button>
      </div>

      <div className="note">
        <AlertTriangle size={16} style={{ flexShrink: 0 }} />
        <span>
          Simulation environment. No production systems are connected. All figures are sample data until simulations produce measurements.
        </span>
      </div>

      <div className="strip">
        <div>
          <b>{d.active_incidents}</b>
          <span>Active incidents</span>
        </div>
        <div>
          <b>{d.critical_alerts}</b>
          <span>Critical alerts</span>
        </div>
        <div>
          <b>{d.services_affected}</b>
          <span>Services affected</span>
        </div>
        <div>
          <b>{d.mttr}</b>
          <span>MTTR · sample data</span>
        </div>
      </div>

      <div className="grid">
        <div className="pn">
          <h2>Incidents per day</h2>
          <svg viewBox="0 0 400 160" width="100%" role="img" aria-label="Incidents per day trend chart">
            {trendData.map((v, i) => {
              const h = (v.count / maxVal) * 105;
              const x = 32 + i * 50;
              const isToday = i === trendData.length - 1;
              return (
                <g key={v.day}>
                  <rect
                    x={x}
                    y={130 - h}
                    width={30}
                    height={h}
                    rx={4}
                    fill={isToday ? 'var(--amb)' : '#273b5e'}
                  />
                  <text
                    x={x + 15}
                    y={122 - h}
                    textAnchor="middle"
                    fill="var(--tx)"
                    fontSize="11"
                  >
                    {v.count}
                  </text>
                  <text
                    x={x + 15}
                    y={148}
                    textAnchor="middle"
                    fill="var(--mu)"
                    fontSize="11"
                  >
                    {v.day}
                  </text>
                </g>
              );
            })}
            <line x1="16" x2="384" y1="130" y2="130" stroke="var(--ln)" />
          </svg>
          <span className="sub">Count of incidents. Today's bar adds active simulated chaos runs.</span>
        </div>

        <div className="pn">
          <h2>Service health</h2>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {d.service_health && d.service_health.map((svc) => (
              <div key={svc.id} className="svc">
                <span className="mono">{svc.name}</span>
                <span className={`b ${svc.color}`}>
                  {svc.color === 'grn' ? '✓' : svc.color === 'red' ? '▲' : '◆'} {svc.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid">
        <div className="pn">
          <h2>Recent incidents</h2>
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
                  <th>Active agent</th>
                </tr>
              </thead>
              <tbody>
                {d.recent_incidents && d.recent_incidents.map((r) => {
                  const sevConf = SEVB[r.severity] || ['mu', '○'];
                  const stConf = STB[r.status] || ['mu', '•'];
                  return (
                    <tr
                      key={r.id}
                      tabIndex={0}
                      onClick={() => onOpenIncident(r.id, r.is_live)}
                      onKeyDown={(e) => e.key === 'Enter' && onOpenIncident(r.id, r.is_live)}
                    >
                      <td className="id">{r.id}</td>
                      <td>{r.title}</td>
                      <td className="mono">{r.service}</td>
                      <td>
                        <span className={`b ${sevConf[0]}`}>
                          {sevConf[1]} {r.severity}
                        </span>
                      </td>
                      <td>{r.detected_at}</td>
                      <td>
                        <span className={`b ${stConf[0]}`}>
                          {stConf[1]} {r.status}
                        </span>
                      </td>
                      <td>
                        {r.status === 'Resolved' ? (
                          <span className="sub">none</span>
                        ) : (
                          r.active_agent
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
          <h2>Agent activity stream</h2>
          <ul className="tl">
            {d.recent_logs && d.recent_logs.map((l, idx) => (
              <li key={idx} className={l.c || 'cy'}>
                <span className="t mono">{l.t}</span>
                <b>{l.a}:</b> {l.m}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

