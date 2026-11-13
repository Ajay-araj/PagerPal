import React, { useState } from 'react';
import { Search, Zap } from 'lucide-react';

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

export function IncidentsList({ incidents, onOpenIncident, onOpenChaos }) {
  const [query, setQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const filtered = (incidents || []).filter((inc) => {
    if (severityFilter && inc.severity !== severityFilter) return false;
    if (statusFilter && inc.status !== statusFilter) return false;
    if (query) {
      const term = query.toLowerCase();
      const match =
        inc.id.toLowerCase().includes(term) ||
        inc.title.toLowerCase().includes(term) ||
        inc.service.toLowerCase().includes(term);
      if (!match) return false;
    }
    return true;
  });

  return (
    <div>
      <div className="hd">
        <div>
          <h1>Incidents</h1>
          <p>Every incident recorded in this simulation environment.</p>
        </div>
        <button className="btn p" onClick={onOpenChaos}>
          <Zap size={14} /> Start Chaos Mode
        </button>
      </div>

      <div className="pn">
        <div className="tools">
          <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
            <Search
              size={15}
              style={{
                position: 'absolute',
                left: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--mu)'
              }}
            />
            <input
              type="text"
              aria-label="Search incidents"
              placeholder="Search by ID, title, or affected service..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ width: '100%', paddingLeft: '32px' }}
            />
          </div>

          <select
            aria-label="Filter by severity"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="">All severities</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>

          <select
            aria-label="Filter by status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All statuses</option>
            <option value="Resolved">Resolved</option>
            <option value="Investigating">Investigating</option>
            <option value="Awaiting approval">Awaiting approval</option>
            <option value="Remediating">Remediating</option>
            <option value="Verifying recovery">Verifying recovery</option>
            <option value="Escalated">Escalated</option>
            <option value="Stopped">Stopped</option>
          </select>
        </div>

        {filtered.length === 0 ? (
          <div className="empty">
            <b>No incidents match your filter</b>
            <br />
            Clear the search query or start Chaos Mode to inject a new failure.
          </div>
        ) : (
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
                {filtered.map((r) => {
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
                          <span style={{ color: 'var(--cy)' }}>{r.active_agent}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

