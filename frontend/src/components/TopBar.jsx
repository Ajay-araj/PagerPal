import React, { useState, useEffect } from 'react';
import { ShieldCheck, AlertCircle, Zap, Clock } from 'lucide-react';
import { PagerPalLogoIcon } from './PagerPalLogo';

export function TopBar({ isSimBusy, onOpenChaos }) {
  const [time, setTime] = useState('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTime(now.toISOString().slice(11, 19) + ' UTC');
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="top" id="top">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <PagerPalLogoIcon size={24} />
        <b style={{ fontFamily: "'Sora', sans-serif", fontSize: '15px', color: '#FFFFFF', letterSpacing: '-0.01em' }}>
          PagerPal
        </b>
        <span className="sim">SIMULATION</span>
      </div>

      <span className="sub" style={{ display: 'none', md: 'inline' }}>
        Evidence-Driven Autonomous SRE · Isolated Telemetry
      </span>

      <div className="sp" />

      {/* Clock Readout */}
      <div 
        className="mono" 
        style={{ 
          fontSize: '11px', 
          color: 'var(--text2)', 
          background: 'var(--elevated)', 
          padding: '4px 10px', 
          borderRadius: '6px',
          border: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: '5px'
        }}
      >
        <Clock size={12} style={{ color: 'var(--cyan)' }} />
        <span>{time || '00:00:00 UTC'}</span>
      </div>

      {isSimBusy ? (
        <span className="b amb" style={{ boxShadow: '0 0 12px rgba(255, 174, 66, 0.35)' }}>
          <AlertCircle size={13} /> 1 Incident In Flight
        </span>
      ) : (
        <span className="b grn" style={{ boxShadow: '0 0 12px rgba(0, 230, 160, 0.25)' }}>
          <ShieldCheck size={13} /> All Systems Operational
        </span>
      )}

      <button 
        className="btn p" 
        style={{ padding: '6px 14px', fontSize: '12.5px' }}
        onClick={onOpenChaos}
        title="Inject simulated failure scenario"
      >
        <Zap size={14} /> Chaos Mode
      </button>
    </div>
  );
}
