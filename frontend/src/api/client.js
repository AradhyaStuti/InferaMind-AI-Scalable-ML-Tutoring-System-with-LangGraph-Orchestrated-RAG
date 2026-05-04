const BASE = '/api';

function getToken() {
  return localStorage.getItem('ml_tutor_token');
}

function authHeaders() {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

const authExpiredListeners = [];
export function onAuthExpired(fn) { authExpiredListeners.push(fn); }

function handleAuthExpired() {
  localStorage.removeItem('ml_tutor_token');
  localStorage.removeItem('ml_tutor_user');
  authExpiredListeners.forEach(fn => fn());
}

async function request(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...options.headers },
  });
  if (res.status === 401) { handleAuthExpired(); throw new ApiError(401, 'Session expired'); }
  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error');
    throw new ApiError(res.status, text);
  }
  return res;
}

export async function fetchHealth() { return (await fetch(`${BASE}/health`)).json(); }

export async function fetchConversations() { return (await request(`${BASE}/conversations`)).json(); }
export async function fetchMessages(id) { return (await request(`${BASE}/conversations/${id}/messages`)).json(); }
export async function deleteConversation(id) { await request(`${BASE}/conversations/${id}`, { method: 'DELETE' }); }
export async function renameConversation(id, title) {
  await request(`${BASE}/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) });
}

let _ws = null;
let _wsReady = false;

function getWsUrl() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${location.host}${BASE}/chat/ws`;
}

function connectWs() {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(getWsUrl());
    const timeout = setTimeout(() => { ws.close(); reject(new Error('WS timeout')); }, 5000);

    ws.onopen = () => {
      clearTimeout(timeout);
      ws.send(JSON.stringify({ token: getToken() }));
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.authenticated) {
          _ws = ws;
          _wsReady = true;
          resolve(ws);
        } else if (data.error) {
          ws.close();
          reject(new Error(data.error));
        }
      } catch {
        ws.close();
        reject(new Error('WS auth failed'));
      }
    };

    ws.onerror = () => { clearTimeout(timeout); reject(new Error('WS connect failed')); };
    ws.onclose = () => { _ws = null; _wsReady = false; };
  });
}

async function getWs() {
  if (_ws && _ws.readyState === WebSocket.OPEN && _wsReady) return _ws;
  _ws = null;
  _wsReady = false;
  return connectWs();
}

export async function* streamChatWs(message, conversationId, signal) {
  const ws = await getWs();
  ws.send(JSON.stringify({ message, conversation_id: conversationId }));

  const queue = [];
  let resolve = null;
  let done = false;

  const onMsg = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (resolve) { const r = resolve; resolve = null; r(data); }
      else queue.push(data);
    } catch {
      // ignore malformed frames
    }
  };

  const onClose = () => { done = true; if (resolve) { const r = resolve; resolve = null; r(null); } };
  const onAbort = () => { done = true; if (resolve) { const r = resolve; resolve = null; r(null); } };

  ws.addEventListener('message', onMsg);
  ws.addEventListener('close', onClose);
  signal?.addEventListener('abort', onAbort);

  try {
    while (!done && !signal?.aborted) {
      const data = queue.length > 0
        ? queue.shift()
        : await new Promise(r => { resolve = r; });

      if (!data) break;
      yield data;
      if (data.done || data.error) break;
    }
  } finally {
    ws.removeEventListener('message', onMsg);
    ws.removeEventListener('close', onClose);
    signal?.removeEventListener('abort', onAbort);
  }

  if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
}

async function* streamChatSSE(message, conversationId, signal) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, conversation_id: conversationId }),
    signal,
  });

  if (res.status === 401) { handleAuthExpired(); return; }
  if (!res.ok) throw new ApiError(res.status, 'Chat request failed');
  if (!res.body) throw new ApiError(0, 'No response body');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const line of decoder.decode(value, { stream: true }).split('\n')) {
        if (!line.startsWith('data: ')) continue;
        try { yield JSON.parse(line.slice(6)); } catch (e) { console.warn('SSE parse error:', e.message, line); }
      }
    }
  } finally { reader.releaseLock(); }
}

export async function* streamChat(message, conversationId, signal) {
  try {
    yield* streamChatWs(message, conversationId, signal);
  } catch (e) {
    if (e.name === 'AbortError') throw e;
    console.warn('WebSocket failed, falling back to SSE:', e.message);
    yield* streamChatSSE(message, conversationId, signal);
  }
}
