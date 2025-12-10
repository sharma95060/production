import React from 'react';
import LedIndicator from './LedIndicator'; // Import the LED component
import './StatusDashboard.css';

const StatusDashboard = ({ status }) => {
  // Determine the LED state based on server status
  const serverLedState = status.server_running ? 'on' : 'off';
  const serverStatusText = status.server_running ? 'Running' : 'Stopped';

  return (
    <div className="card">
      <h3>Server Status</h3>
      <div className="status-grid">
        <span className="status-label">TCP Server:</span>
        <div className="server-status-container">
          <span className="status-value">{serverStatusText}</span>
        </div>

        <span className="status-label">Connected Clients:</span>
        <span className="status-value">{status.client_count}</span>

        <span className="status-label">Button Messages:</span>
        <span className="status-value">{status.message_count}</span>

        <span className="status-label">Last Activity:</span>
        <span className="status-value">{status.last_activity}</span>
      </div>
    </div>
  );
};

export default StatusDashboard;
