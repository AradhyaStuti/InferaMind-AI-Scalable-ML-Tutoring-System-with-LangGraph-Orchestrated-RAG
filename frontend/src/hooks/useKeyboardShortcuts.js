import { useEffect } from 'react';

const isEditable = (el) => {
  if (!el) return false;
  const tag = el.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || el.isContentEditable;
};

export function useKeyboardShortcuts({ onNewChat, onCancel, onFocusInput }) {
  useEffect(() => {
    const handler = (e) => {
      const mod = e.metaKey || e.ctrlKey;

      if (e.key === 'Escape' && onCancel) {
        onCancel();
        return;
      }

      if (mod && (e.key === 'n' || e.key === 'N')) {
        if (onNewChat) {
          e.preventDefault();
          onNewChat();
        }
        return;
      }

      if (mod && e.key === '/') {
        if (onFocusInput) {
          e.preventDefault();
          onFocusInput();
        }
        return;
      }

      if (e.key === '/' && !mod && !isEditable(document.activeElement)) {
        if (onFocusInput) {
          e.preventDefault();
          onFocusInput();
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onNewChat, onCancel, onFocusInput]);
}
