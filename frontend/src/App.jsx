import React, { useState, useRef, useEffect } from 'react';
import { Bot, User, Send, Plus, MessageSquare, Settings, BarChart2, BookOpen, Users, Trophy, X, Trash2, Copy, Edit2, RefreshCw } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(localStorage.getItem('sessionId') || null);
  const [sessions, setSessions] = useState([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editDraft, setEditDraft] = useState('');
  const chatContainerRef = useRef(null);

  const fetchSessions = async () => {
    try {
      const res = await fetch('http://localhost:8000/chats');
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  };

  // Fetch all sessions on load
  useEffect(() => {
    fetchSessions();
  }, []);

  // Fetch chat history on load if session exists
  useEffect(() => {
    if (sessionId) {
      fetch(`http://localhost:8000/chat/${sessionId}`)
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data && data.messages) {
            const history = data.messages.map(msg => ({
              id: msg.id,
              role: msg.role,
              content: msg.content,
              intent: msg.intent
            }));
            setMessages(history);
          }
        })
        .catch(err => console.error("Failed to load chat history:", err));
    }
  }, [sessionId]);

  const loadSession = (id) => {
    setSessionId(id);
    localStorage.setItem('sessionId', id);
  };

  // Scroll to bottom smoothly on new message
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, isLoading]);

  const handleSend = async (text = input) => {
    if (!text.trim()) return;

    const userMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: text, session_id: sessionId }),
      });

      if (!res.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await res.json();
      
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
        localStorage.setItem('sessionId', data.session_id);
      }
      
      const historyRes = await fetch(`http://localhost:8000/chat/${data.session_id}`);
      if (historyRes.ok) {
        const historyData = await historyRes.json();
        if (historyData && historyData.messages) {
          const history = historyData.messages.map(msg => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            intent: msg.intent
          }));
          setMessages(history);
        }
      } else {
        // Fallback if history fetch fails
        const botMessage = {
          role: 'bot',
          content: data.response,
          intent: data.intent,
          context: data.context
        };
        setMessages((prev) => [...prev, botMessage]);
      }
      fetchSessions(); // Refresh sidebar
    } catch (error) {
      console.error('Error fetching chat:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'bot', content: 'Sorry, I encountered an error. Make sure the backend server is running.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isLoading) return;
    handleSend();
  };

  const setSuggestion = (text) => {
    handleSend(text);
  };

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
  };

  const handleEditSubmit = async (messageId, newText) => {
    if (!newText.trim() || isLoading) return;
    setEditingMessageId(null);
    
    // Truncate backend history
    try {
      await fetch(`http://localhost:8000/chat/${sessionId}/truncate/${messageId}`, {
        method: 'DELETE'
      });
    } catch (e) {
      console.error("Failed to truncate chat:", e);
      return;
    }

    // Update frontend state immediately to remove trailing messages
    const messageIndex = messages.findIndex(m => m.id === messageId);
    if (messageIndex !== -1) {
      setMessages(messages.slice(0, messageIndex));
    }
    
    // Resend
    handleSend(newText);
  };

  const handleRegenerate = async (botMsgIndex) => {
    if (isLoading || botMsgIndex <= 0) return;
    const userMsg = messages[botMsgIndex - 1];
    if (userMsg.role !== 'user' || !userMsg.id) return;
    
    await handleEditSubmit(userMsg.id, userMsg.content);
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <Bot />
            <span>KrickBot</span>
          </div>
        </div>
        <button className="new-chat-btn" onClick={() => {
          setMessages([]);
          setSessionId(null);
          localStorage.removeItem('sessionId');
        }}>
          <Plus size={18} /> New chat
        </button>
        <div className="chat-history">
          <p className="history-label">Recent</p>
          <ul className="history-list">
            {sessions.map(s => (
              <li 
                key={s.id} 
                onClick={() => loadSession(s.id)}
                className={s.id === sessionId ? 'active-session' : ''}
              >
                <MessageSquare size={16} /> {s.preview}
              </li>
            ))}
          </ul>
        </div>
        <div className="sidebar-footer">
          <button className="settings-btn" onClick={() => setIsSettingsOpen(true)}>
            <Settings size={18} /> Settings
          </button>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="chat-main">
        <header className="mobile-header">
          <div className="logo">
            <Bot />
            <span>KrickBot</span>
          </div>
        </header>

        <div className="chat-container" ref={chatContainerRef}>
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-logo">
                <Bot size={48} />
              </div>
              <h1>How can I help you with cricket today?</h1>
              <div className="suggestion-cards">
                <div className="card" onClick={() => setSuggestion('How many centuries has Babar Azam scored?')}>
                  <p className="card-text">How many centuries has Babar Azam scored?</p>
                  <BarChart2 className="card-icon" />
                </div>
                <div className="card" onClick={() => setSuggestion('Explain the rules of a super over')}>
                  <p className="card-text">Explain the rules of a super over</p>
                  <BookOpen className="card-icon" />
                </div>
                <div className="card" onClick={() => setSuggestion('Compare Shaheen Afridi and Haris Rauf')}>
                  <p className="card-text">Compare Shaheen Afridi and Haris Rauf</p>
                  <Users className="card-icon" />
                </div>
                <div className="card" onClick={() => setSuggestion('Who won the last PSL?')}>
                  <p className="card-text">Who won the last PSL?</p>
                  <Trophy className="card-icon" />
                </div>
              </div>
            </div>
          ) : (
            <div className="messages-area">
              {messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                  <div className="avatar">
                    {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                  </div>
                  <div className="message-content">
                    {editingMessageId === msg.id && msg.role === 'user' ? (
                      <div className="edit-container">
                        <textarea
                          className="edit-textarea"
                          value={editDraft}
                          onChange={(e) => setEditDraft(e.target.value)}
                          rows={3}
                        />
                        <div className="edit-actions">
                          <button className="edit-cancel-btn" onClick={() => setEditingMessageId(null)}>Cancel</button>
                          <button className="edit-save-btn" onClick={() => handleEditSubmit(msg.id, editDraft)} disabled={isLoading}>Save & Submit</button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <ReactMarkdown 
                          remarkPlugins={[remarkGfm]}
                          components={{
                            code({node, inline, className, children, ...props}) {
                              const match = /language-(\w+)/.exec(className || '')
                              if (!inline && match && match[1] === 'chart') {
                                try {
                                  const data = JSON.parse(String(children).replace(/\n$/, ''));
                                  const keys = Object.keys(data[0] || {});
                                  const xAxisKey = keys[0];
                                  const barKey = keys[1];
                                  
                                  return (
                                    <div className="chart-wrapper">
                                      <ResponsiveContainer width="100%" height={250}>
                                        <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                          <XAxis dataKey={xAxisKey} stroke="var(--text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
                                          <YAxis stroke="var(--text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
                                          <Tooltip 
                                            cursor={{fill: 'var(--card-hover)'}}
                                            contentStyle={{backgroundColor: 'var(--card-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', color: 'var(--text-primary)'}}
                                            itemStyle={{color: 'var(--primary-color)'}}
                                          />
                                          <Bar dataKey={barKey} fill="var(--primary-color)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                                        </BarChart>
                                      </ResponsiveContainer>
                                    </div>
                                  );
                                } catch (e) {
                                  console.error("Chart parse error:", e);
                                }
                              }
                              return <code className={className} {...props}>{children}</code>
                            }
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                        {msg.id && (
                          <div className="message-actions">
                            <button className="action-btn" onClick={() => handleCopy(msg.content)} title="Copy text"><Copy size={14} /></button>
                            {msg.role === 'user' ? (
                              <button className="action-btn" onClick={() => { setEditingMessageId(msg.id); setEditDraft(msg.content); }} title="Edit prompt"><Edit2 size={14} /></button>
                            ) : (
                              <button className="action-btn" onClick={() => handleRegenerate(idx)} title="Regenerate response"><RefreshCw size={14} /></button>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="message bot">
                  <div className="avatar">
                    <Bot size={20} />
                  </div>
                  <div className="message-content">
                    <div className="typing-indicator">
                      <div className="dot"></div>
                      <div className="dot"></div>
                      <div className="dot"></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="input-container">
          <form className="chat-form" onSubmit={handleSubmit}>
            <div className="input-box">
              <input
                type="text"
                className="user-input"
                placeholder="Message KrickBot..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                autoComplete="off"
                disabled={isLoading}
              />
              <button
                type="submit"
                className="send-btn"
                disabled={!input.trim() || isLoading}
              >
                <Send size={18} />
              </button>
            </div>
          </form>
          <p className="disclaimer">KrickBot can make mistakes. Consider verifying important statistics.</p>
        </div>
      </main>

      {/* Settings Modal */}
      {isSettingsOpen && (
        <div className="modal-overlay" onClick={() => setIsSettingsOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Settings</h2>
              <button className="modal-close" onClick={() => setIsSettingsOpen(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1rem' }}>
                Manage your KrickBot local data and preferences.
              </p>
              <button 
                className="modal-action-btn"
                onClick={() => {
                  setMessages([]);
                  setSessionId(null);
                  localStorage.removeItem('sessionId');
                  setIsSettingsOpen(false);
                }}
              >
                <Trash2 size={18} /> Clear Local Chat History
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
