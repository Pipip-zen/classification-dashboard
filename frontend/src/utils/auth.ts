import type { AuthUser } from '../types';

const AUTH_STORAGE_KEY = 'vanguard_auth_session';

export interface AuthSession {
  token: string;
  user: AuthUser;
}

const unauthorizedListeners = new Set<() => void>();

export function onUnauthorized(listener: () => void): () => void {
  unauthorizedListeners.add(listener);
  return () => {
    unauthorizedListeners.delete(listener);
  };
}

export function getAuthSession(): AuthSession | null {
  try {
    const raw = sessionStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AuthSession;
    if (!parsed?.token || !parsed?.user?.role) return null;
    if (parsed.user.exp && parsed.user.exp * 1000 <= Date.now()) {
      sessionStorage.removeItem(AUTH_STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function getAuthToken(): string | null {
  return getAuthSession()?.token || null;
}

export function setAuthSession(token: string, user: AuthUser): void {
  sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ token, user }));
}

export function clearAuthSession(): void {
  sessionStorage.removeItem(AUTH_STORAGE_KEY);
}

export async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const token = getAuthToken();
  const headers = new Headers(init?.headers || {});
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(input, { ...init, headers });
  if (res.status === 401) {
    clearAuthSession();
    unauthorizedListeners.forEach((fn) => fn());
  }
  return res;
}
