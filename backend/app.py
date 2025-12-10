import eventlet
eventlet.monkey_patch()
import os
import threading
import socket
import json
from datetime import datetime
import time
import sqlite3
from flask import Flask, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# TCP Server configuration
TCP_HOST = '0.0.0.0'
TCP_PORT = 8080

DATABASE = 'devices.db'

# Flask & WebSocket configuration
app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')
CORS(app)  # Allow cross-origin requests for React dev server

socketio = SocketIO(app, cors_allowed_origins="*")

# -----------------------------------------------------------------------------
# Database Management
# -----------------------------------------------------------------------------

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the devices table if it doesn't exist."""
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ip TEXT NOT NULL UNIQUE,
                mac TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("[DB] Database initialized.")


# -----------------------------------------------------------------------------
# State Management (Replaces Tkinter class variables)
# -----------------------------------------------------------------------------

# A thread-safe way to store application state
state = {
    'tcp_server_running': False,
    'tcp_server_socket': None,
    'clients': {},  # {client_id: {'socket': socket, 'ip': ip, 'mac': 'N/A', ...}}
    'led_states': {},  # {client_id: 'on'/'off'}
    'alarming_clients': {}, # {client_id: True/False}
    'logs': [],
    'client_counter': 0,
    'message_count': 0,
    'last_activity_time': None,
    'lock': threading.RLock(),
    'last_seen': {},
    'global_selected_sound': 'beep.mp3',
}

# -----------------------------------------------------------------------------
# TCP Server for ESP32 Devices (Runs in a background thread)
# -----------------------------------------------------------------------------

def log_and_emit(message, message_type="SERVER"):
    """Logs a message and emits it to all connected web clients."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {
        'timestamp': timestamp,
        'message': message,
        'type': message_type
    }
    
    with state['lock']:
        state['logs'].append(log_entry)
        # To avoid growing the log list indefinitely, you might want to cap its size
        # state['logs'] = state['logs'][-200:]
    
    socketio.emit('new_log', log_entry)


def _get_current_client_and_led_states():
    """Helper function to get the current client list and LED states."""
    with state['lock']:
        conn = get_db_connection()
        devices = conn.execute('SELECT * FROM devices').fetchall()
        conn.close()

        client_list = []
        led_states = {}
        
        for device in devices:
            device_id = device['id']
            is_connected = device_id in state['clients']
            
            if is_connected:
                current_led_state = state['led_states'].get(device_id, 'connected')
            else:
                current_led_state = 'off'
            print("device_id:",device_id," current_led_state:",current_led_state)
            client_list.append({
                'id': device_id,
                'name': device['name'],
                'ip': device['ip'],
                'mac': device['mac'],
                'led_state': current_led_state
            })
            led_states[device_id] = current_led_state
    return client_list, led_states

def update_clients_and_leds_on_frontend():
    """Emits the current client list and LED states to all connected web clients."""
    client_list, led_states = _get_current_client_and_led_states()
    socketio.emit('update_clients', client_list)
    socketio.emit('update_leds', led_states)
    update_dashboard_on_frontend()



def update_dashboard_on_frontend():
    """Emits general status updates to the frontend."""
    with state['lock']:
        status = {
            'server_running': state['tcp_server_running'],
            'client_count': len(state['clients']),
            'message_count': state['message_count'],
            'last_activity': state['last_activity_time'].strftime("%H:%M:%S") if state['last_activity_time'] else "N/A"
        }
    socketio.emit('update_dashboard', status)

def process_esp_message(message, client_ip, client_id):
    """Processes a message from an ESP32 and updates the state."""
    print(f"[TCP Handler {client_id}] Processing message: {message}")
    try:
        data = json.loads(message)
        message_type = data.get('type', 'unknown')

        with state['lock']:
            state['last_seen'][client_id] = datetime.now()
            if message_type == 'connection':
                if client_id in state['clients']:
                    state['clients'][client_id]['mac'] = data.get('mac', 'N/A')
                log_and_emit(
                    f"Device registered - ID: {client_id}, MAC: {data.get('mac', 'N/A')}", "CLIENT"
                )
                
            elif message_type == 'button_press':
                state['message_count'] += 1
                state['last_activity_time'] = datetime.now()
                state['led_states'][client_id] = 'alarm'

                log_and_emit(
                    f"BUTTON PRESS from client {client_id} (IP: {client_ip})", "RECV"
                )
                
                # Buzzer and alarm state are now handled by handle_play_buzzer
                handle_play_buzzer(client_id)

            else:
                log_and_emit(f"Unknown message type from {client_id}: {message}", "WARNING")

        # After processing, send updates to all web clients
        update_clients_and_leds_on_frontend()

    except json.JSONDecodeError:
        log_and_emit(f"Invalid JSON from client {client_id}: {message}", "ERROR")
    except Exception as e:
        log_and_emit(f"Error processing message from {client_id}: {e}", "ERROR")


def handle_esp_client(client_socket, client_ip, client_id):
    """Handles a single ESP32 client connection."""
    print(f"[TCP Handler {client_id}] Thread started for {client_ip}")
    buffer = ""
    while True:
        try:
            # Check if this client is still considered active
            with state['lock']:
                if client_id not in state['clients'] or state['clients'][client_id]['socket'] != client_socket:
                    break
            
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                print(f"[TCP Handler {client_id}] Received empty data. Client disconnected.")
                break  # Connection closed by client

            print(f"[TCP Handler {client_id}] Received raw data: {data}")
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line.strip():
                    process_esp_message(line.strip(), client_ip, client_id)

        except (ConnectionResetError, BrokenPipeError):
            print(f"[TCP Handler {client_id}] Connection lost abruptly.")
            break
        except Exception as e:
            print(f"[TCP Handler {client_id}] Error: {e}")
            log_and_emit(f"Error with client {client_id}: {e}", "ERROR")
            break

    # Cleanup after disconnection
    print(f"[TCP Handler {client_id}] Cleaning up and closing connection for {client_ip}.")
    log_message = None
    with state['lock']:
        if client_id in state['clients']:
            log_message = f"Client {client_id} ({client_ip}) disconnected."
            state['clients'][client_id]['socket'].close()
            del state['clients'][client_id]
            if client_id in state['led_states']:
                 del state['led_states'][client_id]
    
    if log_message:
        log_and_emit(log_message, "CLIENT")

    update_clients_and_leds_on_frontend()
    print(f"[TCP Handler {client_id}] Thread finished for {client_ip}.")


def tcp_server_loop():
    """The main loop for the TCP server accepting ESP32 connections."""
    log_and_emit("TCP server loop started.", "SERVER")
    print("[TCP Server] Loop started.")

    try:
        while True:
            # Check current running state and socket safely under lock
            with state['lock']:
                running = state['tcp_server_running']
                server_socket = state['tcp_server_socket']

            if not running or server_socket is None:
                print("[TCP Server] Stopping loop because server_running is False or socket is None.")
                break

            try:
                # accept() may timeout because of settimeout(1.0)
                client_socket, client_address = server_socket.accept()
                print(f"[TCP Server] Accepted connection from {client_address}")

                # --- Configure TCP Keep-Alive (Linux-specific) ---
                # This helps detect disconnected clients (e.g., unplugged cable) much faster
                # than the default OS settings. The OS will automatically send probes on idle
                # connections and close them if the probes are not answered.
                try:
                    # Enable keep-alive probes on the socket
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    
                    # The following options are available on Linux and some other OSes
                    if hasattr(socket, 'TCP_KEEPIDLE'):
                        # Time (in seconds) the connection needs to be idle before sending the first keep-alive probe.
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 2)
                    
                    if hasattr(socket, 'TCP_KEEPINTVL'):
                        # Interval (in seconds) between subsequent keep-alive probes.
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
                        
                    if hasattr(socket, 'TCP_KEEPCNT'):
                        # Number of unanswered probes before considering the connection dead.
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 2)
                        
                except OSError as e:
                    print(f"[TCP Server] Warning: Could not set all TCP keep-alive options: {e}")

                client_ip = client_address[0]

                # --- Authorization Check ---
                conn = get_db_connection()
                try:
                    device = conn.execute(
                        'SELECT * FROM devices WHERE ip = ?',
                        (client_ip,)
                    ).fetchone()
                finally:
                    conn.close()

                if device is None:
                    log_and_emit(
                        f"Rejected connection from unauthorized IP: {client_ip}",
                        "WARNING"
                    )
                    client_socket.close()
                    continue  # Move to the next connection attempt

                # --- If Authorized, Proceed ---
                with state['lock']:
                    # Use the database ID as the client_id for consistency
                    client_id = device['id']

                    # If the client is already connected, handle re-connection
                    if client_id in state['clients']:
                        print(f"[TCP Server] Client {client_id} is reconnecting. Closing old socket.")
                        try:
                            state['clients'][client_id]['socket'].close()
                        except Exception as e:
                            print(f"[TCP Server] Error closing old socket for {client_id}: {e}")

                    state['clients'][client_id] = {
                        'socket': client_socket,
                        'ip': client_ip,
                        'mac': device['mac']  # Get MAC from DB
                    }
                    state['led_states'][client_id] = 'connected'

                eventlet.spawn(
                    handle_esp_client,
                    client_socket,
                    client_ip,
                    client_id
                )

                log_and_emit(
                    f"Authorized client {client_ip} connected. Assigned ID {client_id}",
                    "SERVER"
                )
                update_clients_and_leds_on_frontend()

            except socket.timeout:
                # Normal case due to settimeout(1.0); just loop again
                continue

            except OSError as e:
                # Usually means the server socket was closed or is invalid
                print(f"[TCP Server] OS Error on accept: {e}")
                log_and_emit(f"TCP server socket error: {e}", "ERROR")
                break

            except Exception as e:
                # Unexpected error: log it, but don't kill the entire server unless it keeps repeating
                print(f"[TCP Server] Unexpected error on accept/handling: {e}")
                log_and_emit(f"TCP server error: {e}", "ERROR")
                # continue listening for new connections
                continue

    finally:
        # Clean shutdown / state update
        with state['lock']:
            if state['tcp_server_socket'] is not None:
                try:
                    state['tcp_server_socket'].close()
                except Exception:
                    pass
                state['tcp_server_socket'] = None

            state['tcp_server_running'] = False

        print("[TCP Server] Loop finished.")
        log_and_emit("TCP server loop finished.", "SERVER")
        update_dashboard_on_frontend()

def start_tcp_server():
    print("[start_tcp_server] Function called.")
    """Initializes and starts the TCP server."""
    if state['tcp_server_running']:
        print("[Main] TCP server is already running.")
        log_and_emit("TCP server is already running.", "WARNING")
        return

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print(f"[Main] Binding TCP server to {TCP_HOST}:{TCP_PORT}...")
        server_socket.bind((TCP_HOST, TCP_PORT))
        server_socket.listen(5)
        server_socket.settimeout(1.0)  # Non-blocking accept

        with state['lock']:
            state['tcp_server_socket'] = server_socket
            state['tcp_server_running'] = True

        eventlet.spawn(tcp_server_loop)
        print("[Main] TCP server thread started.")
        
        log_and_emit(f"TCP server started on {TCP_HOST}:{TCP_PORT}", "SERVER")
        update_dashboard_on_frontend()
    except Exception as e:
        print(f"[Main] Failed to start TCP server: {e}")
        log_and_emit(f"Failed to start TCP server: {e}", "ERROR")
        state['tcp_server_running'] = False
        update_dashboard_on_frontend()




# Watchdog thread to remove inactive clients
def client_timeout_watcher(timeout_seconds, interval_seconds):
    """
    Periodically checks for clients that haven't sent an application message recently.
    If a client is silent for too long, its connection is assumed to be stalled or dead,
    and the watcher forcefully closes the socket. This allows the client's handler
    thread to perform a full cleanup.
    """
    while True:
        time.sleep(interval_seconds)
        now = datetime.now()

        # Create a list of clients to drop to avoid modifying dict while iterating
        clients_to_close = []
        with state['lock']:
            # Check for clients that are connected but haven't sent data
            for client_id, last_seen_time in state['last_seen'].items():
                if client_id in state['clients'] and (now - last_seen_time).total_seconds() > timeout_seconds:
                    clients_to_close.append(client_id)
        
        # Now, close the sockets for the timed-out clients
        for client_id in clients_to_close:
            with state['lock']:
                # Check if client still exists before trying to close
                if client_id in state['clients']:
                    client_socket = state['clients'][client_id]['socket']
                    log_and_emit(
                        f"Client {client_id} timed out after {timeout_seconds}s of inactivity. Closing connection.",
                        "SERVER"
                    )
                    try:
                        # Closing the socket will cause the recv() in the client's
                        # handler thread to raise an exception, which triggers the full cleanup.
                        client_socket.close()
                    except Exception as e:
                        print(f"[Watcher] Error closing socket for timed-out client {client_id}: {e}")

# -----------------------------------------------------------------------------
# WebSocket Event Handlers (Communication with React Frontend)
# -----------------------------------------------------------------------------

@socketio.on('connect')
def handle_connect():
    """Handler for when a new web client connects."""
    log_and_emit("Web UI connected.", "SERVER")

    # Send current clients + LEDs
    client_list, led_states = _get_current_client_and_led_states()
    emit('update_clients', client_list, broadcast=False)
    emit('update_leds', led_states, broadcast=False)

    # Send logs
    with state['lock']:
        logs = state['logs'][:]
        status = {
            'server_running': state['tcp_server_running'],
            'client_count': len(state['clients']),
            'message_count': state['message_count'],
            'last_activity': state['last_activity_time'].strftime("%H:%M:%S")
                             if state['last_activity_time'] else "N/A"
        }

    emit('all_logs', logs, broadcast=False)
    emit('update_dashboard', status, broadcast=False)


@socketio.on('reset_all_leds')
def handle_reset_leds():
    """
    Resets all LED states to 'connected' and clears internal alarm states.
    Emits an event to the frontend to stop any sounds it might be playing.
    """
    with state['lock']:
        # Reset internal LED and alarm states
        for client_id in list(state['alarming_clients'].keys()):
            state['led_states'][client_id] = 'connected'
            state['alarming_clients'][client_id] = False
        
        # Clear the dictionaries safely
        state['alarming_clients'].clear()
        if 'alarm_channels' in state:
            state['alarm_channels'].clear() # Still good to clear our internal reference

    log_and_emit("All LEDs and internal alarm states have been reset.", "SERVER")
    
    # Instruct the frontend to stop all sounds
    socketio.emit('stop_all_sounds_on_frontend')
    log_and_emit("Sent request to frontend to stop all sounds.", "SERVER")
    
    update_clients_and_leds_on_frontend()

@socketio.on('send_test_message')
def handle_send_test_message(data):
    """Sends a test message to one or all ESP32 clients."""
    client_id_to_send = data.get('client_id') # can be "all" or a specific ID
    message = json.dumps({
        "type": "test",
        "message": "Hello from Flask!",
        "timestamp": time.time()
    }) + '\n'

    with state['lock']:
        clients_to_send_to = []
        if client_id_to_send == 'all':
            clients_to_send_to = state['clients'].items()
            log_msg = "Sending test message to all clients."
        elif client_id_to_send in state['clients']:
            clients_to_send_to = [(client_id_to_send, state['clients'][client_id_to_send])]
            log_msg = f"Sending test message to client {client_id_to_send}."
        else:
            log_msg = f"Cannot send test message: Client {client_id_to_send} not found."
            clients_to_send_to = []
        
        log_and_emit(log_msg, "SERVER")
        
        for cid, client in clients_to_send_to:
            try:
                client['socket'].send(message.encode('utf-8'))
            except Exception as e:
                log_and_emit(f"Failed to send to client {cid}: {e}", "ERROR")

@socketio.on('disconnect_client')
def handle_disconnect_client(data):
    """Forcefully disconnects an ESP32 client."""
    client_id = data.get('client_id')
    with state['lock']:
        if client_id in state['clients']:
            log_and_emit(f"Disconnecting client {client_id} by UI request.", "SERVER")
            state['clients'][client_id]['socket'].close() # This will trigger the cleanup in handle_esp_client
            # The removal from the dict happens in the client handler thread
        else:
            log_and_emit(f"Cannot disconnect: Client {client_id} not found.", "WARNING")

@socketio.on('clear_logs')
def handle_clear_log():
    with state['lock']:
        state['logs'].clear()
        state['message_count'] = 0
    log_and_emit("Log cleared by user.", "SERVER")
    update_dashboard_on_frontend()

@socketio.on('reset_alarm')
def handle_reset_alarm(data):
    client_id = data.get('client_id')
    with state['lock']:
        if client_id in state['alarming_clients']:
            state['alarming_clients'][client_id] = False
            # Optionally reset LED state from 'alarm' to 'connected' or 'off'
            if state['led_states'].get(client_id) == 'alarm':
                state['led_states'][client_id] = 'connected'
            log_and_emit(f"Alarm reset for client {client_id}.", "SERVER")
        else:
            log_and_emit(f"No active alarm found for client {client_id}.", "WARNING")
    update_clients_and_leds_on_frontend()

@socketio.on('set_default_sound')
def set_default_sound(data):
    """Sets the default alarm sound for a client."""
    client_id = data.get('client_id')
    sound_file = data.get('sound')
    if client_id and sound_file:
        with state['lock']:
            state['client_sound_prefs'][client_id] = sound_file
            log_and_emit(f"Default alarm for client {client_id} set to '{sound_file}'.", "SERVER")

@socketio.on('set_global_sound')
def set_global_sound(data):
    """Sets the global alarm sound."""
    sound_file = data.get('sound')
    if sound_file:
        with state['lock']:
            if state['global_selected_sound'] != sound_file:
                state['global_selected_sound'] = sound_file
                log_and_emit(f"Global alarm sound set to '{sound_file}'.", "SERVER")

@socketio.on('play_buzzer')
def handle_play_buzzer(data):
    """
    Handles setting the alarm state when a buzzer is triggered.
    This function NO LONGER plays the sound directly. Instead, it sets the
    alarm state and emits an event to the frontend, instructing it to play the sound.
    """
    with state['lock']:
        if isinstance(data, dict):
            client_id = data.get('client_id')
        else:
            client_id = data

        if client_id is None:
            log_and_emit("play_buzzer called without a client_id.", "ERROR")
            return

        sound_file = state.get('client_sound_prefs', {}).get(client_id, state['global_selected_sound'])

        if not state['alarming_clients'].get(client_id, False):
            state['alarming_clients'][client_id] = True
            state['led_states'][client_id] = 'alarm'
            log_and_emit(f"Alarm activated for client {client_id}.", "SERVER")
        else:
            log_and_emit(f"Buzzer re-triggered for client {client_id} (already alarming).", "WARNING")

        # Emit an event to the frontend to play the sound
        socketio.emit('play_sound_on_frontend', {'client_id': client_id, 'sound': sound_file})
        log_and_emit(f"Sent request to frontend to play '{sound_file}' for client {client_id}.", "SERVER")

        update_clients_and_leds_on_frontend()


# -----------------------------------------------------------------------------
# Flask Routes (Serving the React App)
# -----------------------------------------------------------------------------

@app.route('/')
def serve_react_app():
    """Serves the main index.html of the React app."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    """Serves static files like JS, CSS, images for the React app."""
    return send_from_directory(app.static_folder, path)


# -----------------------------------------------------------------------------
# API Routes for Device Management
# -----------------------------------------------------------------------------

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """API endpoint to get all registered devices."""
    conn = get_db_connection()
    devices = conn.execute('SELECT * FROM devices').fetchall()
    conn.close()
    return jsonify([dict(row) for row in devices])

@app.route('/api/devices', methods=['POST'])
def add_device():
    """API endpoint to add a new device."""
    new_device = request.json
    name = new_device.get('name')
    ip = new_device.get('ip')
    mac = new_device.get('mac')

    if not name or not ip:
        return jsonify({'error': 'Name and IP are required'}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO devices (name, ip, mac) VALUES (?, ?, ?)', (name, ip, mac))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        # After adding, fetch all devices again to update the frontend
        update_clients_and_leds_on_frontend()
        
        return jsonify({'id': new_id, 'name': name, 'ip': ip, 'mac': mac}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'IP address already exists'}), 409

@app.route('/api/devices/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    """API endpoint to update an existing device."""
    device_data = request.json
    name = device_data.get('name')
    ip = device_data.get('ip')
    mac = device_data.get('mac')

    if not name or not ip:
        return jsonify({'error': 'Name and IP are required'}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE devices SET name = ?, ip = ?, mac = ? WHERE id = ?',
            (name, ip, mac, device_id)
        )
        conn.commit()
        conn.close()
        
        # After updating, fetch all devices again to update the frontend
        update_clients_and_leds_on_frontend()
        
        return jsonify({'id': device_id, 'name': name, 'ip': ip, 'mac': mac}), 200
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'IP address already exists for another device'}), 409

@app.route('/api/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    """API endpoint to delete a device."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM devices WHERE id = ?', (device_id,))
    conn.commit()
    conn.close()
    
    # After deleting, fetch all devices again to update the frontend
    update_clients_and_leds_on_frontend()
    
    return jsonify({'message': 'Device deleted successfully'}), 200

    
# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------

if __name__ == '__main__':

    print("--- Turbo Tech Backend Starting ---")

    print("--- Turbo Tech Backend ---")

    init_db()  # Initialize the database

    start_tcp_server()

    # Start the watchdog to clean up stale connections

    # eventlet.spawn(client_timeout_watcher, timeout_seconds=30, interval_seconds=15)



    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)
