import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, FileText, Settings, LogOut, User } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth();
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
          <h1 className="text-2xl font-bold tracking-tighter">ArkLog</h1>
        </div>
        
        <nav className="flex-1 px-4 space-y-1">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive ? 'bg-white text-black' : 'text-gray-400 hover:text-white hover:bg-[#0a0a0a]'
              }`
            }
          >
            <LayoutDashboard size={18} />
            Dashboard
          </NavLink>
          <NavLink
            to="/reports"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive ? 'bg-white text-black' : 'text-gray-400 hover:text-white hover:bg-[#0a0a0a]'
              }`
            }
          >
            <FileText size={18} />
            All Reports
          </NavLink>
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
            Logout
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
