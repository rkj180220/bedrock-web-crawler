import React, { useState, useRef, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    {
      type: 'system',
      content: 'Welcome to the Web Crawler Agent! I can help you scrape and analyze web content. Just provide a URL and ask me what you\'d like to know about it.',
      timestamp: new Date()
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const addMessage = (message) => {
    setMessages(prev => [...prev, { ...message, timestamp: new Date() }]);
  };

  const handleSendMessage = async (userMessage) => {
    // Add user message
    addMessage({
      type: 'user',
      content: userMessage
    });

    setIsLoading(true);

    try {
      // Call Bedrock Agent API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          sessionId: generateSessionId()
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Add agent response
      addMessage({
        type: 'agent',
        content: data.response || 'I apologize, but I encountered an error processing your request.',
        metadata: data.metadata
      });

    } catch (error) {
      console.error('Error calling agent:', error);
      addMessage({
        type: 'error',
        content: 'Sorry, I encountered an error. Please try again or check your connection.'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const generateSessionId = () => {
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>🕷️ Web Crawler Agent</h1>
          <p>Powered by AWS Bedrock & Lambda</p>
        </div>
      </header>

      <main className="App-main">
        <ChatInterface
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
        />
      </main>

      <footer className="App-footer">
        <p>Built with React, AWS Lambda, and Bedrock</p>
      </footer>
    </div>
  );
}

export default App;
