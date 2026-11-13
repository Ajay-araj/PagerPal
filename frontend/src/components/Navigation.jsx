import React from 'react';
import { 
  LayoutDashboard, 
  AlertTriangle, 
  Radio, 
  Network, 
  BookOpen, 
  FileText, 
  Settings 
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
    <nav aria-label="Main">
      <div className="logo">
        <i>P</i>
        <span>PagerPal</span>
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
              <Icon size={16} />
            </span>
            <span>{p.label}</span>
            {p.id === 'live' && isSimBusy && (
              <span className="b amb" style={{ marginLeft: 'auto', padding: '1px 6px', fontSize: '10px' }}>
                LIVE
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
}

