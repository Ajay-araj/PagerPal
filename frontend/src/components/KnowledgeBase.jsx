import React, { useState } from 'react';
import { Search, BookOpen, AlertCircle, ShieldCheck, CheckCircle2 } from 'lucide-react';

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
          <h1>SQLite Operational Knowledge Base</h1>
          <p>
            Historical incident runbooks, verified remediations, and causal resolutions persisted in SQLite.
          </p>
        </div>
      </div>

      <div className="note" style={{ borderColor: 'var(--border)', background: 'var(--elevated)', color: 'var(--text)' }}>
        <AlertCircle size={16} style={{ flexShrink: 0, color: 'var(--cyan)' }} />
        <span>
          <b>HARD SAFETY RULE 8:</b> Past incidents serve strictly as reference suggestions. PagerPal never automatically reapplies a past fix without fresh empirical evidence verification and independent Policy Engine evaluation.
        </span>
      </div>

      <div className="pn">
        <div className="tools">
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              size={15}
              style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text2)'
              }}
            />
            <input
              type="text"
              aria-label="Search knowledge base"
              placeholder="Search symptoms, root causes, or runbook remediations..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ width: '100%', paddingLeft: '36px' }}
            />
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="empty">
            <BookOpen size={40} style={{ color: 'var(--text2)', margin: '0 auto 12px', opacity: 0.5 }} />
            <b style={{ color: '#FFFFFF', display: 'block' }}>No Knowledge Base Records Found</b>
          </div>
        ) : (
          <div className="sc">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Incident & Symptoms</th>
                  <th>Root Cause</th>
                  <th>Approved Runbook Fix</th>
                  <th>Human Approval</th>
                  <th>Verified Recovery</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td className="id">{item.id}</td>
                    <td>
                      <b style={{ color: '#FFFFFF' }}>{item.title}</b>
                      <br />
                      <span className="mono" style={{ color: 'var(--text2)', fontSize: '11.5px' }}>
                        {item.service} · {item.symptoms}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text)' }}>{item.root_cause}</td>
                    <td style={{ color: 'var(--cyan)', fontWeight: 600 }}>{item.fix}</td>
                    <td>
                      <span className="b grn"> {item.approval_status}</span>
                    </td>
                    <td>
                      <span className="b grn"> {item.recovery_status}</span>
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
