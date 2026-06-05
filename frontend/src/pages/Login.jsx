import React from 'react';
import { LogIn, Zap } from 'lucide-react';

export default function Login() {
  const handleLogin = () => {
    // Redirect to backend auth login endpoint
    const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    window.location.href = `${backendUrl.replace(/\/$/, '')}/auth/login`;
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(circle at top right, rgba(99, 102, 241, 0.15), transparent), radial-gradient(circle at bottom left, rgba(168, 85, 247, 0.15), transparent), var(--bg-primary)',
      padding: '20px'
    }}>
      <div className="glass-card animate-slide-in" style={{
        maxWidth: '440px',
        width: '100%',
        textAlign: 'center',
        padding: '40px 30px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '24px'
      }}>
        {/* Brand Logo */}
        <div style={{
          background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
          borderRadius: '20px',
          width: '72px',
          height: '72px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 8px 32px rgba(99, 102, 241, 0.3)',
          animation: 'pulse 3s infinite'
        }}>
          <Zap size={36} color="#fff" />
        </div>

        <div>
          <h1 style={{
            fontSize: '2.2rem',
            fontFamily: 'var(--font-display)',
            fontWeight: 800,
            background: 'linear-gradient(to right, #fff, var(--text-secondary))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '8px'
          }}>
            Zoho Projects AI
          </h1>
          <p style={{
            color: 'var(--text-secondary)',
            fontSize: '0.98rem',
            lineHeight: '1.5',
            fontFamily: 'var(--font-primary)'
          }}>
            Manage tasks, query team utilization, and orchestrate projects using natural language.
          </p>
        </div>

        <button 
          className="btn btn-primary" 
          onClick={handleLogin}
          style={{
            width: '100%',
            padding: '14px',
            fontSize: '1.05rem',
            marginTop: '10px'
          }}
        >
          <LogIn size={20} />
          Login with Zoho
        </button>

        <span style={{
          fontSize: '0.78rem',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-primary)'
        }}>
          Securely connects via Zoho OAuth 2.0
        </span>
      </div>
    </div>
  );
}
