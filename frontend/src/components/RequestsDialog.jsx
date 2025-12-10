import React from 'react';
import './RequestsDialog.css';

const RequestsDialog = ({ isOpen, onClose, pendingClients, onAccept, onReject }) => {
    if (!isOpen) {
        return null;
    }

    return (
        <div className="dialog-overlay">
            <div className="dialog-content">
                <h2>Pending Client Requests</h2>
                <button className="close-button" onClick={onClose}>×</button>
                {pendingClients.length === 0 ? (
                    <p>No pending requests.</p>
                ) : (
                    <table className="requests-table">
                        <thead>
                            <tr>
                                <th>Pending ID</th>
                                <th>IP Address</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {pendingClients.map(client => (
                                <tr key={client.id}>
                                    <td>{client.id}</td>
                                    <td>{client.ip}</td>
                                    <td className="actions-cell">
                                        <button className="accept-button" onClick={() => onAccept(client.id)}>Accept</button>
                                        <button className="reject-button" onClick={() => onReject(client.id)}>Reject</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};

export default RequestsDialog;
