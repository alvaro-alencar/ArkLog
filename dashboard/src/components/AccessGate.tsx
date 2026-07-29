import React from 'react';
import { Clock3, LockKeyhole, LogOut, ShieldAlert } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const AccessGate: React.FC = () => {
  const { access, user, logout, refreshAccess } = useAuth();
  const blocked = access?.status === 'BLOCKED';

  return (
    <div className="min-h-screen bg-[#f5f7fb] flex items-center justify-center px-4">
      <div className="w-full max-w-xl bg-white border border-slate-200 rounded-[28px] p-8 sm:p-10 text-center shadow-xl shadow-slate-200/60">
        <div className={`mx-auto w-16 h-16 rounded-2xl flex items-center justify-center ${blocked ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
          {blocked ? <ShieldAlert size={30} /> : <Clock3 size={30} />}
        </div>
        <h1 className="text-3xl font-bold mt-6">{blocked ? 'Acesso bloqueado' : 'Cadastro recebido'}</h1>
        <p className="text-slate-600 mt-4 leading-relaxed">
          {blocked
            ? access?.blockedReason || 'Esta conta não está autorizada a usar o ArkLog.'
            : `A conta ${user?.email || ''} existe, mas ainda não recebeu cota de relatórios. Isso protege a chave privada da OpenRouter contra consumo não autorizado.`}
        </p>
        {!blocked && (
          <div className="mt-6 flex items-center gap-3 text-left rounded-2xl bg-slate-50 border border-slate-200 p-4">
            <LockKeyhole className="text-violet-600 shrink-0" />
            <p className="text-sm text-slate-600">Quando o teste for liberado, esta conta receberá exatamente um relatório demonstrativo.</p>
          </div>
        )}
        <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
          {!blocked && <button onClick={() => refreshAccess()} className="rounded-xl bg-slate-950 text-white px-5 py-3 font-semibold">Verificar liberação</button>}
          <button onClick={() => logout()} className="rounded-xl border border-slate-300 px-5 py-3 font-semibold flex items-center justify-center gap-2"><LogOut size={18} /> Sair</button>
        </div>
      </div>
    </div>
  );
};

export default AccessGate;
