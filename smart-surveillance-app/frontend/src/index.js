import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { loadConfig } from './config';

// Create root and render App
const root = ReactDOM.createRoot(document.getElementById('root'));

// Load config asynchronously before rendering
loadConfig().then(() => {
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}).catch((error) => {
  console.error("Failed to load configuration:", error);
  // Render anyway using defaults
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
});