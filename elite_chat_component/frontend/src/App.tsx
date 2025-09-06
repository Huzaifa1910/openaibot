import React, { useState, useCallback, useEffect } from 'react';
import { Streamlit, RenderData } from "streamlit-component-lib";
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
    { role: 'assistant', content: 'Welcome to Elite Auto Sales Academy. Use the commands from the sidebar (e.g., !scripts) or type your message below.' }
  ]);
  const [prompt, setPrompt] = useState('');
  const [userName, setUserName] = useState('User');
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
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

  return (
    <div className="chat-container">
      {/* Header */}
      <header className="chat-header">
        <div className="header-content">
          <div className="header-left">
            {/* Logo 1 - Client signature (AG_T_logo.png) */}
            <img 
              src="AG_T_logo.png" 
              alt="AG Goldsmith" 
              className="header-logo client-logo"
              style={{ maxHeight: '60px', marginRight: '20px' }}
            />
            <div className="brand">
              <h2>Sales Coach AI</h2>
              <p>Elite Auto Sales Academy Bot <span className="chip">powered by AG Goldsmith</span></p>
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
            <div className="sidebar-section">
              <h3>Message Mastery</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!scripts')}>Scripts & Templates</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!trust')}>Trust Building</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!tonality')}>Voice & Tonality</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!firstimpression')}>First Impressions</button>
            </div>

            <div className="sidebar-section">
              <h3>Closer Moves</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!pvf')}>Pain-Vision-Fit Close</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!checkpoints')}>Emotional Checkpoints</button>
            </div>

            <div className="sidebar-section">
              <h3>Objection Handling</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection price')}>Price Objections</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection paymenttoohigh')}>Payment Too High</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection tradevalue')}>Trade Value</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection thinkaboutit')}>Think About It</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection shoparound')}>Shop Around</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!objection spouse')}>Spouse Decision</button>
            </div>

            <div className="sidebar-section">
              <h3>Role-Play Scenarios</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!roleplay price')}>Price Role-Play</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!roleplay trade')}>Trade Role-Play</button>
            </div>

            <div className="sidebar-section">
              <h3>Money Momentum</h3>
              <button className="sidebar-btn" onClick={() => sendCommand('!dailylog')}>Daily Activity Log</button>
              <button className="sidebar-btn" onClick={() => sendCommand('!earn')}>E.A.R.N. System</button>
            </div>

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

        {/* Main Chat */}
        <main className="chat-main">
          <div className="messages">
            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.role}`}>
                <p>{msg.content}</p>
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
          <div className="modal-content">
            <h3>Welcome to Training!</h3>
            <p>Please enter your name to begin your personalized sales training experience.</p>
            
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
