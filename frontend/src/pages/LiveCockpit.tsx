import React from 'react';
import type { ChannelId, ChannelStatusSummary, TelemetryData, UserRole } from '../types';
import { OperatorView } from '../components/cockpit/OperatorView';
import { SpectatorView } from '../components/cockpit/SpectatorView';

export { CompassRibbon, CircularCompassDial } from '../components/cockpit/CompassHUD';

interface LiveCockpitProps {
  userRole: UserRole;
  channelsStatus: Record<ChannelId, ChannelStatusSummary>;
  telemetryByChannel: Record<ChannelId, TelemetryData>;
  onLocalTelemetry: (channelId: ChannelId, telemetry: TelemetryData) => void;
}

export const LiveCockpit: React.FC<LiveCockpitProps> = ({
  userRole,
  channelsStatus,
  telemetryByChannel,
  onLocalTelemetry,
}) => {
  if (userRole === 'spectator') {
    return (
      <SpectatorView
        channelsStatus={channelsStatus}
        telemetryByChannel={telemetryByChannel}
      />
    );
  }

  return (
    <OperatorView
      key={userRole}
      channelId={userRole}
      telemetry={telemetryByChannel[userRole]}
      onLocalTelemetry={onLocalTelemetry}
    />
  );
};
