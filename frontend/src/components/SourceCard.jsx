import { memo } from 'react';
import { Video, Clock, BarChart3 } from 'lucide-react';

function formatTime(seconds) {
  const s = Math.max(0, Math.floor(seconds || 0));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, '0')}`;
}

export default memo(function SourceCard({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources" role="region" aria-label="Retrieved sources">
      <div className="sources-header">
        <BarChart3 size={13} aria-hidden="true" />
        <span>Sources ({sources.length} chunks)</span>
      </div>
      <div className="source-chips">
        {sources.map((s) => {
          const videoNum = s.video ?? 0;
          const score = Math.round((s.similarity ?? 0) * 100);
          const key = `v${videoNum}-${s.start ?? 0}-${s.end ?? 0}-${(s.text || '').slice(0, 20)}`;

          return (
            <div key={key} className="source-chip">
              <div className="source-top">
                <div className="source-badge">
                  <Video size={11} aria-hidden="true" />
                  <span>Video {videoNum}</span>
                </div>
                <span className={`source-score ${score >= 70 ? 'high' : score >= 50 ? 'mid' : 'low'}`}>
                  {score}%
                </span>
              </div>
              <div className="source-time">
                <Clock size={10} aria-hidden="true" />
                {formatTime(s.start)} - {formatTime(s.end)}
              </div>
              {s.text && <p className="source-text">{s.text.slice(0, 100)}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
});
