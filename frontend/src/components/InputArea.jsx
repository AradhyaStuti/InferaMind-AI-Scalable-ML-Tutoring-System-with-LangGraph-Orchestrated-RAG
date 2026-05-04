import { useState, useRef, memo } from 'react';
import { ArrowUp, Square } from 'lucide-react';

const MAX_LENGTH = 2000;

export default memo(function InputArea({ onSend, disabled, onCancel }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  const remaining = MAX_LENGTH - text.length;
  const nearLimit = remaining <= 200;
  const atLimit = remaining <= 0;

  const handleSubmit = () => {
    if (!text.trim() || disabled || atLimit) return;
    onSend(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e) => {
    const val = e.target.value;
    if (val.length > MAX_LENGTH) return;
    setText(val);
    const el = e.target;
    el.style.height = 'auto';
    const height = el.scrollHeight || 0;
    el.style.height = Math.min(Math.max(height, 24), 150) + 'px';
  };

  return (
    <div className="input-area">
      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about the ML course..."
          aria-label="Type your question"
          rows={1}
          disabled={disabled}
          autoFocus
        />
        {onCancel ? (
          <button className="send-btn cancel-btn" onClick={onCancel} aria-label="Stop generating">
            <Square size={14} aria-hidden="true" />
          </button>
        ) : (
          <button
            className="send-btn"
            onClick={handleSubmit}
            disabled={!text.trim() || disabled || atLimit}
            aria-label="Send message"
          >
            <ArrowUp size={18} aria-hidden="true" />
          </button>
        )}
      </div>
      <div className="input-footer">
        <p className="input-hint">
          <strong>LangChain</strong> &middot; <strong>LangGraph</strong> &middot; <strong>FAISS</strong> &middot; <strong>Ollama</strong> &middot; <strong>LLaMA 3.2</strong> &mdash; Enter to send
        </p>
        {text.length > 0 && (
          <span className={`char-count ${nearLimit ? 'warn' : ''} ${atLimit ? 'limit' : ''}`}>
            {remaining}
          </span>
        )}
      </div>
    </div>
  );
});
