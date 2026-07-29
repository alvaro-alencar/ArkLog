import React, { FormEvent, useEffect, useMemo, useState } from 'react';
import { ArrowRight, GitBranch, MessageSquare, Play, Plus, RefreshCw, Trash2 } from 'lucide-react';
import api from '../lib/api';

type Connection = {
  id: number;
  provider: 'github' | 'slack';
  label: string;
  status: string;
};

type Resource = {
  id: string;
  name: string;
  label: string;
  private?: boolean;
};

type Flow = {
  id: number;
  name: string;
  status: string;
  sourceConnectionId: number;
  destinationConnectionId: number;
  sourceProvider: string;
  sourceLabel: string;
  destinationProvider: string;
  destinationLabel: string;
  sourceConfig: { repository?: string };
  destinationConfig: { channel?: string; channelLabel?: string };
  reportConfig: { style?: string; instructions?: string; windowHours?: number };
};

const emptyForm = {
  name: '',
  sourceConnectionId: '',
  destinationConnectionId: '',
  repository: '',
  channel: '',
  channelLabel: '',
  reportStyle: 'misto',
  instructions: '',
  windowHours: '168',
};

const Flows: React.FC = () => {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [flows, setFlows] = useState<Flow[]>([]);
  const [repositories, setRepositories] = useState<Resource[]>([]);
  const [channels, setChannels] = useState<Resource[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [showBuilder, setShowBuilder] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const githubConnections = useMemo(() => connections.filter((item) => item.provider === 'github'), [connections]);
  const slackConnections = useMemo(() => connections.filter((item) => item.provider === 'slack'), [connections]);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [connectionsResponse, flowsResponse] = await Promise.all([
        api.get('/connections'),
        api.get('/flows'),
      ]);
      setConnections(connectionsResponse.data.connections || []);
      setFlows(flowsResponse.data.flows || []);
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível carregar os fluxos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const loadResources = async (connectionId: string, kind: 'source' | 'destination') => {
    if (!connectionId) return;
    setBusy(`${kind}-resources`);
    setError('');
    try {
      const response = await api.get(`/connections/${connectionId}/resources`);
      if (kind === 'source') setRepositories(response.data.resources || []);
      else setChannels(response.data.resources || []);
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível carregar os recursos desta conexão.');
    } finally {
      setBusy('');
    }
  };

  const changeSource = (value: string) => {
    setForm((current) => ({ ...current, sourceConnectionId: value, repository: '' }));
    setRepositories([]);
    void loadResources(value, 'source');
  };

  const changeDestination = (value: string) => {
    setForm((current) => ({ ...current, destinationConnectionId: value, channel: '', channelLabel: '' }));
    setChannels([]);
    void loadResources(value, 'destination');
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy('create');
    setError('');
    setMessage('');
    try {
      await api.post('/flows', {
        name: form.name,
        source_connection_id: Number(form.sourceConnectionId),
        destination_connection_id: Number(form.destinationConnectionId),
        repository: form.repository,
        channel: form.channel,
        channel_label: form.channelLabel,
        report_style: form.reportStyle,
        instructions: form.instructions,
        window_hours: Number(form.windowHours),
      });
      setForm(emptyForm);
      setRepositories([]);
      setChannels([]);
      setShowBuilder(false);
      setMessage('Fluxo criado. A primeira execução só acontece quando você apertar Gerar relatório.');
      await load();
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível criar o fluxo.');
    } finally {
      setBusy('');
    }
  };

  const execute = async (flow: Flow) => {
    setBusy(`run-${flow.id}`);
    setError('');
    setMessage('');
    try {
      const response = await api.post(
        `/flows/${flow.id}/execute`,
        {},
        { headers: { 'Idempotency-Key': crypto.randomUUID() } },
      );
      setMessage(`Relatório ${response.data.reportId} gerado e publicado no Slack.`);
      await load();
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'O fluxo falhou. A cota não foi consumida.');
    } finally {
      setBusy('');
    }
  };

  const archive = async (flow: Flow) => {
    if (!window.confirm(`Arquivar o fluxo ${flow.name}?`)) return;
    setBusy(`delete-${flow.id}`);
    setError('');
    try {
      await api.delete(`/flows/${flow.id}`);
      await load();
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível arquivar o fluxo.');
    } finally {
      setBusy('');
    }
  };

  const noConnections = githubConnections.length === 0 || slackConnections.length === 0;

  return (
    <div className="space-y-7">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">Automação de relatórios</span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Fluxos</h1>
          <p className="mt-2 max-w-3xl text-slate-500">
            Escolha uma fonte, deixe a IA construir o relatório e publique no destino conectado. Nesta primeira etapa: GitHub → Slack.
          </p>
        </div>
        <button
          type="button"
          disabled={noConnections}
          onClick={() => setShowBuilder((value) => !value)}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-bold text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Plus size={18} /> Novo fluxo
        </button>
      </header>

      {noConnections && !loading && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
          Conecte pelo menos uma conta GitHub e um workspace Slack na área <strong>Conexões</strong> antes de criar o fluxo.
        </div>
      )}
      {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div>}
      {message && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800">{message}</div>}

      {showBuilder && (
        <form onSubmit={submit} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-violet-100 text-violet-700"><Plus size={20} /></div>
            <div><h2 className="text-xl font-bold">Montar fluxo</h2><p className="text-sm text-slate-500">As duas credenciais pertencem à sua conta Ark.</p></div>
          </div>

          <div className="mt-6 grid gap-5 md:grid-cols-2">
            <label className="text-sm font-semibold md:col-span-2">Nome do fluxo
              <input required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Relatório semanal do Smart-EAD" className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-violet-500" />
            </label>

            <div className="rounded-2xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 font-bold"><GitBranch size={19} /> Fonte GitHub</div>
              <label className="mt-4 block text-sm font-semibold">Conta conectada
                <select required value={form.sourceConnectionId} onChange={(event) => changeSource(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3">
                  <option value="">Escolha a conta</option>
                  {githubConnections.map((connection) => <option key={connection.id} value={connection.id}>{connection.label}</option>)}
                </select>
              </label>
              <label className="mt-4 block text-sm font-semibold">Repositório
                <select required disabled={!form.sourceConnectionId || busy === 'source-resources'} value={form.repository} onChange={(event) => setForm({ ...form, repository: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3 disabled:bg-slate-100">
                  <option value="">{busy === 'source-resources' ? 'Carregando...' : 'Escolha o repositório'}</option>
                  {repositories.map((resource) => <option key={resource.id} value={resource.name}>{resource.label}{resource.private ? ' · privado' : ''}</option>)}
                </select>
              </label>
            </div>

            <div className="rounded-2xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 font-bold"><MessageSquare size={19} /> Destino Slack</div>
              <label className="mt-4 block text-sm font-semibold">Workspace conectado
                <select required value={form.destinationConnectionId} onChange={(event) => changeDestination(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3">
                  <option value="">Escolha o workspace</option>
                  {slackConnections.map((connection) => <option key={connection.id} value={connection.id}>{connection.label}</option>)}
                </select>
              </label>
              <label className="mt-4 block text-sm font-semibold">Canal
                <select required disabled={!form.destinationConnectionId || busy === 'destination-resources'} value={form.channel} onChange={(event) => {
                  const selected = channels.find((resource) => resource.id === event.target.value);
                  setForm({ ...form, channel: event.target.value, channelLabel: selected?.label || '' });
                }} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3 disabled:bg-slate-100">
                  <option value="">{busy === 'destination-resources' ? 'Carregando...' : 'Escolha o canal'}</option>
                  {channels.map((resource) => <option key={resource.id} value={resource.id}>{resource.label}</option>)}
                </select>
              </label>
            </div>

            <label className="text-sm font-semibold">Formato do relatório
              <select value={form.reportStyle} onChange={(event) => setForm({ ...form, reportStyle: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3">
                <option value="misto">Executivo + técnico</option>
                <option value="executivo">Executivo</option>
                <option value="tecnico">Técnico</option>
              </select>
            </label>
            <label className="text-sm font-semibold">Janela de coleta
              <select value={form.windowHours} onChange={(event) => setForm({ ...form, windowHours: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3">
                <option value="24">Últimas 24 horas</option>
                <option value="72">Últimos 3 dias</option>
                <option value="168">Últimos 7 dias</option>
                <option value="336">Últimos 14 dias</option>
                <option value="720">Últimos 30 dias</option>
              </select>
            </label>
            <label className="text-sm font-semibold md:col-span-2">Instruções para o relatório
              <textarea value={form.instructions} onChange={(event) => setForm({ ...form, instructions: event.target.value })} rows={4} placeholder="Ex.: não mencione quantidade de commits; destaque segurança, entregas e próximos passos." className="mt-2 w-full resize-y rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-violet-500" />
            </label>
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <button type="button" onClick={() => setShowBuilder(false)} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-500 hover:bg-slate-100">Cancelar</button>
            <button disabled={busy === 'create'} className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-bold text-white hover:bg-violet-700 disabled:opacity-50">
              {busy === 'create' ? <RefreshCw size={17} className="animate-spin" /> : <ArrowRight size={17} />} Criar fluxo
            </button>
          </div>
        </form>
      )}

      <section className="space-y-4">
        <div className="flex items-center justify-between"><h2 className="text-xl font-bold">Fluxos ativos</h2><button onClick={() => void load()} className="rounded-xl border border-slate-200 p-2.5 text-slate-500 hover:bg-white"><RefreshCw size={18} className={loading ? 'animate-spin' : ''} /></button></div>
        {!loading && flows.length === 0 && (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">Nenhum fluxo criado. Conecte as pontas e abra a primeira ponte.</div>
        )}
        {flows.map((flow) => (
          <article key={flow.id} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-center">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-3"><h3 className="truncate text-xl font-bold">{flow.name}</h3><span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-700">{flow.status}</span></div>
                <div className="mt-4 flex flex-col gap-3 text-sm text-slate-600 sm:flex-row sm:items-center">
                  <span className="inline-flex min-w-0 items-center gap-2 rounded-xl bg-slate-100 px-3 py-2"><GitBranch size={17} /><span className="truncate">{flow.sourceConfig.repository}</span></span>
                  <ArrowRight size={18} className="hidden shrink-0 sm:block" />
                  <span className="inline-flex min-w-0 items-center gap-2 rounded-xl bg-slate-100 px-3 py-2"><MessageSquare size={17} /><span className="truncate">{flow.destinationConfig.channelLabel || flow.destinationConfig.channel}</span></span>
                </div>
                <p className="mt-3 text-xs text-slate-500">{flow.reportConfig.style || 'misto'} · últimas {flow.reportConfig.windowHours || 168} horas</p>
              </div>
              <div className="flex gap-2">
                <button disabled={Boolean(busy)} onClick={() => void execute(flow)} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-violet-700 disabled:opacity-50">
                  {busy === `run-${flow.id}` ? <RefreshCw size={17} className="animate-spin" /> : <Play size={17} />} Gerar relatório
                </button>
                <button disabled={Boolean(busy)} onClick={() => void archive(flow)} className="rounded-xl p-2.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50" aria-label="Arquivar fluxo"><Trash2 size={18} /></button>
              </div>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
};

export default Flows;
