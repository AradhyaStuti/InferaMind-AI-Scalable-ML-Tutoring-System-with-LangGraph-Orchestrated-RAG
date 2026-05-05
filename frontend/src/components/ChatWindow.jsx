import { useEffect, useRef, useState, useCallback } from 'react';
import { AlertCircle, X, RotateCcw, ArrowDown } from 'lucide-react';
import MessageBubble from './MessageBubble';
import WelcomeScreen from './WelcomeScreen';
import InputArea from './InputArea';

export default function ChatWindow({
  messages, isStreaming, activeNode, onSend, onCancel,
  error, onDismissError, onRetry, onRegenerate, inputRef, conversationId,
}) {
  const bottomRef = useRef(null);
  const containerRef = useRef(null);
  const shouldAutoScroll = useRef(true);
  const [showJump, setShowJump] = useState(false);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    shouldAutoScroll.current = nearBottom;
    setShowJump(!nearBottom);
  }, []);

  useEffect(() => {
    if (shouldAutoScroll.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const jumpToBottom = () => {
    shouldAutoScroll.current = true;
    setShowJump(false);
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const lastAssistantIdx = messages.findLastIndex(m => m.role === 'assistant');

  return (
    <main className="chat-window" role="main" aria-label="Chat">
      <div className="messages-container" ref={containerRef} onScroll={handleScroll}>
        {messages.length === 0 ? (
          <WelcomeScreen onSuggestionClick={onSend} />
        ) : (
          <div className="messages-list" role="log" aria-live="polite">
            {messages.map((msg, i) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'}
                activeNode={isStreaming && i === messages.length - 1 ? activeNode : null}
                isLast={i === lastAssistantIdx}
                onRegenerate={!isStreaming ? onRegenerate : null}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {showJump && (
        <button
          className="jump-to-bottom"
          onClick={jumpToBottom}
          aria-label="Scroll to latest message"
        >
          <ArrowDown size={14} />
        </button>
      )}

      {error && !isStreaming && (
        <div className="chat-error" role="alert">
          <AlertCircle size={14} />
          <span>{error}</span>
          <div className="chat-error-actions">
            {onRetry && (
              <button className="error-action-btn" onClick={onRetry} aria-label="Retry">
                <RotateCcw size={12} /> Retry
              </button>
            )}
            <button className="error-dismiss-btn" onClick={onDismissError} aria-label="Dismiss error">
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      <InputArea
        onSend={onSend}
        disabled={isStreaming}
        onCancel={isStreaming ? onCancel : null}
        inputRef={inputRef}
        focusKey={conversationId || 'new'}
      />
    </main>
  );
}
