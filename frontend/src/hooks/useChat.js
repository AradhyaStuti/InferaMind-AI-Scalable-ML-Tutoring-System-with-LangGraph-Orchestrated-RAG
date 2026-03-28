import { useState, useCallback, useRef, useReducer } from 'react';
import { streamChat, fetchMessages, fetchConversations } from '../api/client';

function messagesReducer(state, action) {
  switch (action.type) {
    case 'set':
      return action.messages;
    case 'append':
      return [...state, action.message];
    case 'update_last': {
      if (state.length === 0) return state;
      const updated = [...state];
      updated[updated.length - 1] = {
        ...updated[updated.length - 1],
        ...action.fields,
      };
      return updated;
    }
    case 'append_token': {
      if (state.length === 0) return state;
      const updated = [...state];
      const last = updated[updated.length - 1];
      updated[updated.length - 1] = {
        ...last,
        content: last.content + action.token,
      };
      return updated;
    }
    case 'remove_last_pair': {
      // Remove last assistant + last user message (for retry)
      if (state.length < 2) return [];
      return state.slice(0, -2);
    }
    case 'remove_last': {
      if (state.length === 0) return state;
      return state.slice(0, -1);
    }
    case 'clear':
      return [];
    default:
      return state;
  }
}

export function useChat() {
  const [messages, dispatch] = useReducer(messagesReducer, []);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeNode, setActiveNode] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);
  const convIdRef = useRef(null);
  const lastUserMsgRef = useRef(null);

  const loadConversations = useCallback(async () => {
    setLoadingConversations(true);
    try {
      const data = await fetchConversations();
      setConversations(data);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setLoadingConversations(false);
    }
  }, []);

  const loadConversation = useCallback(async (convId) => {
    setConversationId(convId);
    convIdRef.current = convId;
    setError(null);
    try {
      const msgs = await fetchMessages(convId);
      dispatch({ type: 'set', messages: msgs });
    } catch (err) {
      console.error('Failed to load messages:', err);
      setError('Failed to load messages');
    }
  }, []);

  const startNewChat = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    setConversationId(null);
    convIdRef.current = null;
    dispatch({ type: 'clear' });
    setActiveNode(null);
    setIsStreaming(false);
    setError(null);
    lastUserMsgRef.current = null;
  }, []);

  const cancelStream = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
      setIsStreaming(false);
      setActiveNode(null);
    }
  }, []);

  const dismissError = useCallback(() => setError(null), []);

  const _doStream = useCallback(async (text) => {
    setError(null);
    lastUserMsgRef.current = text;

    const userMsg = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      sources: [],
      timestamp: new Date().toISOString(),
    };

    dispatch({ type: 'append', message: userMsg });
    setIsStreaming(true);
    setActiveNode('classify');

    dispatch({
      type: 'append',
      message: {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        sources: [],
        timestamp: new Date().toISOString(),
      },
    });

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const data of streamChat(text, convIdRef.current, controller.signal)) {
        if (controller.signal.aborted) break;

        if (data.conversation_id) {
          setConversationId(data.conversation_id);
          convIdRef.current = data.conversation_id;
        }

        if (data.node) setActiveNode(data.node);
        if (data.sources) dispatch({ type: 'update_last', fields: { sources: data.sources } });
        if (data.token) dispatch({ type: 'append_token', token: data.token });

        if (data.error) {
          dispatch({ type: 'update_last', fields: { content: data.error, failed: true } });
          setError(data.error);
        }

        if (data.done) {
          fetchConversations().then(setConversations).catch(() => {});
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        dispatch({ type: 'update_last', fields: { content: '*[Cancelled]*' } });
      } else {
        const errorMsg = 'Connection failed. Make sure the server and Ollama are running.';
        dispatch({ type: 'update_last', fields: { content: errorMsg, failed: true } });
        setError(errorMsg);
        console.error('Chat stream error:', err);
      }
    }

    abortRef.current = null;
    setIsStreaming(false);
    setActiveNode(null);
  }, []);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || isStreaming) return;
    await _doStream(text.trim());
  }, [isStreaming, _doStream]);

  const retryLast = useCallback(async () => {
    if (isStreaming || !lastUserMsgRef.current) return;
    // Remove failed assistant + user pair, re-send
    dispatch({ type: 'remove_last_pair' });
    await _doStream(lastUserMsgRef.current);
  }, [isStreaming, _doStream]);

  const regenerateLast = useCallback(async () => {
    if (isStreaming) return;
    // Find the last user message
    const lastUserIdx = messages.findLastIndex(m => m.role === 'user');
    if (lastUserIdx === -1) return;
    const lastQuery = messages[lastUserIdx].content;
    // Remove the assistant response
    dispatch({ type: 'remove_last' });
    lastUserMsgRef.current = lastQuery;

    // Stream a new response (without re-appending user msg)
    setError(null);
    setIsStreaming(true);
    setActiveNode('classify');

    dispatch({
      type: 'append',
      message: {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        sources: [],
        timestamp: new Date().toISOString(),
      },
    });

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const data of streamChat(lastQuery, convIdRef.current, controller.signal)) {
        if (controller.signal.aborted) break;
        if (data.conversation_id) { setConversationId(data.conversation_id); convIdRef.current = data.conversation_id; }
        if (data.node) setActiveNode(data.node);
        if (data.sources) dispatch({ type: 'update_last', fields: { sources: data.sources } });
        if (data.token) dispatch({ type: 'append_token', token: data.token });
        if (data.error) { dispatch({ type: 'update_last', fields: { content: data.error, failed: true } }); setError(data.error); }
        if (data.done) { fetchConversations().then(setConversations).catch(() => {}); }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        dispatch({ type: 'update_last', fields: { content: 'Regeneration failed.', failed: true } });
      }
    }

    abortRef.current = null;
    setIsStreaming(false);
    setActiveNode(null);
  }, [isStreaming, messages]);

  return {
    messages,
    isStreaming,
    activeNode,
    conversationId,
    conversations,
    loadingConversations,
    error,
    sendMessage,
    loadConversations,
    loadConversation,
    startNewChat,
    cancelStream,
    dismissError,
    retryLast,
    regenerateLast,
  };
}
