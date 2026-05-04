import { memo } from 'react';

export default memo(function RobotAvatar({ size = 28 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="robot-avatar-svg"
      aria-hidden="true"
    >
      <line x1="50" y1="8" x2="50" y2="20" stroke="#818cf8" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="50" cy="5" r="4" fill="#818cf8" className="robot-antenna-dot" />

      <rect x="18" y="20" width="64" height="52" rx="16" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="2" />

      <circle cx="36" cy="44" r="8" fill="#0f0f12" />
      <circle cx="64" cy="44" r="8" fill="#0f0f12" />
      <circle cx="36" cy="44" r="5" fill="#818cf8" className="robot-eye" />
      <circle cx="64" cy="44" r="5" fill="#818cf8" className="robot-eye" />
      <circle cx="38" cy="42" r="1.5" fill="#e0e7ff" opacity="0.8" />
      <circle cx="66" cy="42" r="1.5" fill="#e0e7ff" opacity="0.8" />

      <path d="M38 60 Q50 70 62 60" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" fill="none" />

      <rect x="8" y="34" width="10" height="18" rx="5" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="1.5" />
      <rect x="82" y="34" width="10" height="18" rx="5" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="1.5" />

      <rect x="40" y="72" width="20" height="8" rx="4" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="1.5" />

      <rect x="25" y="80" width="50" height="16" rx="8" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="1.5" />
      <circle cx="50" cy="88" r="3" fill="#34d399" className="robot-chest-light" />
    </svg>
  );
});
