import React from 'react';
import { AlertTriangle, Check, X } from 'lucide-react';

export default function ConfirmModal({ pendingAction, onConfirm, onCancel }) {
  if (!pendingAction) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(5, 8, 16, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      animation: 'fadeIn 0.2s ease-out'
    }}>
      <div className="glass-card animate-slide-in" style={{
        maxWidth: '480px',
        width: '90%',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        padding: '28px',
        border: '1px solid rgba(255, 255, 255, 0.12)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            backgroundColor: 'rgba(245, 158, 11, 0.15)',
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <AlertTriangle color="var(--status-warning)" size={22} />
          </div>
          <h3 style={{ fontSize: '1.25rem', color: '#fff', fontFamily: 'var(--font-display)' }}>
            Confirm Action Required
          </h3>
        </div>

        <p style={{
          color: 'var(--text-secondary)',
          fontSize: '0.96rem',
          lineHeight: '1.6',
          backgroundColor: 'var(--bg-secondary)',
          padding: '16px',
          borderRadius: '10px',
          border: '1px solid var(--border-color)',
          fontFamily: 'var(--font-primary)'
        }}>
          {pendingAction.human_readable}
        </p>

        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '12px',
          marginTop: '8px'
        }}>
          <button className="btn btn-secondary" onClick={onCancel} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <X size={16} /> Cancel
          </button>
          <button className="btn btn-success" onClick={onConfirm} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Check size={16} /> Confirm Action
          </button>
        </div>
      </div>
    </div>
  );
}
