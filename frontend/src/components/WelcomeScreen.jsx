import { Brain, TrendingUp, Cpu, Workflow, Sparkles, Zap } from 'lucide-react';
import RobotAvatar from './RobotAvatar';

const suggestions = [
  { icon: <Brain size={14} />, text: 'What is supervised learning?' },
  { icon: <TrendingUp size={14} />, text: 'How is ML creating economic value?' },
  { icon: <Cpu size={14} />, text: 'What are the types of machine learning?' },
  { icon: <Workflow size={14} />, text: 'What are the most important ML algorithms?' },
  { icon: <Sparkles size={14} />, text: 'When should I apply machine learning?' },
  { icon: <Zap size={14} />, text: 'Explain gradient descent simply' },
];

export default function WelcomeScreen({ onSuggestionClick }) {
  return (
    <div className="welcome">
      <div className="welcome-bot">
        <RobotAvatar size={48} />
        <div>
          <h2>InferaMind AI</h2>
          <p>Ask me anything about the ML course videos</p>
        </div>
      </div>

      <h3>Suggestions</h3>
      <div className="suggestions">
        {suggestions.map((s) => (
          <button
            key={s.text}
            className="suggestion"
            onClick={() => onSuggestionClick(s.text)}
          >
            {s.icon}
            {s.text}
          </button>
        ))}
      </div>
    </div>
  );
}
