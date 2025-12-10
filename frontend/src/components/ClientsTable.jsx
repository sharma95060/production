import React from 'react';
import './ClientsTable.css';

const ClientsTable = ({ clients, activeClientId, onClientSelect, alarmingClientId }) => {
  
  const handleRowClick = (clientId) => {
    if (activeClientId === clientId) {
      onClientSelect(null); // Deselect if clicking the already active client
    } else {
      onClientSelect(clientId);
    }
  };

  return (
    <div className="card">
      <h3>Registered ESP32 Devices</h3>
      <div className="table-container">
        <table className="clients-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>IP Address</th>
              <th>MAC Address</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {clients.length > 0 ? (
              clients.map((client) => (
                <tr 
                  key={client.id} 
                  onClick={() => handleRowClick(client.id)}
                  className={`${client.id === activeClientId ? 'active-row' : ''} ${client.id === alarmingClientId ? 'alarming-row' : ''}`}
                >
                  <td>{client.id}</td>
                  <td>{client.name}</td>
                  <td>{client.ip}</td>
                  <td>{client.mac || 'N/A'}</td>
                  <td className={`status-${client.led_state}`}>
                    {client.led_state}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="5" className="no-clients-message">No devices registered.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ClientsTable;
