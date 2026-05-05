import { useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';
import { subscribeToasts } from '../lib/toast';

const ICONS = {
  success: <CheckCircle2 size={15} />,
  error: <AlertTriangle size={15} />,
  info: <Info size={15} />,
};

export default function ToastHost() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => subscribeToasts((t) => {
    setToasts(prev => [...prev, t]);
    setTimeout(() => {
      setToasts(prev => prev.filter(x => x.id !== t.id));
    }, t.durationMs);
  }), []);

  const dismiss = (id) => setToasts(prev => prev.filter(t => t.id !== id));

  if (toasts.length === 0) return null;

  return (
    <div className="toast-host" role="status" aria-live="polite">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.kind}`}>
          <span className="toast-icon">{ICONS[t.kind] || ICONS.info}</span>
          <span className="toast-message">{t.message}</span>
          <button
            className="toast-close"
            onClick={() => dismiss(t.id)}
            aria-label="Dismiss notification"
          >
            <X size={12} />
          </button>
        </div>
      ))}
    </div>
  );
}
