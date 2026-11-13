import React, { useState } from 'react';
import { Search, BookOpen, AlertCircle } from 'lucide-react';

export function KnowledgeBase({ items }) {
  const [query, setQuery] = useState('');

  const filtered = (items || []).filter((item) => {
    if (!query) return true;
    const term = query.toLowerCase();
    return (
      item.id.toLowerCase().includes(term) ||
      item.title.toLowerCase().includes(term) ||
      item.symptoms.toLowerCase().includes(term) ||
      item.root_cause.toLowerCase().includes(term) ||
      item.fix.toLowerCase().includes(term)
    );
  });

  return (
    <div>
      <div className="hd">
        <div>
          <h1>Knowledge base</h1>
          <p>
            Historical incident runbooks and verified resolutions stored in SQLite.
          </p>
        </div>
      </div>

      <div className="note" style={{ borderColor: 'var(--cy)', background: '#0a1d2e', color: '#bce4ff' }}>
        <AlertCircle size={16} style={{ flexShrink: 0 }} />
        <span>
          Past incidents serve as reference suggestions only. PagerPal never automatically reapplies a past fix without fresh evidence correlation and policy engine evaluation.
        </span>
      </div>

      <div className="pn">
        <div className="tools">
          <div style={{ position: 'relative', flex: 1 }}>
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
              aria-label="Search knowledge base"
              placeholder="Search symptoms, root causes, or runbook fixes..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ width: '100%', paddingLeft: '32px' }}
            />
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="empty">
            <BookOpen size={36} style={{ color: 'var(--mu)', margin: '0 auto 8px' }} />
            <b>No knowledge base items match your query</b>
          </div>
        ) : (
          <div className="sc">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Incident & Symptoms</th>
                  <th>Root cause</th>
                  <th>Approved fix</th>
                  <th>Human approval</th>
                  <th>Verified recovery</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td className="id">{item.id}</td>
                    <td>
                      <b>{item.title}</b>
                      <br />
                      <span className="sub mono" style={{ color: 'var(--mu)' }}>
                        {item.service} · {item.symptoms}
                      </span>
                    </td>
                    <td>{item.root_cause}</td>
                    <td style={{ color: 'var(--cy)' }}><b>{item.fix}</b></td>
                    <td>
                      <span className="b grn">✓ {item.approval_status}</span>
                    </td>
                    <td>
                      <span className="b grn">✓ {item.recovery_status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

