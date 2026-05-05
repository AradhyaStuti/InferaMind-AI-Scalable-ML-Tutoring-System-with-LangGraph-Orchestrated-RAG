let nextId = 1;
const listeners = new Set();

export function pushToast(message, kind = 'info', durationMs = 3500) {
  const toast = { id: nextId++, message, kind, durationMs };
  listeners.forEach(fn => fn(toast));
  return toast.id;
}

export function subscribeToasts(fn) {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}
