import { getAuthToken } from './auth';

export function getOperatorSessionId(): string {
  const storageKey = 'vanguard_operator_sid';
  let sid = sessionStorage.getItem(storageKey);
  if (!sid) {
    sid = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `op-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    sessionStorage.setItem(storageKey, sid);
  }
  return sid;
}

export function buildWsUrl(pathAndQuery: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const token = getAuthToken();
  if (!token) {
    return `${protocol}//${window.location.host}${pathAndQuery}`;
  }
  const sep = pathAndQuery.includes('?') ? '&' : '?';
  return `${protocol}//${window.location.host}${pathAndQuery}${sep}token=${encodeURIComponent(token)}`;
}
