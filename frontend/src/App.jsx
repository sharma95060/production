import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import StatusDashboard from './components/StatusDashboard';
import ControlButtons from './components/ControlButtons';
import ClientsTable from './components/ClientsTable';
import LedGrid from './components/LedGrid';
import MessageLog from './components/MessageLog';
import AddDeviceDialog from './components/AddDeviceDialog';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import './App.css';

const soundModules = import.meta.glob('./alarm/*.mp3', { eager: true });
const soundMap = Object.fromEntries(
  Object.entries(soundModules).map(([path, module]) => [
    path.split('/').pop(),
    module.default,
  ])
);
const soundFiles = Object.keys(soundMap);


// Establish a single socket connection
const socket = io();

function App() {
  const [dashboardStatus, setDashboardStatus] = useState({
    server_running: false,
    client_count: 0,
    message_count: 0,
    last_activity: "N/A"
  });
  const [clients, setClients] = useState([]);
  const [leds, setLeds] = useState({});
  const [logs, setLogs] = useState([]);
  const [activeClientId, setActiveClientId] = useState(null);
  const [editingDevice, setEditingDevice] = useState(null);
  const [deletingDevice, setDeletingDevice] = useState(null);
  const [isAddDeviceOpen, setAddDeviceOpen] = useState(false);

  const [alarmingClientId, setAlarmingClientId] = useState(null);
  const [globalSound, setGlobalSound] = useState(() => {
    return localStorage.getItem('globalAlarmSound') || 'beep.mp3';
  });

  const audioRef = useRef(null);

  const stopSound = () => {
    if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        audioRef.current.loop = false;
    }
  };

  useEffect(() => {
    localStorage.setItem('globalAlarmSound', globalSound);
  }, [globalSound]);
  
  useEffect(() => {
    const handleUpdateClients = (clientList) => {
     console.log("Received updated client list:", clientList);
      setClients(clientList);
      
      setAlarmingClientId((prevAlarming) => {
        if (!prevAlarming) return null;
        const current = clientList.find(c => c.id === prevAlarming);
        const isStillAlarming = current && current.led_state === 'alarm';
        if (!isStillAlarming) {
          stopSound();
          return null;
        }
        return isStillAlarming ? prevAlarming : null;
      });
    };
  
    const handleUpdateDashboard = (status) => {
      setDashboardStatus(status);
    };

    const handleUpdateLeds = (ledStates) => {
      setLeds(ledStates);
    };

    const handlePlaySoundOnFrontend = ({ client_id, sound }) => {
      setAlarmingClientId(client_id);
      const soundFile = soundMap[sound] || soundMap['beep.mp3'];
      if (audioRef.current) {
        audioRef.current.loop = true; // Alarms should loop
        audioRef.current.src = soundFile;
        audioRef.current.play().catch(e => console.error("Audio playback failed:", e));
      }
    };

    const handleStopAllSounds = () => {
        stopSound();
        setAlarmingClientId(null);
    };

    const handleNewLog = (log) => setLogs(prev => [...prev, log]);
    const handleAllLogs = (allLogs) => setLogs(allLogs);

    const handleDisconnect = () => {
      console.log('Socket disconnected from server.');
      handleUpdateClients([]);
    };
  
    socket.on('all_logs', handleAllLogs);
    socket.on('new_log', handleNewLog);
    socket.on('update_dashboard', handleUpdateDashboard);    
    socket.on('update_clients', handleUpdateClients);
    socket.on('update_leds', handleUpdateLeds);
    socket.on('play_sound_on_frontend', handlePlaySoundOnFrontend);
    socket.on('stop_all_sounds_on_frontend', handleStopAllSounds);
    socket.on('disconnect', handleDisconnect);

    return () => {
      socket.off('all_logs', handleAllLogs);
      socket.off('new_log', handleNewLog);
      socket.off('update_dashboard', handleUpdateDashboard);
      socket.off('update_clients', handleUpdateClients);
      socket.off('update_leds', handleUpdateLeds);
      socket.off('play_sound_on_frontend', handlePlaySoundOnFrontend);
      socket.off('stop_all_sounds_on_frontend', handleStopAllSounds);
      socket.off('disconnect', handleDisconnect);
    };
  }, [alarmingClientId]); 
  
  const handleResetLeds = () => {
    socket.emit('reset_all_leds');
    stopSound();
    setAlarmingClientId(null);
  };
  
  const handleClearLog = () => {
    setLogs([]);
    socket.emit('clear_logs');
  };
  
  const handleResetAlarm = () => {
    if (activeClientId) {
      socket.emit('reset_alarm', { client_id: activeClientId });
    } else {
      console.warn("No client selected to reset alarm.");
    }
  };
  
  const handleSendTestMessage = () => {
    const target = activeClientId || 'all';
    socket.emit('send_test_message', { client_id: target });
  };
  
  const handleDisconnectClient = () => {
    if (activeClientId) {
      socket.emit('disconnect_client', { client_id: activeClientId });
      setActiveClientId(null);
    }
  };
  
  const handleDisconnectAll = () => {
    clients.forEach(c => {
        if (c.led_state && c.led_state !== 'off') {
            socket.emit('disconnect_client', { client_id: c.id });
        }
    });
    setActiveClientId(null);
  };

  const handleOpenAddDevice = () => {
    setEditingDevice(null);
    setAddDeviceOpen(true);
  };

  const handleCloseAddDevice = () => {
    setAddDeviceOpen(false);
    setEditingDevice(null);
  };

  const handleDeviceAdded = () => {
    handleCloseAddDevice();
    socket.emit('get_clients');
  };

  const handleEditDevice = (device) => {
    setEditingDevice(device);
    setAddDeviceOpen(true);
  };

  const handleDeleteDevice = (device) => {
    setDeletingDevice(device);
  };

  const confirmDeleteDevice = async () => {
    if (deletingDevice) {
      try {
        const response = await fetch(`http://localhost:5000/api/devices/${deletingDevice.id}`, {
          method: 'DELETE',
        });
        if (response.ok) {
          toast.success('Device deleted successfully');
          setClients(clients.filter(c => c.id !== deletingDevice.id));
        } else {
          toast.error('Failed to delete device');
        }
      } catch (err) {
        toast.error("Failed to delete device");
        console.error("Failed to delete device", err);
      } finally {
        setDeletingDevice(null);
      }
    }
  };

  const cancelDeleteDevice = () => {
    setDeletingDevice(null);
  };

  const handleSetDefaultSound = (data) => {
    socket.emit('set_default_sound', data);
  };

  const handleSetGlobalSound = (sound) => {
    setGlobalSound(sound);
    socket.emit('set_global_sound', { sound });
  };

  const handlePlayTestSound = () => {
    const soundFile = soundMap[globalSound];
    if (audioRef.current) {
        if (audioRef.current.paused || audioRef.current.ended) {
            audioRef.current.loop = false; // Test sound should not loop
            audioRef.current.src = soundFile;
            audioRef.current.play().catch(e => console.error("Audio playback failed:", e));
        } else {
            stopSound();
        }
    }
  };


  return (
    <>
      <ToastContainer />
      <div className="app-container">
        <header className="header">
          <h1>Turbo Tech</h1>
        </header>

        <div className="sidebar">
          <StatusDashboard status={dashboardStatus} />
          <ControlButtons
            onResetLeds={handleResetLeds}
            onClearLog={handleClearLog}
            onSendTest={handleSendTestMessage}
            onDisconnect={handleDisconnectClient}
            onDisconnectAll={handleDisconnectAll}
            onAddDevice={handleOpenAddDevice}
            hasActiveClient={!!activeClientId}
            onResetAlarm={handleResetAlarm}
            alarmingClientId={alarmingClientId}
            activeClientId={activeClientId}
          />
        </div>

        <div className="main-content">
          <LedGrid
            clients={clients}
            leds={leds}
            alarmingClientId={alarmingClientId}
            activeClientId={activeClientId}
            onSetDefaultSound={handleSetDefaultSound}
            soundFiles={soundFiles}
            globalSound={globalSound}
            onSetGlobalSound={handleSetGlobalSound}
            onPlayTestSound={handlePlayTestSound}
            onEdit={handleEditDevice}
            onDelete={handleDeleteDevice}
          />
          <ClientsTable
            clients={clients}
            activeClientId={activeClientId}
            onClientSelect={setActiveClientId}
            alarmingClientId={alarmingClientId}
          />
          <MessageLog logs={logs} />
        </div>
      </div>

      {(isAddDeviceOpen || editingDevice) && (
        <AddDeviceDialog
          onClose={handleCloseAddDevice}
          onDeviceAdded={handleDeviceAdded}
          device={editingDevice}
        />
      )}

      {deletingDevice && (
        <div className="dialog-backdrop">
          <div className="dialog-content">
            <h2>Confirm Deletion</h2>
            <p>Are you sure you want to delete the device "{deletingDevice.name}"?</p>
            <div className="form-actions">
              <button onClick={confirmDeleteDevice} className="btn-danger">Delete</button>
              <button onClick={cancelDeleteDevice} className="btn-secondary">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <audio ref={audioRef} src={soundMap['beep.mp3']} preload="auto"></audio>
    </>
  );
}


export default App;