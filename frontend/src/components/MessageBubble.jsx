import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Cpu } from 'lucide-react';

export default function MessageBubble({ message }) {
  const { role, content, agent_type } = message;
  const isUser = role === 'user';

  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: '18px',
      gap: '12px',
      alignItems: 'flex-start',
      maxWidth: '100%',
      animation: 'fadeIn 0.22s ease-out forwards'
    }}>
      {!isUser && (
        <div style={{
          background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
          borderRadius: '10px',
          width: '36px',
          height: '36px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          boxShadow: 'var(--shadow-sm)'
        }}>
          <Cpu size={18} color="#fff" />
        </div>
      )}

      <div style={{
        maxWidth: '75%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start'
      }}>
        {/* Agent Badge */}
        {!isUser && agent_type && (
          <div style={{
            fontSize: '0.72rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            padding: '2px 8px',
            borderRadius: '4px',
            marginBottom: '6px',
            fontFamily: 'var(--font-display)',
            backgroundColor: agent_type === 'action' ? 'rgba(168, 85, 247, 0.15)' : 'rgba(99, 102, 241, 0.15)',
            color: agent_type === 'action' ? '#c084fc' : '#818cf8',
            border: agent_type === 'action' ? '1px solid rgba(168, 85, 247, 0.3)' : '1px solid rgba(99, 102, 241, 0.3)',
          }}>
            {agent_type === 'action' ? 'Action Agent' : 'Query Agent'}
          </div>
        )}

        <div style={{
          backgroundColor: isUser ? 'var(--accent-primary)' : 'var(--bg-secondary)',
          color: '#ffffff',
          borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
          padding: '12px 18px',
          boxShadow: 'var(--shadow-sm)',
          border: isUser ? 'none' : '1px solid var(--border-color)',
          fontSize: '0.96rem',
          lineHeight: '1.5'
        }}>
          <div className="prose">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        </div>
      </div>

      {isUser && (
        <div style={{
          backgroundColor: 'rgba(255, 255, 255, 0.06)',
          borderRadius: '10px',
          width: '36px',
          height: '36px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          border: '1px solid var(--border-color)'
        }}>
          <User size={18} color="var(--text-primary)" />
        </div>
      )}
    </div>
  );
}
