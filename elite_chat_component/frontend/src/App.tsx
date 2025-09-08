import React, { useState, useCallback, useEffect } from 'react';
import { Streamlit, RenderData } from "streamlit-component-lib";
import ReactMarkdown from 'react-markdown';
import './ChatApp.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Args {
  messages?: Message[];
  user_name?: string;
  session_id?: string;
}

// Create a standalone mode for development and a connected mode for Streamlit
const isStreamlit = window.parent !== window;

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Welcome to Elite Auto Sales Academy. Use the commands from the sidebar (e.g., Scripts & Templates) or type your message below.' }
  ]);
  const [prompt, setPrompt] = useState('');
  const [userName, setUserName] = useState('User');
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true); // Set to true to show sidebar by default
  const [showModal, setShowModal] = useState(true); // Show modal by default for both standalone and Streamlit
  const [args, setArgs] = useState<Args>({});
  
  // Initialize Streamlit communication
  useEffect(() => {
    if (isStreamlit) {
      console.log("Running in Streamlit!");
      
      // This is the key fix - make sure setFrameHeight is called AFTER the component renders
      const resizeFrame = () => {
        setTimeout(() => {
          console.log("Setting frame height");
          Streamlit.setFrameHeight(800);
        }, 10);
      };
      
      // Subscribe to Streamlit events
      const onRender = (event: Event): void => {
        console.log("Render event received");
        const data = (event as CustomEvent<RenderData>).detail;
        setArgs(data.args as unknown as Args);
        resizeFrame();
      };
      
      // Set up the event listener
      Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
      
      // Signal that the component is ready to receive events
      console.log("Setting component ready");
      Streamlit.setComponentReady();
      
      // Initial frame resize
      resizeFrame();
      
      // Cleanup
      return () => {
        Streamlit.events.removeEventListener(Streamlit.RENDER_EVENT, onRender);
      };
    }
  }, []);
  
  // Update from Streamlit args
  useEffect(() => {
    if (isStreamlit && args) {
      if (args.messages && args.messages.length > 0) {
        setMessages(args.messages);
        setIsLoading(false);
      }
      
      if (args.user_name) {
        setUserName(args.user_name);
        // If we receive a user name from Streamlit, we can hide the modal
        if (args.user_name.trim() && args.user_name !== 'User') {
          setShowModal(false);
        }
      }
    }
  }, [args]);

  const mockResponse = (message: string) => {
    // For standalone demo: simulate a response when not in Streamlit
    if (!isStreamlit) {
      setTimeout(() => {
        let response = 'Thank you for your message. This is a standalone demo mode without backend connection.';
        
        if (message.startsWith('!')) {
          response = `You've used a command: ${message}. In the full version, this would trigger specific training content.`;
        }
        
        setMessages(prev => [...prev, { role: 'assistant', content: response }]);
        setIsLoading(false);
      }, 1000);
    }
  };

  const sendMessage = useCallback((message: string) => {
    if (!message.trim() || isLoading) return;
    
    // Add user message to the chat (in standalone mode only)
    if (!isStreamlit) {
      setMessages(prev => [...prev, { role: 'user', content: message }]);
    }
    
    setIsLoading(true);
    
    if (isStreamlit) {
      // Send to Streamlit
      Streamlit.setComponentValue({
        action: 'send_message',
        message: message,
        user_name: userName
      });
    } else {
      // Mock response in standalone mode
      mockResponse(message);
    }
  }, [isLoading, userName]);

  const sendCommand = useCallback((command: string) => {
    setIsLoading(true);
    
    // Add command as user message (in standalone mode only)
    if (!isStreamlit) {
      setMessages(prev => [...prev, { role: 'user', content: command }]);
    }
    
    if (isStreamlit) {
      // Send to Streamlit
      Streamlit.setComponentValue({
        action: 'send_command',
        command: command,
        user_name: userName
      });
    } else {
      // Mock response in standalone mode
      mockResponse(command);
    }
  }, [userName]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim()) {
      sendMessage(prompt);
      setPrompt('');
    }
  };

  const closeModal = (skip = false) => {
    setShowModal(false);
    if (skip) {
      setUserName('User');
      // Send the default name to Streamlit if we're in Streamlit mode
      if (isStreamlit) {
        Streamlit.setComponentValue({
          action: 'set_name',
          user_name: 'User'
        });
      }
    }
  };

  const submitName = (name: string) => {
    if (name.trim()) {
      const trimmedName = name.trim();
      setUserName(trimmedName);
      setShowModal(false);
      
      // Send the name to Streamlit if we're in Streamlit mode
      if (isStreamlit) {
        console.log("Sending name to Streamlit:", trimmedName);
        Streamlit.setComponentValue({
          action: 'set_name',
          user_name: trimmedName
        });
      }
    }
  };

  // Force consistent colors regardless of theme
  const forceConsistentStyle = {
    color: 'var(--elite-text)',
    backgroundColor: 'var(--elite-white)',
    colorScheme: 'light' // Ensure select elements also use light theme
  };

  return (
    <div className="chat-container" style={forceConsistentStyle}>
      {/* Header */}
      <header className="chat-header">
        <div className="header-content">
          <div className="header-left">
            {/* Sidebar toggle button */}
            <button 
              className="sidebar-toggle" 
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? '◀ Hide Menu' : '▶ Show Menu'}
            </button>
            
            {/* Logo 1 - Client signature (AG_T_logo.png) */}
            <img 
              src="AG_T_logo.png" 
              alt="AG Goldsmith" 
              className="header-logo client-logo"
              style={{ maxHeight: '60px', marginRight: '20px' }}
            />
            <div className="brand">
              <h2>Sales Coach AI</h2>
              <p>Elite Auto Sales Academy Bot <span className="elite-chip">powered by AG Goldsmith</span></p>
            </div>
          </div>
          {/* Logo 2 - Product logo (logo_1.png) */}
          <img 
            src="logo_1.png" 
            alt="Product Logo" 
            className="header-logo product-logo"
            style={{ maxHeight: '80px' }}
          />
        </div>
      </header>

      <div className="chat-layout">
        {/* Sidebar */}
        <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
          <div className="sidebar-content">
            <div className="sidebar-header">
              <h2>AG Bot • Controls</h2>
            </div>

            {/* Message Mastery */}
            <div className="sidebar-section">
              <h3>Message Mastery</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!scripts')}>!scripts</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!trust')}>!trust</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!tonality')}>!tonality</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!firstimpression')}>!firstimpression</button>
            </div>
            
            <div className="sidebar-divider"></div>
            
            {/* Closer Moves */}
            <div className="sidebar-section">
              <h3>Closer Moves</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!pvf')}>!pvf</button>
            </div>

            <div className="sidebar-divider"></div>

            {/* Objection Handling */}
            <div className="sidebar-section">
              <h3>Objection Handling</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection price')}>!objection price</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection paymenttoohigh')}>!objection paymenttoohigh</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection tradevalue')}>!objection tradevalue</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection thinkaboutit')}>!objection thinkaboutit</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection shoparound')}>!objection shoparound</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection spouse')}>!objection spouse</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection paymentvsprice')}>!objection paymentvsprice</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection timingstall')}>!objection timingstall</button>
            </div>
            
            <div className="sidebar-divider"></div>
            
            {/* Roleplay Scenarios */}
            <div className="sidebar-section">
              <h3>Role-Play Scenarios</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!roleplay price')}>!roleplay price</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!roleplay trade')}>!roleplay trade</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!roleplay think')}>!roleplay think</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!roleplay shop')}>!roleplay shop</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!roleplay spouse')}>!roleplay spouse</button>
            </div>
            
            <div className="sidebar-divider"></div>
            
            {/* Money Momentum */}
            <div className="sidebar-section">
              <h3>Money Momentum</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!dailylog')}>!dailylog</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!earn')}>!earn</button>
            </div>
            
            <div className="sidebar-divider"></div>
            
            {/* Five Emotional Checkpoints */}
            <div className="sidebar-section">
              <h3>Five Emotional Checkpoints</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!checkpoints')}>!checkpoints</button>
            </div>
            
            <div className="sidebar-divider"></div>
            
            {/* Coaching Resources */}
            <div className="sidebar-section">
              <h3>Coaching Resources</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!coaching')}>!coaching</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!coaching tips')}>!coaching tips</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!coaching roleplay')}>!coaching roleplay</button>
            </div>
            
            <div className="sidebar-divider"></div>
            
            {/* Quick Actions */}
            <div className="sidebar-section">
              <h3>Quick Actions</h3>
              <div className="quick-actions">
                <button className="sidebar-btn small" onClick={() => sendCommand('continue')}>Continue</button>
                <button className="sidebar-btn small" onClick={() => sendCommand('restart')}>Restart</button>
                <button className="sidebar-btn small" onClick={() => sendCommand('end')}>End</button>
              </div>
            </div>
          </div>
        </aside>
        
        {/* Overlay for mobile - closes sidebar when clicked */}
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)}></div>

        {/* Main Chat */}
        <main className="chat-main">
          <div className="messages" style={forceConsistentStyle}>
            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.role}`} style={{color: 'var(--elite-text)'}}>
                {msg.content.startsWith("COACHING_TIP:") && (
                  <div className="coaching-tip">
                    <div className="coaching-tip-header">
                      <span className="coaching-icon">💡</span>
                      <h4>Coaching Tip</h4>
                    </div>
                    <p>{msg.content.match(/COACHING_TIP:([\s\S]+?)END_COACHING_TIP/)?.[1].trim() || ""}</p>
                  </div>
                )}
                
                {msg.content.includes("ROLE_PLAY_LEVEL:") && (
                  <div className="role-play-level">
                    Role-Play Depth: Level {msg.content.match(/ROLE_PLAY_LEVEL:(\d+)END_ROLE_PLAY_LEVEL/)?.[1] || "1"}
                  </div>
                )}
                
                {msg.role === 'assistant' ? (
                  <div className="markdown-content" style={{color: 'var(--elite-text)'}}>
                    <ReactMarkdown>
                      {msg.content
                        .replace(/COACHING_TIP:[\s\S]+?END_COACHING_TIP/, '')
                        .replace(/ROLE_PLAY_LEVEL:\d+END_ROLE_PLAY_LEVEL/, '')
                        .trim()}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p style={{color: 'var(--elite-text)'}}>{msg.content}</p>
                )}
              </div>
            ))}
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Type a command or message…"
              disabled={isLoading}
              className="message-input"
            />
            <button type="submit" disabled={isLoading || !prompt.trim()} className="send-btn">
              {isLoading ? '...' : 'Send'}
            </button>
          </form>
        </main>
      </div>

      {/* Name Modal */}
      {showModal && (
        <div className="modal">
          <div className="modal-content" style={forceConsistentStyle}>
            <h3 style={{color: 'var(--elite-blue)'}}>Welcome to Training!</h3>
            <p style={{color: 'var(--elite-text)'}}>Please enter your name to begin your personalized sales training experience.</p>
            
            <form onSubmit={(e) => {
              e.preventDefault();
              const input = e.currentTarget.querySelector('input') as HTMLInputElement;
              submitName(input.value);
            }}>
              <label>Your Name</label>
              <input 
                type="text" 
                placeholder="Enter your full name" 
                required
                autoComplete="name"
              />
              
              <div className="modal-actions">
                <button type="button" onClick={() => closeModal(true)} className="btn-secondary">
                  Skip
                </button>
                <button type="submit" className="btn-primary">
                  Start Training
                </button>
              </div>
            </form>
            
            <p className="modal-note">Your name helps us personalize your training experience.</p>
          </div>
        </div>
      )}
    </div>
  );
};

// Export component
export default App;
