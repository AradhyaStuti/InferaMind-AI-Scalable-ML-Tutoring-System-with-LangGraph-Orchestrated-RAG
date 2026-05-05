import { Brain, Workflow, Database, Network, Layers, Code2, BarChart3, Boxes } from 'lucide-react';
import RobotAvatar from './RobotAvatar';

const suggestions = [
  { icon: <Brain size={14} />, text: 'What is supervised learning?' },
  { icon: <Workflow size={14} />, text: 'Explain gradient descent simply' },
  { icon: <Database size={14} />, text: 'What is RAG and why use it?' },
  { icon: <Network size={14} />, text: 'How does self-attention work in transformers?' },
  { icon: <Layers size={14} />, text: 'What is LangGraph used for?' },
  { icon: <Code2 size={14} />, text: 'How do I use pandas groupby?' },
  { icon: <BarChart3 size={14} />, text: 'When should I use random forest vs XGBoost?' },
  { icon: <Boxes size={14} />, text: 'What are scikit-learn pipelines?' },
];

export default function WelcomeScreen({ onSuggestionClick }) {
  return (
    <div className="welcome">
      <div className="welcome-bot">
        <RobotAvatar size={48} />
        <div>
          <h2>RouteLM</h2>
          <p>Ask about ML, the LLM/RAG stack, or Python data science — I'll route to the right corpus.</p>
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
