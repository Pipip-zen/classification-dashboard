import React, { useState, useEffect, useCallback } from 'react';
import { TopNavbar } from './components/layout/TopNavbar';
import { LiveCockpit } from './pages/LiveCockpit';
import { MediaAnalysis } from './pages/MediaAnalysis';
import { DatasetView } from './pages/DatasetView';
import { LoginView } from './pages/LoginView';
import type { AuthUser, ChannelId, ChannelStatusSummary, TelemetryData } from './types';
import { buildWsUrl, getOperatorSessionId } from './utils/session';
import {
  authFetch,
  clearAuthSession,
  getAuthSession,
  onUnauthorized,
  setAuthSession,
  type AuthSession,
} from './utils/auth';

const createDefaultTelemetry = (channelId: ChannelId): TelemetryData => ({
  channel_id: channelId,
  cockpit_mode: channelId,
  stream_active: false,
  threat_level: 'GREEN SECTOR',
  threat_color_hex: '#00FF66',
  total_objects: 0,
  hazard_count: 0,
  neutral_count: 0,
  fps: 0,
  ai_fps: 0,
  latency_ms: 0,
  heading_deg: 0,
  cardinal: 'N',
  turn_rate_dps: 0,
  detections: [],
});

const createDefaultChannelStatus = (channelId: ChannelId): ChannelStatusSummary => ({
  channel_id: channelId,
  stream_active: false,
  source_type: 'testbench',
  source_param: channelId === 'drone' ? 'drone_forest_person_patrol.mp4' : 'rov_underwater_patrol.mp4',
  locked: false,
  fps: 0,
  ai_fps: 0,
  latency_ms: 0,
  confidence_gate: 0.25,
  dusk_enhancer: false,
  reticle_visible: true,
  labels_visible: true,
  telemetry: createDefaultTelemetry(channelId),
});

export const App: React.FC = () => {
  const [authSession, setAuthState] = useState<AuthSession | null>(() => getAuthSession());
  const [activeTab, setActiveTab] = useState<string>('live');

  const [telemetryByChannel, setTelemetryByChannel] = useState<Record<ChannelId, TelemetryData>>({
    drone: createDefaultTelemetry('drone'),
    rov: createDefaultTelemetry('rov'),
  });

  const [channelsStatus, setChannelsStatus] = useState<Record<ChannelId, ChannelStatusSummary>>({
    drone: createDefaultChannelStatus('drone'),
    rov: createDefaultChannelStatus('rov'),
  });

  useEffect(() => {
    return onUnauthorized(() => {
      setAuthState(null);
      setActiveTab('live');
    });
  }, []);

  // Verifikasi token tersimpan saat reload halaman
  useEffect(() => {
    if (!authSession?.token) return;
    authFetch('/api/auth/me')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.user) {
          setAuthSession(authSession.token, data.user);
        }
      })
      .catch(() => {});
  }, [authSession?.token]);

  const handleLoginSuccess = (token: string, user: AuthUser) => {
    setAuthSession(token, user);
    setAuthState({ token, user });
    setActiveTab('live');
  };

  const handleLogout = async () => {
    const currentRole = authSession?.user?.role;
    if (currentRole === 'drone' || currentRole === 'rov') {
      const sid = getOperatorSessionId();
      await authFetch(`/api/channels/${currentRole}/release`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sid }),
      }).catch(() => {});
    }
    await authFetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
    clearAuthSession();
    setAuthState(null);
    setActiveTab('live');
  };

  const handleLocalTelemetry = useCallback((channelId: ChannelId, telemetry: TelemetryData) => {
    setTelemetryByChannel((prev) => ({
      ...prev,
      [channelId]: telemetry,
    }));
  }, []);

  const currentRole = authSession?.user?.role;

  // Poll status multi-channel sesuai izin peran
  useEffect(() => {
    if (!authSession?.token) return;
    const fetchChannels = () => {
      authFetch('/api/channels/status')
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (!data?.channels) return;
          setChannelsStatus((prev) => ({
            drone: data.channels.drone || prev.drone,
            rov: data.channels.rov || prev.rov,
          }));
        })
        .catch(() => {});
    };
    fetchChannels();
    const timer = setInterval(fetchChannels, 3000);
    return () => clearInterval(timer);
  }, [authSession?.token]);

  // Buka WebSocket telemetri hanya untuk channel yang diizinkan oleh peran login
  useEffect(() => {
    if (!authSession?.token || !currentRole) return;
    let active = true;
    const sockets: WebSocket[] = [];
    const timers: ReturnType<typeof setTimeout>[] = [];

    const subscribedChannels: ChannelId[] =
      currentRole === 'spectator' ? ['drone', 'rov'] : [currentRole];

    subscribedChannels.forEach((cid) => {
      const connect = () => {
        if (!active) return;
        const ws = new WebSocket(buildWsUrl(`/ws/telemetry/${cid}`));
        sockets.push(ws);

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data && data.threat_level) {
              setTelemetryByChannel((prev) => ({
                ...prev,
                [cid]: data,
              }));
            }
          } catch {
            // Abaikan heartbeat non-JSON
          }
        };

        ws.onclose = () => {
          if (active) {
            timers.push(setTimeout(connect, 2000));
          }
        };

        ws.onerror = () => ws.close();
      };

      connect();
    });

    return () => {
      active = false;
      timers.forEach((t) => clearTimeout(t));
      sockets.forEach((ws) => {
        if (ws.readyState < WebSocket.CLOSING) ws.close();
      });
    };
  }, [authSession?.token, currentRole]);

  if (!authSession) {
    return <LoginView onLoginSuccess={handleLoginSuccess} />;
  }

  const user = authSession.user;
  const effectiveTab = user.role === 'spectator' ? 'live' : activeTab;

  const navbarTelemetry =
    user.role === 'spectator'
      ? (channelsStatus.drone.stream_active ? telemetryByChannel.drone : telemetryByChannel.rov)
      : telemetryByChannel[user.role];

  return (
    <div className="min-h-screen bg-aerospace-bg text-tactical-text flex flex-col font-sans">
      <TopNavbar
        user={user}
        activeTab={effectiveTab}
        setActiveTab={setActiveTab}
        telemetry={navbarTelemetry}
        channelsStatus={channelsStatus}
        onLogout={handleLogout}
      />

      <main className="flex-1 overflow-auto">
        {effectiveTab === 'live' && (
          <LiveCockpit
            userRole={user.role}
            channelsStatus={channelsStatus}
            telemetryByChannel={telemetryByChannel}
            onLocalTelemetry={handleLocalTelemetry}
          />
        )}
        {effectiveTab === 'analysis' && user.role !== 'spectator' && <MediaAnalysis />}
        {effectiveTab === 'dataset' && user.role !== 'spectator' && <DatasetView />}
      </main>
    </div>
  );
};

export default App;
