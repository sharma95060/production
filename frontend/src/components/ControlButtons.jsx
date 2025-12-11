import React from 'react';
import './ControlButtons.css';

const ControlButtons = ({
    onResetLeds,
    onClearLog,
    onSendTest,
    onDisconnect,
    onDisconnectAll,
    onAddDevice, // New prop
    hasActiveClient,
    onResetAlarm, // New prop
    alarmingClientId, // New prop
    activeClientId // Add activeClientId prop
}) => {
  const isAlarmingClientSelected = hasActiveClient && activeClientId === alarmingClientId;

  return (
    <div className="card">
      <h3>System Controls</h3>
      <div className="control-buttons-grid">
        {/* New Device action */}
        <button
          onClick={onAddDevice}
          className="btn btn-primary full-width"
        >
          Add New Device
        </button>

        {/* Primary actions */}
        <button
          onClick={onSendTest}
          className="btn btn-secondary full-width" // Changed to secondary
        >
          Send Test Message
        </button>

        {/* Secondary actions */}
        <button
          onClick={isAlarmingClientSelected ? onResetAlarm : onResetLeds}
          className={`btn ${isAlarmingClientSelected ? 'btn-warning' : 'btn-secondary'}`}
          disabled={isAlarmingClientSelected && !hasActiveClient} // Disable if trying to reset alarm without a selected client
        >
          {isAlarmingClientSelected ? 'Reset Alarm' : 'Reset LEDs'}
        </button>
        <button onClick={onClearLog} className="btn btn-secondary">
          Clear Log
        </button>

        {/* Destructive actions */}
        
      </div>
    </div>
  );
};

export default ControlButtons;

