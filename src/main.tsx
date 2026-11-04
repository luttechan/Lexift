import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

if (new URLSearchParams(location.search).has('notice-popup')) {
  document.documentElement.classList.add('notice-window');
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
