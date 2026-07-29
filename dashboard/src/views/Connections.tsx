import React, { useEffect, useState } from 'react';
import { GitBranch, MessageSquare, Plug, RefreshCw, Trash2 } from 'lucide-react';
import api from '../lib/api';

type Connection = {
  id: number;
  provider: 'github' | 'slack';
  label: string;
  externalAccountName?: string;
  scopes: string[];
  status: string;
  connectedAt: string;
};

type Providers = Record<'github' | 'slack', { configured: boolean }>;

const Connections: React.FC = () => {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [providers, setProviders] = useState<Providers>({
    github: { configured: false },
    slack: { configured: false },
  });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/connections');
      setConnections(response.data.connections || []);
      setProviders(response.data.providers);
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível carregar as conexões.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const connect = async (provider: 'github' | 'slack') => {
    setBusy(provider);
    setError('');
    try {
      const response = await api.get(`/connections/${provider}/start`);
      window.location.assign(response.data.authorizationUrl);
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || `Não foi possível conectar ${provider}.`);
      setBusy('');
    }
  };

  const disconnect = async (connection: Connection) => {
    if (!window.confirm(`Desconectar ${connection.label}?`)) return;
    setBusy(String(connection.id));
    setError('');
    try {
      await api.delete(`/connections/${connection.id}`);
      await load();
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível desconectar esta conta.');
    } finally {
      setBusy('');
    }
  };

  const cards = [
    {
      provider: 'github' as const,
      icon: <GitBranch size={24} />,
      title: 'GitHub',
      text: 'Fonte inicial para commits, pull requests, issues, CI e releases. A autorização pertence à sua conta.',
    },
    {
      provider: 'slack' as const,
      icon: <MessageSquare size={24} />,
      title: 'Slack',
      text: 'Destino inicial para publicar o relatório em um canal escolhido do seu workspace.',
    },
  ];

  return (
    <div className="space-y-7">
      <header>
        <span className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">Integrações</span>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Suas conexões</h1>
        <p className="mt-2 max-w-3xl text-slate-500">
          Cada conta autoriza apenas os próprios serviços. O ArkLog não usa um token administrativo escondido para ler seus dados.
        </p>
      </header>

      {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <section className="grid gap-4 md:grid-cols-2">
        {cards.map((card) => {
          const configured = providers[card.provider]?.configured;
          return (
            <article key={card.provider} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="grid h-12 w-12 place-items-center rounded-2xl bg-slate-950 text-white">{card.icon}</div>
                <span className={`rounded-full px-3 py-1 text-xs font-bold ${configured ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'}`}>
                  {configured ? 'Disponível' : 'Aguardando configuração'}
                </span>
              </div>
              <h2 className="mt-5 text-xl font-bold">{card.title}</h2>
              <p className="mt-2 min-h-16 text-sm leading-relaxed text-slate-500">{card.text}</p>
              <button
                type="button"
                disabled={!configured || Boolean(busy)}
                onClick={() => connect(card.provider)}
                className="mt-5 inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {busy === card.provider ? <RefreshCw size={17} className="animate-spin" /> : <Plug size={17} />}
                Conectar {card.title}
              </button>
            </article>
          );
        })}
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-7 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">Contas conectadas</h2>
            <p className="mt-1 text-sm text-slate-500">Os tokens ficam criptografados e nunca são enviados ao navegador.</p>
          </div>
          <button onClick={() => void load()} className="rounded-xl border border-slate-200 p-2.5 text-slate-500 hover:bg-slate-50" aria-label="Atualizar">
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>

        <div className="mt-5 space-y-3">
          {!loading && connections.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
              Nenhuma conexão ainda. Conecte uma fonte e um destino para montar o primeiro fluxo.
            </div>
          )}
          {connections.map((connection) => (
            <div key={connection.id} className="flex flex-col gap-3 rounded-2xl border border-slate-200 p-4 sm:flex-row sm:items-center">
              <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-100">
                {connection.provider === 'github' ? <GitBranch size={20} /> : <MessageSquare size={20} />}
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-bold">{connection.label}</p>
                <p className="truncate text-xs text-slate-500">{connection.scopes.join(' · ') || 'Escopos fornecidos pelo provedor'}</p>
              </div>
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">{connection.status}</span>
              <button
                type="button"
                disabled={busy === String(connection.id)}
                onClick={() => void disconnect(connection)}
                className="inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                <Trash2 size={16} /> Desconectar
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Connections;
