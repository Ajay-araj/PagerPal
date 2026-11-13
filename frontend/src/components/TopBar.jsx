import React from 'react';
import { ShieldCheck, AlertCircle, Zap } from 'lucide-react';

export function TopBar({ isSimBusy, onOpenChaos }) {
  return (
    <div className="top" id="top">
      <b style={{ fontFamily: "'Bricolage Grotesque', sans-serif", fontSize: '15px' }}>PagerPal</b>
      <span className="sim">SIMULATION</span>
      <span className="sub">All data is simulated · no production systems connected</span>
      <div className="sp" />
      {isSimBusy ? (
        <span className="b amb">
          <AlertCircle size={13} /> 1 incident active
        </span>
      ) : (
        <span className="b grn">
          <ShieldCheck size={13} /> All systems healthy
        </span>
      )}
      <button 
        className="btn p" 
        style={{ padding: '5px 12px', fontSize: '12px' }}
        onClick={onOpenChaos}
      >
        <Zap size={13} /> Chaos Mode
      </button>
    </div>
  );
}

