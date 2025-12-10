import React, { useState } from 'react';
import LedIndicator from './LedIndicator';
import './LedGrid.css';
import { CiEdit } from "react-icons/ci";
import { MdDeleteOutline } from "react-icons/md";
import { toast } from 'react-toastify';

const LedGrid = ({ 
    clients, 
    leds, 
    alarmingClientId, 
    activeClientId, 
    soundFiles, 
    globalSound, 
    onSetGlobalSound,
    onPlayTestSound,
    onEdit,
    onDelete
}) => {
    const [editingClientId, setEditingClientId] = useState(null);
    const [newName, setNewName] = useState('');

    const handleSoundChange = (e) => {
        onSetGlobalSound(e.target.value);
    };

    const handleNameChange = (e) => {
        setNewName(e.target.value);
    };

    const handleUpdateName = async (clientId) => {
        try {
            const response = await fetch(`http://localhost:5000/api/devices/${clientId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: newName }),
            });

            if (response.ok) {
                toast.success('Device name updated successfully');
                setEditingClientId(null);
                // Optionally, you can trigger a refresh of the client list here
            } else {
                toast.error('Failed to update device name');
            }
        } catch (error) {
            toast.error('An error occurred while updating the device name.');
        }
    };

    const handleKeyDown = (e, clientId) => {
        if (e.key === 'Enter') {
            handleUpdateName(clientId);
        }
    };

    return (
        <div className="card">
            <div className="card-header">
                <h3>Client LED Indicators</h3>
                <div className="alarm-controls">
                    <select value={globalSound} onChange={handleSoundChange}>
                        {soundFiles.map((sound) => (
                            <option key={sound} value={sound}>
                                {sound}
                            </option>
                        ))}
                    </select>
                    <button onClick={onPlayTestSound}>Play/Stop Test</button>
                </div>
            </div>

            {clients.length > 0 ? (
                <div className="led-grid-container">
                    {clients.map(client => (
                        <div
                            key={client.id}
                            className={`led-item ${client.id === alarmingClientId ? 'alarming' : ''}`}
                        >
                            <div className="led-actions">
                                <button onClick={() => onEdit(client)} className="edit-btn"><CiEdit /></button>
                                <button onClick={() => onDelete(client)} className="delete-btn"><MdDeleteOutline /></button>
                            </div>
                            <LedIndicator state={client.led_state || 'off'} />
                            <div className="led-label" onDoubleClick={() => { setEditingClientId(client.id); setNewName(client.name); }}>
                                {editingClientId === client.id ? (
                                    <input
                                        type="text"
                                        value={newName}
                                        onChange={handleNameChange}
                                        onKeyDown={(e) => handleKeyDown(e, client.id)}
                                        onBlur={() => handleUpdateName(client.id)}
                                        autoFocus
                                    />
                                ) : (
                                    <span className="led-name">{client.name}</span>
                                )}
                                <span className="led-ip">{client.ip}</span>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <p className="no-clients-message">No devices registered.</p>
            )}
        </div>
    );
};

export default LedGrid;
