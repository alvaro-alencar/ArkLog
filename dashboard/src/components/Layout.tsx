import React from 'react';
import { FileText, FolderGit2, LogOut, Plug, Settings, ShieldCheck, User, Workflow } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';
import ArkBrand from './ArkBrand';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, access, logout } = useAuth();
  const { t } = useSettings();
  const navigate = useNavigate();

  const links = [
    { to: '/', icon: <Workflow size={18} />, label: 'Fluxos' },
    { to: '/connections', icon: <Plug size={18} />, label: 'Conexões' },
    { to: '/reports', icon: <FileText size={18} />, label: t.nav.reports },
    { to: '/settings', icon: <Settings size={18} />, label: t.nav.settings },
    ...(access?.isAdmin ? [
      { to: '/projects', icon: <FolderGit2 size={18} />, label: 'Projetos legados' },
      { to: '/access', icon: <ShieldCheck size={18} />, label: 'Acessos' },
    ] : []),
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-[#f5f7fb] text-slate-950 lg:flex">
      <aside className="lg:w-64 lg:fixed lg:inset-y-0 bg-white border-b lg:border-b-0 lg:border-r border-slate-200 z-20">
        <div className="px-5 py-4 flex lg:block items-center justify-between">
          <a href="https://www.arksystem.net" aria-label="ArkSystem"><ArkBrand compact /></a>
          <div className="lg:hidden text-xs font-semibold rounded-full bg-violet-100 text-violet-700 px-3 py-1">{access?.status}</div>
        </div>
        <nav className="px-3 pb-3 lg:pb-0 flex lg:block overflow-x-auto gap-1 lg:space-y-1">
          {links.map(({ to, icon, label }) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `shrink-0 flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-semibold ${isActive ? 'bg-slate-950 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>{icon}{label}</NavLink>)}
        </nav>
        <div className="hidden lg:block absolute bottom-0 left-0 right-0 p-4 border-t border-slate-200">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-9 h-9 rounded-full bg-slate-100 grid place-items-center"><User size={17} /></div>
            <div className="min-w-0 flex-1"><p className="text-sm font-semibold truncate">{user?.name}</p><p className="text-xs text-slate-500 truncate">{user?.email}</p></div>
          </div>
          <button onClick={handleLogout} className="mt-2 w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold text-slate-500 hover:bg-red-50 hover:text-red-700"><LogOut size={17} /> Sair</button>
        </div>
      </aside>
      <main className="lg:ml-64 flex-1 p-4 sm:p-7 lg:p-9"><div className="max-w-6xl mx-auto">{children}</div></main>
    </div>
  );
};

export default Layout;
