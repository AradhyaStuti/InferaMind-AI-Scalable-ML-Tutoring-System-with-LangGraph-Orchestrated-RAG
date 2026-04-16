import { useEffect, useState, memo } from 'react';
import {
  MessageSquarePlus, Trash2, GraduationCap, MessageCircle,
  User, Loader2, PanelLeftClose, PanelLeft, Pencil, Check, X, Home,
} from 'lucide-react';
import { deleteConversation, renameConversation } from '../api/client';

export default memo(function Sidebar({
  conversations, activeId, onSelect, onNewChat, onRefresh,
  loading, username, onBack,
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  useEffect(() => { onRefresh(); }, [onRefresh]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    try {
      await deleteConversation(id);
      onRefresh();
      if (activeId === id) onNewChat();
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const startRename = (e, conv) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const saveRename = async (e) => {
    e?.stopPropagation();
    if (!editTitle.trim()) return;
    try {
      await renameConversation(editingId, editTitle.trim());
      onRefresh();
    } catch (err) {
      console.error('Failed to rename:', err);
    }
    setEditingId(null);
  };

  const cancelRename = (e) => {
    e?.stopPropagation();
    setEditingId(null);
  };

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`} role="navigation" aria-label="Conversations">
      <div className="sidebar-header">
        <div className="logo">
          <GraduationCap size={22} aria-hidden="true" />
          {!collapsed && <span>RouteLM</span>}
        </div>
        <button
          className="collapse-btn"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>

      <button className="new-chat-btn" onClick={onNewChat} aria-label="Start new chat">
        <MessageSquarePlus size={16} aria-hidden="true" />
        {!collapsed && 'New Chat'}
      </button>

      {!collapsed && (
        <>
          <div className="conversations-label">Recent</div>
          <div className="conversations-list" role="list" aria-label="Chat history">
            {loading && (
              <p className="no-chats"><Loader2 size={14} className="spin" /> Loading...</p>
            )}
            {!loading && conversations.map((conv) => (
              <div
                key={conv.id}
                role="listitem"
                className={`conv-item ${activeId === conv.id ? 'active' : ''}`}
                onClick={() => editingId !== conv.id && onSelect(conv.id)}
                onKeyDown={(e) => e.key === 'Enter' && editingId !== conv.id && onSelect(conv.id)}
                tabIndex={0}
                aria-current={activeId === conv.id ? 'true' : undefined}
              >
                <MessageCircle size={14} aria-hidden="true" />

                {editingId === conv.id ? (
                  <div className="rename-input-wrap" onClick={e => e.stopPropagation()}>
                    <input
                      value={editTitle}
                      onChange={e => setEditTitle(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') saveRename(e); if (e.key === 'Escape') cancelRename(e); }}
                      autoFocus
                      className="rename-input"
                    />
                    <button className="rename-ok" onClick={saveRename}><Check size={12} /></button>
                    <button className="rename-cancel" onClick={cancelRename}><X size={12} /></button>
                  </div>
                ) : (
                  <>
                    <span className="conv-title">{conv.title}</span>
                    <div className="conv-actions">
                      <button className="edit-btn" onClick={(e) => startRename(e, conv)} aria-label="Rename">
                        <Pencil size={12} />
                      </button>
                      <button className="delete-btn" onClick={(e) => handleDelete(e, conv.id)} aria-label="Delete">
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
            {!loading && conversations.length === 0 && (
              <p className="no-chats">No conversations yet</p>
            )}
          </div>
        </>
      )}

      <div className="sidebar-footer">
        <div className="user-info">
          <div className="user-avatar">
            <User size={12} aria-hidden="true" />
          </div>
          {!collapsed && <span>{username}</span>}
          <button className="logout-btn" onClick={onBack} aria-label="Back to home" title="Back to home">
            <Home size={13} />
          </button>
        </div>
      </div>
    </aside>
  );
});
