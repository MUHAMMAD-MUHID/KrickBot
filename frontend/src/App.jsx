import React, { useState, useRef, useEffect } from 'react';
import { Bot, User, Send, Plus, MessageSquare, Settings, BarChart2, BookOpen, Users, Trophy } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatContainerRef = useRef(null);

  // Scroll to bottom on new message
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
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
        body: JSON.stringify({ query: text }),
      });

      if (!res.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await res.json();
      
      const botMessage = {
        role: 'bot',
        content: data.response,
        intent: data.intent,
        context: data.context
      };
      
      setMessages((prev) => [...prev, botMessage]);
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
    handleSend();
  };

  const setSuggestion = (text) => {
    handleSend(text);
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
        <button className="new-chat-btn" onClick={() => setMessages([])}>
          <Plus size={18} /> New chat
        </button>
        <div className="chat-history">
          <p className="history-label">Recent</p>
          <ul className="history-list">
            <li><MessageSquare size={16} /> Babar Azam stats</li>
            <li><MessageSquare size={16} /> World Cup 2023 summary</li>
          </ul>
        </div>
        <div className="sidebar-footer">
          <button className="settings-btn">
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
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                    {msg.intent && (
                      <div className="metadata">Intent: {msg.intent}</div>
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
    </div>
  );
}

export default App;
