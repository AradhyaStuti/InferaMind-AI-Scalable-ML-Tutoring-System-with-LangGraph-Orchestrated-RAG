import { memo } from 'react';

export default memo(function RobotMascot({ size = 160, message }) {
  return (
    <div className="robot-container">
      <div className="robot-wrapper">
        <svg
          width={size}
          height={size}
          viewBox="0 0 200 200"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="robot-svg"
          aria-hidden="true"
        >
          <line x1="100" y1="28" x2="100" y2="48" stroke="#818cf8" strokeWidth="3" strokeLinecap="round" />
          <circle cx="100" cy="22" r="6" fill="#818cf8" className="robot-antenna-dot" />

          <rect x="55" y="48" width="90" height="70" rx="20" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="2.5" />

          <circle cx="78" cy="80" r="10" fill="#0f0f12" />
          <circle cx="122" cy="80" r="10" fill="#0f0f12" />
          <circle cx="78" cy="80" r="6" fill="#818cf8" className="robot-eye" />
          <circle cx="122" cy="80" r="6" fill="#818cf8" className="robot-eye" />
          <circle cx="81" cy="77" r="2" fill="#e0e7ff" opacity="0.8" />
          <circle cx="125" cy="77" r="2" fill="#e0e7ff" opacity="0.8" />

          <path d="M82 98 Q100 110 118 98" stroke="#818cf8" strokeWidth="2.5" strokeLinecap="round" fill="none" />

          <rect x="90" y="118" width="20" height="10" rx="4" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="1.5" />

          <rect x="50" y="128" width="100" height="50" rx="16" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="2.5" />

          <circle cx="100" cy="150" r="8" fill="#0f0f12" stroke="#4f46e5" strokeWidth="1.5" />
          <circle cx="100" cy="150" r="4" fill="#34d399" className="robot-chest-light" />

          <rect x="28" y="134" width="20" height="36" rx="10" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="2" className="robot-arm-left" />
          <rect x="152" y="134" width="20" height="36" rx="10" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="2" className="robot-arm-right" />

          <circle cx="38" cy="174" r="6" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="2" className="robot-arm-left" />
          <circle cx="162" cy="174" r="6" fill="#1e1b4b" stroke="#4f46e5" strokeWidth="2" className="robot-arm-right" />
        </svg>
      </div>

      {message && (
        <div className="robot-speech-bubble">
          <p>{message}</p>
          <div className="robot-speech-tail" />
        </div>
      )}
    </div>
  );
});
