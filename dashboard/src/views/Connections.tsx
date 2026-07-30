import React, { useEffect, useMemo, useState } from 'react';
import { Plug, RefreshCw, Search, Trash2 } from 'lucide-react';
import ProviderIcon from '../components/ProviderIcon';
import api from '../lib/api';

type Role = 'source' | 'destination';

type Connection = {
  id: number;
  provider: string;
  label: string;
  externalAccountName?: string;
  scopes: string[];
  capabilities: Role[];
  status: string;
  connectedAt: string;
};

type Provider = {
  id: string;
  name: string;
  description: string;
  capabilities: Role[];
  category: string;
  implemented: boolean;
  configured: boolean;
};

const providerOrder = ['github', 'slack', 'notion', 'clickup', 'trello'];
const allCategories = 'Todas';

const Connections: React.FC = () => {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [providers, setProviders] = useState<Record<string, Provider>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState(allCategories);

  const providerCards = useMemo(
    () => Object.values(providers)
      .sort((first, second) => {
        const firstIndex = providerOrder.indexOf(first.id);
        const secondIndex = providerOrder.indexOf(second.id);
        if (firstIndex >= 0 || secondIndex >= 0) {
          if (firstIndex < 0) return 1;
          if (secondIndex < 0) return -1;
          return firstIndex - secondIndex;
        }
        return first.name.localeCompare(second.name, 'pt-BR');
      })
      .filter((provider) => category === allCategories || provider.category === category)
      .filter((provider) => {
        const normalized = query.trim().toLocaleLowerCase('pt-BR');
        return !normalized || `${provider.name} ${provider.description} ${provider.category}`.toLocaleLowerCase('pt-BR').includes(normalized);
      }),
    [category, providers, query],
  );
  const categories = useMemo(
    () => [allCategories, ...Array.from(new Set(Object.values(providers).map((provider) => provider.category))).sort((a, b) => a.localeCompare(b, 'pt-BR'))],
    [providers],
  );
  const implementedCount = Object.values(providers).filter((provider) => provider.implemented).length;
  const roadmapCount = Object.values(providers).length - implementedCount;

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/connections');
      setConnections(response.data.connections || []);
      setProviders(response.data.providers || {});
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível carregar as conexões.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const connect = async (provider: string) => {
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

  return (
    <div className="space-y-7">
      <header>
        <span className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">Integrações</span>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Suas conexões</h1>
        <p className="mt-2 max-w-3xl text-slate-500">
          Cada conta é autorizada pelo próprio usuário e pode atuar como fonte, destino ou ambos, conforme as capacidades do serviço. Os segredos ficam criptografados e nunca chegam ao navegador.
        </p>
      </header>

      {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="font-bold text-slate-950">{Object.values(providers).length} conexões no ecossistema</p>
            <p className="mt-1 text-sm text-slate-500">{implementedCount} com adaptadores completos · {roadmapCount} priorizadas no roadmap</p>
          </div>
          <label className="relative block w-full lg:max-w-sm">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <span className="sr-only">Buscar conexão</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar por serviço ou categoria"
              className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 pl-11 pr-4 text-sm outline-none transition focus:border-violet-400 focus:bg-white focus:ring-4 focus:ring-violet-100"
            />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {categories.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setCategory(item)}
              className={`rounded-full px-3 py-1.5 text-xs font-bold transition ${category === item ? 'bg-slate-950 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
            >
              {item}
            </button>
          ))}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {providerCards.map((provider) => (
          <article key={provider.id} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-slate-950 text-white"><ProviderIcon provider={provider.id} size={24} /></div>
              <span className={`rounded-full px-3 py-1 text-xs font-bold ${provider.configured ? 'bg-emerald-100 text-emerald-700' : provider.implemented ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'}`}>
                {provider.configured ? 'Disponível' : provider.implemented ? 'Configuração pendente' : 'Em planejamento'}
              </span>
            </div>
            <p className="mt-5 text-xs font-bold uppercase tracking-[0.14em] text-violet-600">{provider.category}</p>
            <h2 className="mt-2 text-xl font-bold">{provider.name}</h2>
            <p className="mt-2 min-h-16 text-sm leading-relaxed text-slate-500">{provider.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {provider.capabilities.map((role) => <span key={role} className="rounded-full bg-violet-50 px-2.5 py-1 text-xs font-bold text-violet-700">{role === 'source' ? 'Fonte' : 'Destino'}</span>)}
            </div>
            <button
              type="button"
              disabled={!provider.configured || !provider.implemented || Boolean(busy)}
              onClick={() => void connect(provider.id)}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy === provider.id ? <RefreshCw size={17} className="animate-spin" /> : <Plug size={17} />}
              {provider.implemented ? `Conectar ${provider.name}` : 'Integração planejada'}
            </button>
          </article>
        ))}
      </section>

      {!loading && providerCards.length === 0 && (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
          Nenhuma conexão corresponde a essa busca.
        </div>
      )}

      <section className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-7 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">Contas conectadas</h2>
            <p className="mt-1 text-sm text-slate-500">Uma mesma conexão pode aparecer nas duas pontas do construtor quando o provedor permite leitura e escrita.</p>
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
          {connections.map((connection) => {
            const slackNeedsReconnect = connection.provider === 'slack' && !connection.scopes.includes('channels:history');
            return (
              <div key={connection.id} className="flex flex-col gap-3 rounded-2xl border border-slate-200 p-4 sm:flex-row sm:items-center">
                <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-100"><ProviderIcon provider={connection.provider} /></div>
                <div className="min-w-0 flex-1">
                  <p className="font-bold">{connection.label}</p>
                  <p className="truncate text-xs text-slate-500">{connection.capabilities.map((role) => role === 'source' ? 'Fonte' : 'Destino').join(' · ')}</p>
                  {slackNeedsReconnect && <p className="mt-1 text-xs font-semibold text-amber-700">Reconecte o Slack para também usá-lo como fonte de mensagens.</p>}
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
            );
          })}
        </div>
      </section>
    </div>
  );
};

export default Connections;
