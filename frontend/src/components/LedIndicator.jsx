import React from 'react';
import './LedIndicator.css';

const LedIndicator = ({ state = 'off' }) => {
  const classes = `led led-${state}`;
  return (
    <div className={classes}>
      <div className="led-glow"></div>
      <div className="led-highlight"></div>
    </div>
  );
};

export default LedIndicator;

