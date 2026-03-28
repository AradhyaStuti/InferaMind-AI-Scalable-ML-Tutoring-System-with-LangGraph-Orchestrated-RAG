import { memo } from 'react';
import { Filter, Database, Cpu, Check, ChevronRight } from 'lucide-react';

const NODES = [
  { id: 'classify', label: 'Classify', icon: <Filter size={12} /> },
  { id: 'retrieve', label: 'Retrieve', icon: <Database size={12} /> },
  { id: 'generate', label: 'Generate', icon: <Cpu size={12} /> },
];

export default memo(function PipelineStatus({ activeNode }) {
  if (!activeNode) return null;

  const activeIdx = NODES.findIndex(n => n.id === activeNode);

  return (
    <div className="pipeline-status" role="status" aria-label="Processing pipeline">
      <div className="pipeline-nodes">
        {NODES.map((node, i) => {
          let status = 'pending';
          if (i < activeIdx) status = 'done';
          else if (i === activeIdx) status = 'active';

          return (
            <div key={node.id} className="pipeline-step">
              <div className={`pipeline-node ${status}`} aria-label={`${node.label}: ${status}`}>
                <div className="pipeline-icon" aria-hidden="true">
                  {status === 'done' ? <Check size={12} /> : node.icon}
                </div>
                <span>{node.label}</span>
              </div>
              {i < NODES.length - 1 && (
                <ChevronRight size={12} className={`pipeline-arrow ${status === 'done' ? 'done' : ''}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
});
