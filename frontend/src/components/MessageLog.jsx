import React, { useEffect, useRef } from 'react';
import './MessageLog.css';

const MessageLog = ({ logs }) => {
  const logContainerRef = useRef(null);

  // Effect to auto-scroll to the bottom.
  // Since the container is reversed, we scroll to the top.
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = 0;
    }
  }, [logs]);

  return (
    <div className="card">
      <h3>Message Log</h3>
      <div ref={logContainerRef} className="log-container">
        {/* Render logs in reverse to show newest first at the bottom */}
        {[...logs].reverse().map((log, index) => (
          <div key={index} className="log-entry">
            <span className="log-meta">[{log.timestamp}]</span>
            <span className={`log-message type-${log.type}`}>
              {log.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MessageLog;
