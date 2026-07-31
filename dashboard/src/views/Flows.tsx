import React, { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Copy,
  History,
  Info,
  Pause,
  Pencil,
  Play,
  Plus,
  Power,
  RefreshCw,
  Save,
  Trash2,
  X,
} from 'lucide-react';
import ProviderIcon from '../components/ProviderIcon';
import api from '../lib/api';

type Role = 'source' | 'destination';

type Connection = {
  id: number;
  provider: string;
  label: string;
  status: string;
  capabilities: Role[];
};

type Resource = {
  id: string;
  name: string;
  label: string;
  type?: string;
  private?: boolean;
  available?: boolean;
  availabilityReason?: string;
  metadata?: Record<string, unknown>;
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
  sourceConfig: { resourceId?: string; resourceLabel?: string; resourceType?: string };
  destinationConfig: { resourceId?: string; resourceLabel?: string; resourceType?: string };
  reportConfig: { style?: string; instructions?: string; windowHours?: number };
};

type Preflight = {
  ready: boolean;
  message: string;
  checks: Array<{
    role: Role;
    provider: string;
    ready: boolean;
    resourceLabel: string;
    message: string;
  }>;
};

type Run = {
  id: string;
  status: string;
  trigger: string;
  reportId?: number | null;
  error?: string | null;
  createdAt: string;
  completedAt?: string | null;
};

type FlowForm = {
  name: string;
  sourceConnectionId: string;
  destinationConnectionId: string;
  sourceResourceId: string;
  sourceResourceLabel: string;
  sourceResourceType: string;
  destinationResourceId: string;
  destinationResourceLabel: string;
  destinationResourceType: string;
  reportStyle: string;
  instructions: string;
  windowHours: string;
};

type EditorState = { mode: 'create' } | { mode: 'edit'; flowId: number } | null;

const emptyForm: FlowForm = {
  name: '',
  sourceConnectionId: '',
  destinationConnectionId: '',
  sourceResourceId: '',
  sourceResourceLabel: '',
  sourceResourceType: '',
  destinationResourceId: '',
  destinationResourceLabel: '',
  destinationResourceType: '',
  reportStyle: 'misto',
  instructions: '',
  windowHours: '168',
};

const flowStatus = (status: string) => status === 'ACTIVE'
  ? 'bg-emerald-100 text-emerald-700'
  : 'bg-amber-100 text-amber-800';

const runStatus = (status: string) => {
  if (status === 'COMPLETED') return { label: 'Concluído', className: 'bg-emerald-100 text-emerald-700' };
  if (status === 'FAILED') return { label: 'Falhou', className: 'bg-red-100 text-red-700' };
  if (status === 'RESERVED') return { label: 'Em andamento', className: 'bg-amber-100 text-amber-800' };
  return { label: status, className: 'bg-slate-100 text-slate-600' };
};

const existingResource = (
  id: string,
  label: string,
  type: string,
): Resource[] => id ? [{ id, name: label, label: label || id, type, available: true }] : [];

const Flows: React.FC = () => {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [flows, setFlows] = useState<Flow[]>([]);
  const [sourceResources, setSourceResources] = useState<Resource[]>([]);
  const [destinationResources, setDestinationResources] = useState<Resource[]>([]);
  const [resourceBusy, setResourceBusy] = useState<Record<Role, boolean>>({ source: false, destination: false });
  const [preflights, setPreflights] = useState<Record<number, Preflight>>({});
  const [runs, setRuns] = useState<Record<number, Run[]>>({});
  const [openHistory, setOpenHistory] = useState<number | null>(null);
  const [form, setForm] = useState<FlowForm>(emptyForm);
  const [editor, setEditor] = useState<EditorState>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const sourceConnections = useMemo(
    () => connections.filter((item) => item.capabilities?.includes('source')),
    [connections],
  );
  const destinationConnections = useMemo(
    () => connections.filter((item) => item.capabilities?.includes('destination')),
    [connections],
  );
  const selectedSource = sourceConnections.find((item) => String(item.id) === form.sourceConnectionId);
  const selectedDestination = destinationConnections.find((item) => String(item.id) === form.destinationConnectionId);

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

  const loadResources = async (connectionId: string, role: Role) => {
    if (!connectionId) return;
    setResourceBusy((current) => ({ ...current, [role]: true }));
    setError('');
    try {
      const response = await api.get(`/connections/${connectionId}/resources`, { params: { role } });
      if (role === 'source') setSourceResources(response.data.resources || []);
      else setDestinationResources(response.data.resources || []);
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível carregar os recursos desta conexão.');
    } finally {
      setResourceBusy((current) => ({ ...current, [role]: false }));
    }
  };

  const changeConnection = (value: string, role: Role) => {
    if (role === 'source') {
      setForm((current) => ({ ...current, sourceConnectionId: value, sourceResourceId: '', sourceResourceLabel: '', sourceResourceType: '' }));
      setSourceResources([]);
    } else {
      setForm((current) => ({ ...current, destinationConnectionId: value, destinationResourceId: '', destinationResourceLabel: '', destinationResourceType: '' }));
      setDestinationResources([]);
    }
    void loadResources(value, role);
  };

  const chooseResource = (resourceId: string, role: Role) => {
    const resources = role === 'source' ? sourceResources : destinationResources;
    const selected = resources.find((resource) => resource.id === resourceId);
    if (role === 'source') {
      setForm((current) => ({
        ...current,
        sourceResourceId: resourceId,
        sourceResourceLabel: selected?.label || '',
        sourceResourceType: selected?.type || '',
      }));
    } else {
      setForm((current) => ({
        ...current,
        destinationResourceId: resourceId,
        destinationResourceLabel: selected?.label || '',
        destinationResourceType: selected?.type || '',
      }));
    }
  };

  const openCreate = () => {
    setForm(emptyForm);
    setSourceResources([]);
    setDestinationResources([]);
    setEditor({ mode: 'create' });
    setError('');
    setMessage('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const openEdit = (flow: Flow) => {
    const nextForm: FlowForm = {
      name: flow.name,
      sourceConnectionId: String(flow.sourceConnectionId),
      destinationConnectionId: String(flow.destinationConnectionId),
      sourceResourceId: flow.sourceConfig.resourceId || '',
      sourceResourceLabel: flow.sourceConfig.resourceLabel || '',
      sourceResourceType: flow.sourceConfig.resourceType || '',
      destinationResourceId: flow.destinationConfig.resourceId || '',
      destinationResourceLabel: flow.destinationConfig.resourceLabel || '',
      destinationResourceType: flow.destinationConfig.resourceType || '',
      reportStyle: flow.reportConfig.style || 'misto',
      instructions: flow.reportConfig.instructions || '',
      windowHours: String(flow.reportConfig.windowHours || 168),
    };
    setForm(nextForm);
    setSourceResources(existingResource(nextForm.sourceResourceId, nextForm.sourceResourceLabel, nextForm.sourceResourceType));
    setDestinationResources(existingResource(nextForm.destinationResourceId, nextForm.destinationResourceLabel, nextForm.destinationResourceType));
    setEditor({ mode: 'edit', flowId: flow.id });
    setError('');
    setMessage('');
    void Promise.all([
      loadResources(nextForm.sourceConnectionId, 'source'),
      loadResources(nextForm.destinationConnectionId, 'destination'),
    ]);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const closeEditor = () => {
    setEditor(null);
    setForm(emptyForm);
    setSourceResources([]);
    setDestinationResources([]);
  };

  const flowPayload = () => ({
    name: form.name,
    source_connection_id: Number(form.sourceConnectionId),
    destination_connection_id: Number(form.destinationConnectionId),
    source_resource_id: form.sourceResourceId,
    source_resource_label: form.sourceResourceLabel,
    source_resource_type: form.sourceResourceType,
    destination_resource_id: form.destinationResourceId,
    destination_resource_label: form.destinationResourceLabel,
    destination_resource_type: form.destinationResourceType,
    report_style: form.reportStyle,
    instructions: form.instructions,
    window_hours: Number(form.windowHours),
  });

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!editor) return;
    setBusy(editor.mode === 'edit' ? `edit-${editor.flowId}` : 'create');
    setError('');
    setMessage('');
    try {
      if (editor.mode === 'edit') {
        await api.put(`/operations/flows/${editor.flowId}/configuration`, flowPayload());
        setPreflights((current) => {
          const next = { ...current };
          delete next[editor.flowId];
          return next;
        });
        setMessage('Fluxo atualizado. Faça um novo pré-teste antes da próxima execução.');
      } else {
        await api.post('/flows', flowPayload());
        setMessage('Fluxo criado. Faça o pré-teste antes da primeira execução.');
      }
      closeEditor();
      await load();
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível salvar o fluxo.');
    } finally {
      setBusy('');
    }
  };

  const preflight = async (flow: Flow) => {
    setBusy(`test-${flow.id}`);
    setError('');
    setMessage('');
    try {
      const response = await api.post(`/operations/flows/${flow.id}/preflight`);
      setPreflights((current) => ({ ...current, [flow.id]: response.data }));
      if (response.data.ready) setMessage(`${flow.name}: fonte e destino estão prontos.`);
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível pré-testar este fluxo.');
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
      setMessage(`Relatório ${response.data.reportId} gerado e publicado em ${flow.destinationLabel}.`);
      await Promise.all([load(), loadRuns(flow, true)]);
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'O fluxo falhou. A cota não foi consumida.');
      await loadRuns(flow, true);
    } finally {
      setBusy('');
    }
  };

  const toggle = async (flow: Flow) => {
    const nextStatus = flow.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    setBusy(`toggle-${flow.id}`);
    setError('');
    try {
      await api.patch(`/operations/flows/${flow.id}`, { status: nextStatus });
      setMessage(nextStatus === 'ACTIVE' ? `${flow.name} reativado.` : `${flow.name} pausado.`);
      await load();
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível alterar o estado do fluxo.');
    } finally {
      setBusy('');
    }
  };

  const cloneFlow = async (flow: Flow) => {
    setBusy(`clone-${flow.id}`);
    setError('');
    setMessage('');
    try {
      const response = await api.post(`/operations/flows/${flow.id}/clone`);
      const cloned = response.data.flow as Flow;
      setMessage(`${cloned.name} criado como pausado. Edite as pontas e ative somente depois do pré-teste.`);
      await load();
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível duplicar o fluxo.');
    } finally {
      setBusy('');
    }
  };

  const loadRuns = async (flow: Flow, keepOpen = false) => {
    setBusy(`history-${flow.id}`);
    setError('');
    try {
      const response = await api.get(`/operations/flows/${flow.id}/runs`);
      setRuns((current) => ({ ...current, [flow.id]: response.data.runs || [] }));
      setOpenHistory((current) => keepOpen ? flow.id : current === flow.id ? null : flow.id);
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível carregar o histórico do fluxo.');
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
      if (editor?.mode === 'edit' && editor.flowId === flow.id) closeEditor();
      await load();
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível arquivar o fluxo.');
    } finally {
      setBusy('');
    }
  };

  const noConnections = sourceConnections.length === 0 || destinationConnections.length === 0;

  return (
    <div className="space-y-7">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">Automação de relatórios</span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Fluxos</h1>
          <p className="mt-2 max-w-3xl text-slate-500">Monte, teste, edite e duplique pontes entre qualquer fonte e destino compatíveis.</p>
        </div>
        <button type="button" disabled={noConnections} onClick={openCreate} className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-bold text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-40">
          <Plus size={18} /> Novo fluxo
        </button>
      </header>

      {noConnections && !loading && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">Conecte pelo menos um serviço com capacidade de <strong>fonte</strong> e outro com capacidade de <strong>destino</strong> na área Conexões.</div>
      )}
      {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div>}
      {message && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800">{message}</div>}

      {editor && (
        <form onSubmit={submit} className="rounded-3xl border border-violet-200 bg-white p-5 shadow-sm ring-4 ring-violet-50 sm:p-7">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-violet-100 text-violet-700">{editor.mode === 'edit' ? <Pencil size={20} /> : <Plus size={20} />}</div>
              <div><h2 className="text-xl font-bold">{editor.mode === 'edit' ? 'Editar fluxo' : 'Montar fluxo'}</h2><p className="text-sm text-slate-500">O ArkLog confirma as duas pontas diretamente nos provedores antes de salvar.</p></div>
            </div>
            <button type="button" onClick={closeEditor} className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Fechar editor"><X size={19} /></button>
          </div>

          <label className="mt-6 block text-sm font-semibold">Nome do fluxo
            <input required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Relatório semanal do produto" className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-violet-500" />
          </label>

          <div className="mt-5 grid gap-5 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 font-bold"><ProviderIcon provider={selectedSource?.provider || ''} size={19} /> Fonte</div>
              <label className="mt-4 block text-sm font-semibold">Conexão
                <select required value={form.sourceConnectionId} onChange={(event) => changeConnection(event.target.value, 'source')} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3">
                  <option value="">Escolha a conexão</option>
                  {sourceConnections.map((connection) => <option key={connection.id} value={connection.id}>{connection.label}</option>)}
                </select>
              </label>
              <label className="mt-4 block text-sm font-semibold">Origem
                <select required disabled={!form.sourceConnectionId || resourceBusy.source} value={form.sourceResourceId} onChange={(event) => chooseResource(event.target.value, 'source')} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3 disabled:bg-slate-100">
                  <option value="">{resourceBusy.source ? 'Carregando...' : 'Escolha a origem'}</option>
                  {sourceResources.map((resource) => <option key={resource.id} value={resource.id} disabled={resource.available === false}>{resource.label}{resource.private ? ' · privado' : ''}{resource.available === false ? ` · ${resource.availabilityReason || 'indisponível'}` : ''}</option>)}
                </select>
              </label>
              {selectedSource?.provider === 'slack' && <div className="mt-4 flex gap-2 rounded-xl bg-blue-50 p-3 text-xs leading-relaxed text-blue-900"><Info size={17} className="mt-0.5 shrink-0" /><span>Para ler mensagens, use <strong>/invite @ArkLog</strong> no canal e reconecte contas antigas que não tenham permissão de histórico.</span></div>}
            </div>

            <div className="rounded-2xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 font-bold"><ProviderIcon provider={selectedDestination?.provider || ''} size={19} /> Destino</div>
              <label className="mt-4 block text-sm font-semibold">Conexão
                <select required value={form.destinationConnectionId} onChange={(event) => changeConnection(event.target.value, 'destination')} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3">
                  <option value="">Escolha a conexão</option>
                  {destinationConnections.map((connection) => <option key={connection.id} value={connection.id}>{connection.label}</option>)}
                </select>
              </label>
              <label className="mt-4 block text-sm font-semibold">Destino
                <select required disabled={!form.destinationConnectionId || resourceBusy.destination} value={form.destinationResourceId} onChange={(event) => chooseResource(event.target.value, 'destination')} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3 disabled:bg-slate-100">
                  <option value="">{resourceBusy.destination ? 'Carregando...' : 'Escolha o destino'}</option>
                  {destinationResources.map((resource) => <option key={resource.id} value={resource.id} disabled={resource.available === false}>{resource.label}{resource.private ? ' · privado' : ''}{resource.available === false ? ` · ${resource.availabilityReason || 'indisponível'}` : ''}</option>)}
                </select>
              </label>
              {selectedDestination?.provider === 'slack' && <div className="mt-4 flex gap-2 rounded-xl bg-amber-50 p-3 text-xs leading-relaxed text-amber-900"><Info size={17} className="mt-0.5 shrink-0" /><span>Antes de salvar, abra o canal no Slack e use <strong>/invite @ArkLog</strong>. Canais sem o app ficam indisponíveis.</span></div>}
            </div>

            <label className="text-sm font-semibold">Formato do relatório
              <select value={form.reportStyle} onChange={(event) => setForm({ ...form, reportStyle: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3">
                <option value="misto">Executivo + técnico</option><option value="executivo">Executivo</option><option value="tecnico">Técnico</option>
              </select>
            </label>
            <label className="text-sm font-semibold">Janela de coleta
              <select value={form.windowHours} onChange={(event) => setForm({ ...form, windowHours: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3">
                <option value="24">Últimas 24 horas</option><option value="72">Últimos 3 dias</option><option value="168">Últimos 7 dias</option><option value="336">Últimos 14 dias</option><option value="720">Últimos 30 dias</option>
              </select>
            </label>
            <label className="text-sm font-semibold md:col-span-2">Instruções para o relatório
              <textarea value={form.instructions} onChange={(event) => setForm({ ...form, instructions: event.target.value })} rows={4} placeholder="Ex.: destaque entregas, riscos e próximos passos; não cite quantidade de eventos." className="mt-2 w-full resize-y rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-violet-500" />
            </label>
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <button type="button" onClick={closeEditor} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-500 hover:bg-slate-100">Cancelar</button>
            <button disabled={Boolean(busy) || resourceBusy.source || resourceBusy.destination} className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-bold text-white hover:bg-violet-700 disabled:opacity-50">
              {busy.startsWith('edit-') || busy === 'create' ? <RefreshCw size={17} className="animate-spin" /> : editor.mode === 'edit' ? <Save size={17} /> : <ArrowRight size={17} />}
              {editor.mode === 'edit' ? 'Salvar alterações' : 'Criar fluxo'}
            </button>
          </div>
        </form>
      )}

      <section className="space-y-4">
        <div className="flex items-center justify-between"><h2 className="text-xl font-bold">Fluxos</h2><button onClick={() => void load()} className="rounded-xl border border-slate-200 p-2.5 text-slate-500 hover:bg-white"><RefreshCw size={18} className={loading ? 'animate-spin' : ''} /></button></div>
        {!loading && flows.length === 0 && <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">Nenhum fluxo criado. Conecte as pontas e abra a primeira ponte.</div>}
        {flows.map((flow) => {
          const preflightResult = preflights[flow.id];
          const history = runs[flow.id] || [];
          return (
            <article key={flow.id} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <div className="flex flex-col gap-5">
                <div className="flex flex-col gap-5 lg:flex-row lg:items-center">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-3"><h3 className="truncate text-xl font-bold">{flow.name}</h3><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${flowStatus(flow.status)}`}>{flow.status === 'ACTIVE' ? 'ATIVO' : 'PAUSADO'}</span></div>
                    <div className="mt-4 flex flex-col gap-3 text-sm text-slate-600 sm:flex-row sm:items-center">
                      <span className="inline-flex min-w-0 items-center gap-2 rounded-xl bg-slate-100 px-3 py-2"><ProviderIcon provider={flow.sourceProvider} size={17} /><span className="truncate">{flow.sourceConfig.resourceLabel || flow.sourceConfig.resourceId}</span></span>
                      <ArrowRight size={18} className="hidden shrink-0 sm:block" />
                      <span className="inline-flex min-w-0 items-center gap-2 rounded-xl bg-slate-100 px-3 py-2"><ProviderIcon provider={flow.destinationProvider} size={17} /><span className="truncate">{flow.destinationConfig.resourceLabel || flow.destinationConfig.resourceId}</span></span>
                    </div>
                    <p className="mt-3 text-xs text-slate-500">{flow.sourceProvider} → {flow.destinationProvider} · {flow.reportConfig.style || 'misto'} · últimas {flow.reportConfig.windowHours || 168} horas</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button disabled={Boolean(busy)} onClick={() => openEdit(flow)} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-bold text-slate-700 hover:border-violet-300 hover:text-violet-700 disabled:opacity-50"><Pencil size={17} /> Editar</button>
                    <button disabled={Boolean(busy)} onClick={() => void cloneFlow(flow)} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-bold text-slate-700 hover:border-violet-300 hover:text-violet-700 disabled:opacity-50">{busy === `clone-${flow.id}` ? <RefreshCw size={17} className="animate-spin" /> : <Copy size={17} />} Duplicar</button>
                    <button disabled={Boolean(busy)} onClick={() => void preflight(flow)} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-bold text-slate-700 hover:border-violet-300 hover:text-violet-700 disabled:opacity-50">{busy === `test-${flow.id}` ? <RefreshCw size={17} className="animate-spin" /> : <Activity size={17} />} Pré-testar</button>
                    <button disabled={Boolean(busy)} onClick={() => void loadRuns(flow)} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-bold text-slate-700 hover:border-violet-300 hover:text-violet-700 disabled:opacity-50">{busy === `history-${flow.id}` ? <RefreshCw size={17} className="animate-spin" /> : <History size={17} />} Histórico</button>
                    <button disabled={Boolean(busy)} onClick={() => void toggle(flow)} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50">{flow.status === 'ACTIVE' ? <Pause size={17} /> : <Power size={17} />} {flow.status === 'ACTIVE' ? 'Pausar' : 'Ativar'}</button>
                    <button disabled={Boolean(busy) || flow.status !== 'ACTIVE'} onClick={() => void execute(flow)} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-violet-700 disabled:opacity-50">{busy === `run-${flow.id}` ? <RefreshCw size={17} className="animate-spin" /> : <Play size={17} />} Gerar relatório</button>
                    <button disabled={Boolean(busy)} onClick={() => void archive(flow)} className="rounded-xl p-2.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50" aria-label="Arquivar fluxo"><Trash2 size={18} /></button>
                  </div>
                </div>

                {preflightResult && <div className={`rounded-2xl border p-4 text-sm ${preflightResult.ready ? 'border-emerald-200 bg-emerald-50 text-emerald-950' : 'border-amber-200 bg-amber-50 text-amber-950'}`}><div className="flex items-center gap-2 font-bold">{preflightResult.ready ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}{preflightResult.message}</div><div className="mt-2 grid gap-2 sm:grid-cols-2">{preflightResult.checks.map((check) => <p key={check.role} className="text-xs"><strong>{check.role === 'source' ? 'Fonte' : 'Destino'}:</strong> {check.message}</p>)}</div></div>}

                {openHistory === flow.id && <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><h4 className="font-bold">Últimas execuções</h4><div className="mt-3 space-y-2">{history.length === 0 && <p className="text-sm text-slate-500">Este fluxo ainda não possui tentativas registradas.</p>}{history.map((run) => { const style = runStatus(run.status); return <div key={run.id} className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-white p-3 sm:flex-row sm:items-center"><Clock3 size={16} className="text-slate-400" /><div className="min-w-0 flex-1"><p className="text-sm font-semibold">{new Date(run.createdAt).toLocaleString('pt-BR')}</p>{run.error && <p className="mt-1 truncate text-xs text-red-700">{run.error}</p>}</div>{run.reportId && <a href="/arklog/reports" className="text-xs font-bold text-violet-700">Relatório #{run.reportId}</a>}<span className={`rounded-full px-2.5 py-1 text-xs font-bold ${style.className}`}>{style.label}</span></div>; })}</div></div>}
              </div>
            </article>
          );
        })}
      </section>
    </div>
  );
};

export default Flows;
