import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, FileText, Settings, LogOut, User } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth();
  const { t } = useSettings();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex min-h-screen bg-black text-foreground">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border flex flex-col fixed h-full bg-black">
        <div className="p-6">
          <img src="/logo_arklog.png" alt="ArkLog" className="h-20 w-auto" />
        </div>
        
        <nav className="flex-1 px-4 space-y-1">
          {[
            { to: '/', icon: <LayoutDashboard size={18} />, label: t.nav.dashboard, exact: true },
            { to: '/reports', icon: <FileText size={18} />, label: t.nav.reports },
            { to: '/settings', icon: <Settings size={18} />, label: t.nav.settings },
          ].map(({ to, icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive ? 'bg-white text-black' : 'text-gray-400 hover:text-white hover:bg-[#0a0a0a]'
                }`
              }
            >
              {icon}
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-border space-y-4">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center overflow-hidden border border-border">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt={user.username} />
              ) : (
                <User size={16} />
              )}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-sm font-medium truncate">{user?.username}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-md text-sm font-medium text-gray-400 hover:text-red-400 hover:bg-red-900/10 transition-colors"
          >
            <LogOut size={18} />
            {t.nav.logout}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 flex-1 p-8">
        <div className="max-w-5xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
