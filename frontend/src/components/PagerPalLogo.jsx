import React from 'react';

/**
 * PagerPalLogoIcon
 * Compact official PagerPal shield symbol with pulse "P".
 * Used in sidebar, header, navigation, and compact UI locations.
 */
export function PagerPalLogoIcon({ size = 32, style = {}, className = '', glow = true }) {
  return (
    <div
      className={`pagerpal-logo-icon ${className}`}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        position: 'relative',
        filter: glow ? 'drop-shadow(0 0 8px rgba(0, 217, 255, 0.45))' : 'none',
        ...style
      }}
    >
      <img
        src="/branding/pagerpal-shield.png"
        alt="PagerPal Shield Logo"
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          borderRadius: '4px'
        }}
      />
    </div>
  );
}

/**
 * PagerPalLogoFull
 * Full official PagerPal logo composition with orbital AI agent illustrations,
 * central shield, and "AI-POWERED INCIDENT RESPONSE · Detect • Investigate • Resolve" tagline.
 */
export function PagerPalLogoFull({ maxWidth = '620px', className = '', style = {}, showBorder = true }) {
  return (
    <div
      className={`pagerpal-logo-full ${className}`}
      style={{
        width: '100%',
        maxWidth,
        margin: '0 auto',
        borderRadius: '14px',
        overflow: 'hidden',
        border: showBorder ? '1px solid var(--border)' : 'none',
        background: 'var(--card)',
        boxShadow: '0 12px 36px rgba(0, 0, 0, 0.65), 0 0 24px rgba(0, 217, 255, 0.1)',
        position: 'relative',
        ...style
      }}
    >
      <img
        src="/branding/pagerpal-brand-full.jpg"
        alt="PagerPal — AI-Powered Autonomous Incident Response"
        style={{
          width: '100%',
          height: 'auto',
          display: 'block',
          objectFit: 'cover'
        }}
      />
    </div>
  );
}

/**
 * PagerPalWordmark
 * Horizontal branding badge with shield and typography.
 */
export function PagerPalBrandBadge({ height = 34, showTagline = true }) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
      <PagerPalLogoIcon size={height} />
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ 
          fontFamily: "'Sora', sans-serif", 
          fontWeight: 700, 
          fontSize: '15px', 
          color: '#FFFFFF',
          letterSpacing: '-0.01em',
          lineHeight: 1.2
        }}>
          PagerPal
        </span>
        {showTagline && (
          <span style={{ 
            fontSize: '9.5px', 
            textTransform: 'uppercase', 
            letterSpacing: '0.12em', 
            color: 'var(--cyan)', 
            fontWeight: 600 
          }}>
            AI SRE Console
          </span>
        )}
      </div>
    </div>
  );
}
