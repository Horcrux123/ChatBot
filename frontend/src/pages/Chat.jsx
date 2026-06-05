import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, LogOut, ArrowRight, MessageSquare, Briefcase, Users, PieChart, Sparkles } from 'lucide-react';
import { apiClient } from '../api/client';
import MessageBubble from '../components/MessageBubble';
import ConfirmModal from '../components/ConfirmModal';
import LoadingDots from '../components/LoadingDots';

// Helper to generate a UUID v4 session ID
function getOrCreateSessionId() {
  let sid = localStorage.getItem('zoho_chat_session_id');
  if (!sid) {
    sid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
    localStorage.setItem('zoho_chat_session_id', sid);
  }
  return sid;
}

export default function Chat() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am your Zoho Projects AI Assistant. How can I help you manage your projects today?',
      agent_type: 'query'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [sessionId] = useState(getOrCreateSessionId);

  const messagesEndRef = useRef(null);

  // Check authentication on mount
  useEffect(() => {
    async function initAuth() {
      try {
        const profile = await apiClient.checkAuth();
        setUser(profile);
      } catch (err) {
        console.error('Auth check failed, redirecting to login...', err);
        navigate('/login');
      }
    }
    initAuth();
  }, [navigate]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Sends standard user message
  const handleSend = async (textToSend = input) => {
    const trimmed = textToSend.trim();
    if (!trimmed || isLoading) return;

    setInput('');
    setIsLoading(true);

    // 1. Add user message locally
    const userMsg = { role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMsg]);

    try {
      // 2. Dispatch to API
      const response = await apiClient.sendMessage(trimmed, sessionId);
      
      // 3. Process reply
      if (response.requires_confirmation) {
        setPendingAction(response.pending_action);
      }
      
      const botMsg = {
        role: 'assistant',
        content: response.reply,
        agent_type: response.agent_type
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}`, agent_type: 'query' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handles confirmation modal approvals
  const handleConfirmAction = async () => {
    setPendingAction(null);
    setIsLoading(true);

    try {
      // Send message with confirmed: true
      const response = await apiClient.sendMessage('', sessionId, true);
      
      // Append confirmation result
      const botMsg = {
        role: 'assistant',
        content: response.reply,
        agent_type: response.agent_type
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Execution failed: ${err.message}`, agent_type: 'action' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handles confirmation modal rejections
  const handleCancelAction = async () => {
    setPendingAction(null);
    setIsLoading(true);

    try {
      // Send message with confirmed: false
      const response = await apiClient.sendMessage('', sessionId, false);
      
      const botMsg = {
        role: 'assistant',
        content: response.reply,
        agent_type: response.agent_type
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await apiClient.logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const sampleChips = [
    { text: 'What projects do I have?', icon: <Briefcase size={14} /> },
    { text: 'Show tasks for the first project', icon: <MessageSquare size={14} /> },
    { text: 'Who has the most tasks this month?', icon: <PieChart size={14} /> },
    { text: 'Create task API Integration', icon: <Sparkles size={14} /> }
  ];

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      backgroundColor: 'var(--bg-primary)',
      fontFamily: 'var(--font-primary)',
      overflow: 'hidden'
    }}>
      {/* Sidebar Panel */}
      <div className="glass" style={{
        width: '300px',
        borderRight: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '24px',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* Logo Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
              borderRadius: '8px',
              padding: '6px',
              display: 'flex'
            }}>
              <Sparkles size={20} color="#fff" />
            </div>
            <h2 style={{ fontSize: '1.25rem', color: '#fff', fontFamily: 'var(--font-display)', fontWeight: 700 }}>
              Zoho Projects AI
            </h2>
          </div>

          {/* Quick Info */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
              Connection
            </div>
            {user && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <span style={{ fontSize: '0.88rem', color: '#fff', fontWeight: 500 }}>{user.email}</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--status-success)' }}>● Authenticated</span>
              </div>
            )}
            
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginTop: '16px' }}>
              Current Session
            </div>
            <span style={{
              fontFamily: 'monospace',
              fontSize: '0.75rem',
              color: 'var(--text-secondary)',
              background: 'rgba(255, 255, 255, 0.04)',
              padding: '8px',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              wordBreak: 'break-all'
            }}>
              {sessionId}
            </span>
          </div>
        </div>

        {/* Logout Control */}
        <button 
          className="btn btn-secondary" 
          onClick={handleLogout}
          style={{ width: '100%', display: 'flex', justifyContent: 'center' }}
        >
          <LogOut size={16} /> Logout
        </button>
      </div>

      {/* Main Workspace */}
      <div style={{
        flexGrow: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative'
      }}>
        {/* Messages Feed */}
        <div style={{
          flexGrow: 1,
          overflowY: 'auto',
          padding: '40px 30px',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{ maxWidth: '800px', width: '100%', margin: '0 auto' }}>
            {messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))}
            
            {isLoading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '18px' }}>
                <LoadingDots />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Interface */}
        <div style={{
          padding: '24px 30px 40px 30px',
          background: 'linear-gradient(to top, var(--bg-primary) 80%, transparent)'
        }}>
          <div style={{ maxWidth: '800px', width: '100%', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            {/* Quick Action Chips */}
            {messages.length === 1 && (
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', animation: 'fadeIn 0.4s' }}>
                {sampleChips.map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(chip.text)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '8px 14px',
                      borderRadius: '20px',
                      backgroundColor: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid var(--border-color)',
                      color: 'var(--text-secondary)',
                      fontSize: '0.82rem',
                      cursor: 'pointer',
                      transition: 'all var(--transition-fast)'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.3)';
                      e.currentTarget.style.backgroundColor = 'rgba(99, 102, 241, 0.05)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--border-color)';
                      e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.03)';
                    }}
                  >
                    {chip.icon}
                    {chip.text}
                  </button>
                ))}
              </div>
            )}

            {/* Main Input Box */}
            <form 
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="glass"
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '8px 12px 8px 18px',
                borderRadius: '14px',
                border: '1px solid var(--border-color)',
                backgroundColor: 'rgba(22, 29, 48, 0.5)',
                transition: 'border-color var(--transition-fast)'
              }}
              onFocusCapture={(e) => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
              onBlurCapture={(e) => e.currentTarget.style.borderColor = 'var(--border-color)'}
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about your projects, create tasks or request utilisation reports..."
                disabled={isLoading}
                style={{
                  flexGrow: 1,
                  background: 'none',
                  border: 'none',
                  color: '#fff',
                  fontSize: '0.98rem',
                  outline: 'none',
                  padding: '8px 0'
                }}
              />
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={!input.trim() || isLoading}
                style={{
                  padding: '8px 12px',
                  borderRadius: '10px',
                  opacity: (!input.trim() || isLoading) ? 0.5 : 1,
                  cursor: (!input.trim() || isLoading) ? 'not-allowed' : 'pointer'
                }}
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Confirmation Overlay Modal */}
      <ConfirmModal
        pendingAction={pendingAction}
        onConfirm={handleConfirmAction}
        onCancel={handleCancelAction}
      />
    </div>
  );
}
