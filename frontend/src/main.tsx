import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { JobPage } from './pages/JobPage';
import { TicketsPage } from './pages/TicketsPage';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<TicketsPage />} />
          <Route path="/jobs/:id" element={<JobPage />} />
          <Route
            path="*"
            element={
              <p>
                Page not found. <a href="/">Return to the inbox.</a>
              </p>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
