import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App';
import { mockData } from './mockData';
import type { DashboardData } from './types';

const data: DashboardData =
  (window as unknown as { __DASHBOARD_DATA__?: DashboardData }).__DASHBOARD_DATA__ ?? mockData;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App data={data} />
  </StrictMode>,
);
