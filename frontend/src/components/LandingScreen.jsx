import { Sparkles, Brain, TrendingUp, Cpu, Workflow, Zap, ArrowRight, LogOut } from 'lucide-react';
import RobotMascot from './RobotMascot';

const features = [
  { icon: <Brain size={18} />, title: 'RAG Pipeline', desc: 'Retrieves exact video timestamps' },
  { icon: <Workflow size={18} />, title: 'LangGraph Agent', desc: 'Multi-step reasoning graph' },
  { icon: <Sparkles size={18} />, title: 'Smart Answers', desc: 'Context-aware LLM responses' },
];

const techStack = ['LangChain', 'LangGraph', 'FAISS', 'LLaMA 3.2'];

export default function LandingScreen({ username, onStart, onLogout }) {
  return (
    <div className="landing-screen">
      <button className="landing-logout" onClick={onLogout} aria-label="Sign out">
        <LogOut size={14} /> Sign out
      </button>

      <div className="landing-content">
        <div className="landing-robot" onClick={onStart} role="button" tabIndex={0} onKeyDown={e => e.key === 'Enter' && onStart()}>
          <RobotMascot size={180} message="Click me to start chatting!" />
        </div>

        <h1 className="landing-title">InferaMind AI</h1>
        <p className="landing-subtitle">
          Hey <strong>{username}</strong>! I'm your AI teaching assistant for Andrew Ng's ML Specialization.
        </p>

        <button className="landing-start-btn" onClick={onStart}>
          <span>Start Chatting</span>
          <ArrowRight size={18} />
        </button>

        <div className="landing-features">
          {features.map(f => (
            <div key={f.title} className="landing-feature">
              <div className="landing-feature-icon">{f.icon}</div>
              <div>
                <strong>{f.title}</strong>
                <span>{f.desc}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="landing-tech">
          {techStack.map(t => <span key={t}>{t}</span>)}
        </div>
      </div>
    </div>
  );
}
