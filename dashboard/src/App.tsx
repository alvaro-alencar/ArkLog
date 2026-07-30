import React, { useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { SettingsProvider } from './contexts/SettingsContext';
import AccessGate from './components/AccessGate';
import Layout from './components/Layout';
import Login from './views/Login';
import Dashboard from './views/Dashboard';
import ProjectEntry from './views/ProjectEntry';
import Reports from './views/Reports';
import Settings from './views/Settings';
import AccessAdmin from './views/AccessAdmin';
import Connections from './views/Connections';
import Flows from './views/Flows';
import TrelloCallback from './views/TrelloCallback';

const basename = import.meta.env.BASE_URL.replace(/\/$/, '') || '/';

const ProtectedRoute: React.FC<{ children: React.ReactNode; admin?: boolean }> = ({ children, admin = false }) => {
  const { user, access, isLoading } = useAuth();
  if (isLoading) return <div className="min-h-screen grid place-items-center bg-[#f5f7fb]"><div className="w-7 h-7 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!access || access.status === 'PENDING' || access.status === 'BLOCKED') return <AccessGate />;
  if (admin && !access.isAdmin) return <Navigate to="/" replace />;
  return <Layout>{children}</Layout>;
};

const ExpiredSessionListener: React.FC = () => {
  const navigate = useNavigate();
  useEffect(() => {
    const expired = () => navigate('/login', { replace: true });
    window.addEventListener('ark-auth-expired', expired);
    return () => window.removeEventListener('ark-auth-expired', expired);
  }, [navigate]);
  return null;
};

const App: React.FC = () => (
  <AuthProvider>
    <SettingsProvider>
      <BrowserRouter basename={basename}>
        <ExpiredSessionListener />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><Flows /></ProtectedRoute>} />
          <Route path="/flows" element={<ProtectedRoute><Flows /></ProtectedRoute>} />
          <Route path="/connections" element={<ProtectedRoute><Connections /></ProtectedRoute>} />
          <Route path="/trello/callback" element={<ProtectedRoute><TrelloCallback /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
          <Route path="/projects" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/projects/new" element={<ProtectedRoute><ProjectEntry /></ProtectedRoute>} />
          <Route path="/access" element={<ProtectedRoute admin><AccessAdmin /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </SettingsProvider>
  </AuthProvider>
);

export default App;
