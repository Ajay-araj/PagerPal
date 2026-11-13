import React from 'react';
import { 
  LayoutDashboard, 
  AlertTriangle, 
  Radio, 
  Network, 
  BookOpen, 
  FileText, 
  Settings,
  ShieldAlert
} from 'lucide-react';

const PAGES = [
  { id: 'overview', icon: LayoutDashboard, label: 'Overview' },
  { id: 'incidents', icon: AlertTriangle, label: 'Incidents' },
  { id: 'live', icon: Radio, label: 'Live investigation' },
  { id: 'map', icon: Network, label: 'Service map' },
  { id: 'kb', icon: BookOpen, label: 'Knowledge base' },
  { id: 'reports', icon: FileText, label: 'Postmortems' },
  { id: 'settings', icon: Settings, label: 'Settings' }
];

export function Navigation({ currentPage, onNavigate, isSimBusy }) {
  return (
    <nav aria-label="Main Navigation">
      <div className="logo">
        <i>P</i>
        <div>
          <span>PagerPal</span>
          <span className="logo-sub">AI SRE Console</span>
        </div>
      </div>
      {PAGES.map((p) => {
        const Icon = p.icon;
        const isActive = currentPage === p.id || (currentPage === 'detail' && p.id === 'incidents');
        return (
          <button
            key={p.id}
            className={isActive ? 'on' : ''}
            onClick={() => onNavigate(p.id)}
            aria-current={isActive ? 'page' : undefined}
          >
            <span className="g">
              <Icon size={17} />
            </span>
            <span>{p.label}</span>
            {p.id === 'live' && isSimBusy && (
              <span 
                className="b amb" 
                style={{ 
                  marginLeft: 'auto', 
                  padding: '2px 7px', 
                  fontSize: '10px',
                  fontWeight: 700,
                  boxShadow: '0 0 10px rgba(255, 174, 66, 0.4)' 
                }}
              >
                LIVE
              </span>
            )}
          </button>
        );
      })}

      <div style={{ marginTop: 'auto', paddingTop: '20px', borderTop: '1px solid var(--border)' }}>
        <div style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '12px',
          fontSize: '11px',
          color: 'var(--text2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--cyan)', fontWeight: 600, marginBottom: '4px' }}>
            <ShieldAlert size={13} /> Policy Guard
          </div>
          <div>L2 Reversible actions locked behind human approval gate.</div>
        </div>
      </div>
    </nav>
  );
}
