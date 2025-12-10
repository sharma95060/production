# Turbo Tech (Flask + React)

A complete web-based control center for managing and monitoring EMC485 devices, featuring a Python/Flask backend and a modern React UI.

- **Real-Time Communication**: Utilizes WebSockets for instant updates between the server and the UI.
- **Modern Frontend**: Built with React and Vite, providing a fast, responsive, and expressive user experience.
- **Concurrent Backend**: The Flask server uses threading to handle multiple TCP connections from ESP32 devices simultaneously.

## Project Structure

```
.
├── backend/
│   ├── app.py              # Main Flask application with TCP and WebSocket servers
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── dist/               # Production build output (generated)
│   ├── src/
│   │   ├── components/     # Reusable React components
│   │   ├── App.jsx         # Main application component and layout
│   │   ├── main.jsx        # React entry point
│   │   └── *.css           # Component and global styles
│   ├── index.html          # HTML template for the React app
│   ├── package.json        # Frontend dependencies and scripts
│   └── vite.config.js      # Vite configuration
└── README.md
```

## Setup and Installation

Requires **Python (3.10.0)** and **Node.js (18+)**.

### 1. Backend Setup (Ubuntu)

```bash
# Navigate to the backend directory
cd backend

# Install python3.10-venv if not already installed
sudo apt-get install python3.10-venv

# Create and activate a virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Run backend server
python app.py
```


### 2. Backend Setup (Windows)

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# run backend server
python app.py
```


**Note for Windows users:** The `eventlet` library, used for websocket communication, has limited support on Windows. The application may not function as expected.

### 3. Frontend Setup (Ubuntu and Windows)

```bash
# Navigate to the frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Run frontend server
npm run dev
```


### 4. Add Buzzer Sound

The application plays a sound for button press notifications. You must provide this file.

- Find or create a short sound file named `beep.mp3`.
- Place it inside the `frontend/public/` directory. If this directory doesn't exist, create it.

---

## Running the Application

You will need two terminals running simultaneously.

### Terminal 1: Start the Backend Server

**For Ubuntu:**
```bash
cd backend
source venv/bin/activate
python app.py
```

**For Windows:**
```bash
cd backend
venv\Scripts\activate
python app.py
```
> The backend runs on `http://localhost:5000` and the TCP server on port `8080`.

### Terminal 2: Start the Frontend Dev Server

**For Ubuntu and Windows:**
```bash
cd frontend
npm run dev
```
> The UI will be available at `http://localhost:3000`.

## Device Connection

To connect your ESP32 or other devices, they must connect to the TCP server on port `8080` of the machine running the backend. The backend will then be able to communicate with the devices.
