import React, { useState } from 'react';
import { Lock, LogIn } from 'lucide-react';
import type { AuthUser } from '../types';

interface LoginViewProps {
  onLoginSuccess: (token: string, user: AuthUser) => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrorMsg('Isi username dan password terlebih dahulu.');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const data = await res.json();
      if (!res.ok || !data.success || !data.access_token || !data.user) {
        setErrorMsg(data.detail || 'Username atau password salah.');
        return;
      }
      onLoginSuccess(data.access_token, data.user);
    } catch {
      setErrorMsg('Tidak dapat menghubungi server otentikasi.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded p-6 space-y-5 font-mono">
        <div className="border-b border-slate-800 pb-4 space-y-1">
          <div className="flex items-center justify-between">
            <span className="font-extrabold text-base tracking-wider text-emerald-400">
              VANGUARD AI GCS
            </span>
            <Lock className="w-4 h-4 text-slate-400" />
          </div>
          <p className="text-xs text-slate-400">
            Masuk dengan akun peran Anda (Admin Drone, Admin ROV, atau Spectator).
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {errorMsg && (
            <div
              role="alert"
              className="text-xs text-signal-red bg-red-950/50 border border-red-800/70 px-3 py-2 rounded"
            >
              {errorMsg}
            </div>
          )}

          <div className="space-y-1.5">
            <label htmlFor="login-username" className="block text-[11px] uppercase tracking-wider text-slate-300">
              Username
            </label>
            <input
              id="login-username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="drone / rov / spectator"
              className="w-full min-h-[44px] bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-white focus:border-signal-cyan focus:outline-none focus-visible:ring-2 focus-visible:ring-signal-cyan"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="login-password" className="block text-[11px] uppercase tracking-wider text-slate-300">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Masukkan password akun"
              className="w-full min-h-[44px] bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-white focus:border-signal-cyan focus:outline-none focus-visible:ring-2 focus-visible:ring-signal-cyan"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full min-h-[44px] flex items-center justify-center space-x-2 py-2.5 px-4 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold uppercase tracking-wider transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-cyan"
          >
            <LogIn className="w-4 h-4" />
            <span>{loading ? 'Memverifikasi...' : 'Masuk ke Dashboard'}</span>
          </button>
        </form>
      </div>
    </div>
  );
};
