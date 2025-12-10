import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import './AddDeviceDialog.css';

const AddDeviceDialog = ({ onClose, onDeviceAdded, device }) => {
    const [name, setName] = useState('');
    const [ip, setIp] = useState('');
    const [mac, setMac] = useState('');

    const isEditMode = device != null;

    useEffect(() => {
        if (isEditMode) {
            setName(device.name);
            setIp(device.ip);
            setMac(device.mac || '');
        }
    }, [device, isEditMode]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!name || !ip) {
            toast.error('Device Name and IP Address are required.');
            return;
        }

        const url = isEditMode
            ? `http://localhost:5000/api/devices/${device.id}`
            : 'http://localhost:5000/api/devices';
        
        const method = isEditMode ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, ip, mac }),
            });

            if (response.ok) {
                const savedDevice = await response.json();
                toast.success(`Device ${isEditMode ? 'updated' : 'added'} successfully`);
                onDeviceAdded(savedDevice);
                onClose();
            } else {
                const errorData = await response.json();
                toast.error(errorData.error || `Failed to ${isEditMode ? 'update' : 'add'} device.`);
            }
        } catch (err) {
            toast.error('An error occurred while communicating with the server.');
        }
    };

    return (
        <div className="dialog-backdrop">
            <div className="dialog-content">
                <h2>{isEditMode ? 'Edit Device' : 'Add New Device'}</h2>
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="name">Device Name</label>
                        <input
                            type="text"
                            id="name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="ip">IP Address</label>
                        <input
                            type="text"
                            id="ip"
                            value={ip}
                            onChange={(e) => setIp(e.target.value)}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="mac">MAC Address (Optional)</label>
                        <input
                            type="text"
                            id="mac"
                            value={mac}
                            onChange={(e) => setMac(e.target.value)}
                        />
                    </div>
                    <div className="form-actions">
                        <button type="submit" className="btn-primary">
                            {isEditMode ? 'update' : 'Save'}
                        </button>
                        <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddDeviceDialog;
