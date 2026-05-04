import { useState } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import AuthScreen from './components/AuthScreen';
import LandingScreen from './components/LandingScreen';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import { useAuth } from './hooks/useAuth';
import { useChat } from './hooks/useChat';
import './styles.css';

function ChatApp({ username, onBack }) {
  const {
    messages, isStreaming, activeNode, conversationId, conversations,
    loadingConversations, error,
    sendMessage, loadConversations, loadConversation, startNewChat,
    cancelStream, dismissError, retryLast, regenerateLast,
  } = useChat();

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={conversationId}
        onSelect={loadConversation}
        onNewChat={startNewChat}
        onRefresh={loadConversations}
        loading={loadingConversations}
        username={username}
        onBack={onBack}
      />
      <ChatWindow
        messages={messages}
        isStreaming={isStreaming}
        activeNode={activeNode}
        onSend={sendMessage}
        onCancel={cancelStream}
        error={error}
        onDismissError={dismissError}
        onRetry={retryLast}
        onRegenerate={regenerateLast}
      />
    </div>
  );
}

export default function App() {
  const { isAuthenticated, username, error, loading, register, login, logout } = useAuth();
  const [chatStarted, setChatStarted] = useState(false);

  if (!isAuthenticated) {
    return (
      <ErrorBoundary>
        <AuthScreen onLogin={login} onRegister={register} error={error} loading={loading} />
      </ErrorBoundary>
    );
  }

  if (!chatStarted) {
    return (
      <ErrorBoundary>
        <LandingScreen
          username={username}
          onStart={() => setChatStarted(true)}
          onLogout={logout}
        />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <ChatApp username={username} onBack={() => setChatStarted(false)} />
    </ErrorBoundary>
  );
}
