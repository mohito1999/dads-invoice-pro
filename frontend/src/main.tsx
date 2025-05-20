// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { AuthProvider } from './contexts/AuthContext.tsx';
import { OrgProvider } from './contexts/OrgContext.tsx'; // <--- Import OrgProvider

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <OrgProvider> {/* <--- Wrap App with OrgProvider */}
        <App />
      </OrgProvider>
    </AuthProvider>
  </React.StrictMode>,
);