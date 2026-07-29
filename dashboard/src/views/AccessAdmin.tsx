import React, { useCallback, useEffect, useState } from 'react';
import { Ban, CheckCircle2, RefreshCw, TicketCheck } from 'lucide-react';
import api from '../lib/api';

interface AccessUser {
  localUserId: number;
  arkUserId?: string;
  name: string;
  email?: string;
  createdAt: string;
  access: {
    status: string;
    reportLimit: number;
    reportsUsed: number;
    remainingReports: number | null;
    isAdmin: boolean;
  };
}

const AccessAdmin: React.FC = () => {
  const [users, setUsers] = useState<AccessUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState<number | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    api.get('/access/admin/users')
      .then((response) => setUsers(response.data.users))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const act = async (user: AccessUser, action: 'grant-trial' | 'activate' | 'block') => {
    setWorking(user.localUserId);
    try {
      await api.post(`/access/admin/users/${user.localUserId}/${action}`);
      load();
    } finally {
      setWorking(null);
    }
  };

  return (
    <div className="space-y-7">
      <div className="flex justify-between items-center">
        <div><h1 className="text-3xl font-bold">Controle de acesso</h1><p className="text-slate-500 mt-1">Nenhum cadastro consome IA antes desta autorização.</p></div>
        <button onClick={load} className="p-2.5 rounded-xl border border-slate-300"><RefreshCw size={18} /></button>
      </div>
      {loading ? <p className="text-slate-500">Carregando...</p> : (
        <div className="space-y-3">
          {users.map((user) => (
            <div key={user.localUserId} className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col lg:flex-row lg:items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex gap-2 items-center"><strong className="truncate">{user.name || user.email}</strong><span className="text-xs px-2 py-1 rounded-full bg-slate-100">{user.access.status}</span>{user.access.isAdmin && <span className="text-xs px-2 py-1 rounded-full bg-violet-100 text-violet-700">ADMIN</span>}</div>
                <p className="text-sm text-slate-500 mt-1">{user.email}</p>
                <p className="text-xs text-slate-400 mt-1">Uso: {user.access.reportsUsed} / {user.access.reportLimit < 0 ? 'ilimitado' : user.access.reportLimit}</p>
              </div>
              {!user.access.isAdmin && <div className="flex flex-wrap gap-2">
                <button disabled={working === user.localUserId} onClick={() => act(user, 'grant-trial')} className="px-3 py-2 rounded-lg bg-amber-100 text-amber-800 text-sm font-semibold flex gap-2"><TicketCheck size={16} /> 1 teste</button>
                <button disabled={working === user.localUserId} onClick={() => act(user, 'activate')} className="px-3 py-2 rounded-lg bg-emerald-100 text-emerald-800 text-sm font-semibold flex gap-2"><CheckCircle2 size={16} /> Autorizar</button>
                <button disabled={working === user.localUserId} onClick={() => act(user, 'block')} className="px-3 py-2 rounded-lg bg-red-100 text-red-800 text-sm font-semibold flex gap-2"><Ban size={16} /> Bloquear</button>
              </div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AccessAdmin;
