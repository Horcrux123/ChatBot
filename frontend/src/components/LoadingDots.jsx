import React from 'react';

export default function LoadingDots() {
  return (
    <div className="flex items-center gap-1.5 p-2 px-4 bg-tertiary/40 border border-white/5 rounded-2xl w-fit animate-pulse" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginRight: '4px', fontFamily: 'var(--font-display)' }}>
        AI is thinking
      </span>
      <div style={{ display: 'flex', gap: '4px', alignItems: 'center', marginTop: '2px' }}>
        <div style={{
          width: '6px',
          height: '6px',
          backgroundColor: 'var(--accent-primary)',
          borderRadius: '50%',
          animation: 'pulse 1.4s infinite both',
          animationDelay: '0s'
        }} />
        <div style={{
          width: '6px',
          height: '6px',
          backgroundColor: 'var(--accent-primary)',
          borderRadius: '50%',
          animation: 'pulse 1.4s infinite both',
          animationDelay: '0.2s'
        }} />
        <div style={{
          width: '6px',
          height: '6px',
          backgroundColor: 'var(--accent-primary)',
          borderRadius: '50%',
          animation: 'pulse 1.4s infinite both',
          animationDelay: '0.4s'
        }} />
      </div>
      
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(0.6); opacity: 0.4; }
          50% { transform: scale(1.1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
