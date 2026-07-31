import React, { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Clipboard,
  Clock3,
  Download,
  FileText,
  Filter,
  Layers3,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  Workflow,
} from 'lucide-react';
import ProviderIcon from '../components/ProviderIcon';
import api from '../lib/api';

type Publication = {
  platform: string;
  target_id: string;
  external_id?: string | null;
  status: string;
  error_message?: string | null;
  published_at?: string | null;
};

type ReportSummary = {
  id: number;
  project_id?: number | null;
  flow_id?: number | null;
  project_name: string;
  owner_kind: 'flow' | 'project';
  source_provider?: string | null;
  destination_provider?: string | null;
  trigger: string;
  status: string;
  summary: string;
  item_count: number;
  commit_count: number;
  generated_at: string;
};

type ReportDetail = ReportSummary & {
  content: string;
  publications: Publication[];
};

type Flow = { id: number; name: string };
type Project = { id: number; name: string };

type StatusStyle = { label: string; className: string; icon: React.ReactNode };

const statusStyle = (status: string): StatusStyle => {
  if (status === 'published') {
    return {
      label: 'Publicado',
      className: 'bg-emerald-100 text-emerald-700',
      icon: <CheckCircle2 size={14} />,
    };
  }
  if (status === 'publication_failed') {
    return {
      label: 'Publicação falhou',
      className: 'bg-red-100 text-red-700',
      icon: <AlertCircle size={14} />,
    };
  }
  if (status === 'publication_pending') {
    return {
      label: 'Aguardando publicação',
      className: 'bg-amber-100 text-amber-800',
      icon: <Clock3 size={14} />,
    };
  }
  return {
    label: status || 'Pendente',
    className: 'bg-slate-100 text-slate-600',
    icon: <Clock3 size={14} />,
  };
};

const triggerLabel = (trigger: string) => ({
  manual_flow: 'Execução manual',
  instant: 'Relatório instantâneo',
  daily_scheduled: 'Agendamento diário',
  weekly_scheduled: 'Agendamento semanal',
  webhook: 'Webhook',
}[trigger] || trigger);

const downloadMarkdown = (report: ReportDetail) => {
  const blob = new Blob([report.content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `arklog-relatorio-${report.id}.md`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
};

const ReportCard: React.FC<{
  report: ReportSummary;
  onMessage: (message: string) => void;
  onRefresh: () => Promise<void> | void;
}> = ({ report, onMessage, onRefresh }) => {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState('');
  const style = statusStyle(report.status);

  const loadDetail = async () => {
    const response = await api.get(`/reports/${report.id}`);
    setDetail(response.data);
  };

  const expand = async () => {
    if (!expanded && !detail) {
      setLoading(true);
      setError('');
      try {
        await loadDetail();
      } catch (caught: any) {
        setError(caught?.response?.data?.detail || 'Não foi possível abrir este relatório.');
      } finally {
        setLoading(false);
      }
    }
    setExpanded((value) => !value);
  };

  const copy = async () => {
    if (!detail) return;
    try {
      await navigator.clipboard.writeText(detail.content);
      onMessage('Relatório copiado para a área de transferência.');
    } catch {
      onMessage('O navegador não permitiu copiar automaticamente.');
    }
  };

  const retryPublication = async () => {
    if (!detail) return;
    setRetrying(true);
    setError('');
    try {
      const response = await api.post(`/deliveries/reports/${detail.id}/retry`);
      await loadDetail();
      await onRefresh();
      const provider = response.data?.publication?.provider || detail.destination_provider || 'destino';
      onMessage(`Relatório republicado em ${provider}, sem nova geração de IA e sem consumo de cota.`);
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível republicar. O relatório continua salvo e nenhuma cota foi consumida.');
      try {
        await loadDetail();
        await onRefresh();
      } catch {
        // Preserve the original publication error when refreshing also fails.
      }
    } finally {
      setRetrying(false);
    }
  };

  const retryable = Boolean(
    detail?.flow_id
    && detail.publications.some((publication) => publication.status === 'failed'),
  );

  return (
    <article className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
      <button type="button" onClick={() => void expand()} className="w-full p-5 text-left sm:p-6">
        <div className="flex items-start gap-4">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-violet-100 text-violet-700">
            <FileText size={21} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${style.className}`}>
                {style.icon}{style.label}
              </span>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                {triggerLabel(report.trigger)}
              </span>
            </div>
            <h2 className="mt-3 truncate text-lg font-bold text-slate-950">{report.project_name}</h2>
            <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-slate-500">
              {report.summary || 'Relatório gerado sem resumo separado.'}
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1.5"><Clock3 size={14} />{new Date(report.generated_at).toLocaleString('pt-BR')}</span>
              <span className="inline-flex items-center gap-1.5"><Layers3 size={14} />{report.item_count} item(ns) processado(s)</span>
              {report.source_provider && (
                <span className="inline-flex items-center gap-1.5"><ProviderIcon provider={report.source_provider} size={14} />{report.source_provider}</span>
              )}
              {report.destination_provider && (
                <span className="inline-flex items-center gap-1.5"><Send size={14} />{report.destination_provider}</span>
              )}
            </div>
          </div>
          <span className="mt-1 text-slate-400">{expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}</span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-200 bg-slate-50 p-5 sm:p-6">
          {loading && <div className="flex justify-center py-8"><RefreshCw className="animate-spin text-violet-600" /></div>}
          {error && <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
          {detail && (
            <div className="space-y-5">
              <div className="flex flex-wrap justify-end gap-2">
                {retryable && (
                  <button type="button" disabled={retrying} onClick={() => void retryPublication()} className="inline-flex items-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-bold text-amber-900 hover:bg-amber-100 disabled:opacity-50">
                    {retrying ? <RefreshCw size={16} className="animate-spin" /> : <RotateCcw size={16} />} Republicar sem gerar novamente
                  </button>
                )}
                <button type="button" onClick={() => void copy()} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-violet-300 hover:text-violet-700">
                  <Clipboard size={16} /> Copiar
                </button>
                <button type="button" onClick={() => downloadMarkdown(detail)} className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-700">
                  <Download size={16} /> Baixar Markdown
                </button>
              </div>

              <div className="whitespace-pre-wrap rounded-2xl border border-slate-200 bg-white p-5 text-sm leading-7 text-slate-700">
                {detail.content}
              </div>

              <section>
                <h3 className="text-sm font-bold text-slate-950">Publicações</h3>
                <div className="mt-3 space-y-2">
                  {detail.publications.length === 0 && <p className="text-sm text-slate-500">Este relatório não possui publicação externa registrada.</p>}
                  {detail.publications.map((publication, index) => (
                    <div key={`${publication.platform}-${publication.target_id}-${index}`} className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center">
                      <div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-100"><ProviderIcon provider={publication.platform} size={18} /></div>
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold capitalize">{publication.platform}</p>
                        <p className="truncate text-xs text-slate-500">Destino {publication.target_id}</p>
                        {publication.error_message && <p className="mt-1 text-xs font-semibold text-red-700">{publication.error_message}</p>}
                      </div>
                      <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${publication.status === 'success' ? 'bg-emerald-100 text-emerald-700' : publication.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-800'}`}>
                        {publication.status === 'success' ? 'Enviado' : publication.status === 'failed' ? 'Falhou' : 'Pendente'}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          )}
        </div>
      )}
    </article>
  );
};

const Reports: React.FC = () => {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [flows, setFlows] = useState<Flow[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [ownerKind, setOwnerKind] = useState<'all' | 'flow' | 'project'>('all');
  const [ownerId, setOwnerId] = useState('');
  const [status, setStatus] = useState('');
  const [query, setQuery] = useState('');
  const [appliedQuery, setAppliedQuery] = useState('');
  const [page, setPage] = useState(0);
  const limit = 10;

  const owners = useMemo(() => ownerKind === 'flow' ? flows : ownerKind === 'project' ? projects : [], [flows, ownerKind, projects]);

  useEffect(() => {
    Promise.all([api.get('/flows'), api.get('/projects')])
      .then(([flowResponse, projectResponse]) => {
        setFlows((flowResponse.data.flows || []).map((item: any) => ({ id: item.id, name: item.name })));
        setProjects(projectResponse.data.projects || []);
      })
      .catch(() => {
        setFlows([]);
        setProjects([]);
      });
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params: Record<string, string | number> = { limit, offset: page * limit };
      if (ownerKind === 'flow' && ownerId) params.flow_id = Number(ownerId);
      if (ownerKind === 'project' && ownerId) params.project_id = Number(ownerId);
      if (status) params.status = status;
      if (appliedQuery) params.query = appliedQuery;
      const response = await api.get('/reports', { params });
      setReports(response.data.reports || []);
      setTotal(response.data.total || 0);
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível carregar os relatórios.');
    } finally {
      setLoading(false);
    }
  }, [appliedQuery, ownerId, ownerKind, page, status]);

  useEffect(() => { void load(); }, [load]);

  const applySearch = (event: FormEvent) => {
    event.preventDefault();
    setPage(0);
    setAppliedQuery(query.trim());
  };

  const changeOwnerKind = (value: 'all' | 'flow' | 'project') => {
    setOwnerKind(value);
    setOwnerId('');
    setPage(0);
  };

  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-7">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">Memória operacional</span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Relatórios</h1>
          <p className="mt-2 max-w-3xl text-slate-500">Consulte o conteúdo gerado, acompanhe a publicação e leve o resultado em Markdown para qualquer outro lugar.</p>
        </div>
        <button type="button" onClick={() => void load()} className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-700 hover:border-violet-300 hover:text-violet-700">
          <RefreshCw size={17} className={loading ? 'animate-spin' : ''} /> Atualizar
        </button>
      </header>

      {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div>}
      {message && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800">{message}</div>}

      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <form onSubmit={applySearch} className="grid gap-3 lg:grid-cols-[1.4fr_0.8fr_1fr_auto]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <span className="sr-only">Buscar nos relatórios</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar no resumo ou conteúdo" className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 pl-11 pr-4 text-sm outline-none focus:border-violet-400 focus:bg-white focus:ring-4 focus:ring-violet-100" />
          </label>
          <select value={ownerKind} onChange={(event) => changeOwnerKind(event.target.value as 'all' | 'flow' | 'project')} className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700">
            <option value="all">Todos os relatórios</option>
            <option value="flow">Por fluxo</option>
            <option value="project">Projetos legados</option>
          </select>
          {ownerKind === 'all' ? (
            <div className="hidden lg:block" />
          ) : (
            <select value={ownerId} onChange={(event) => { setOwnerId(event.target.value); setPage(0); }} className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700">
              <option value="">Todos</option>
              {owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.name}</option>)}
            </select>
          )}
          <button className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 text-sm font-bold text-white hover:bg-violet-700"><Filter size={17} /> Aplicar</button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            ['', 'Todos'],
            ['published', 'Publicados'],
            ['publication_pending', 'Pendentes'],
            ['publication_failed', 'Com falha'],
          ].map(([value, label]) => (
            <button key={value} type="button" onClick={() => { setStatus(value); setPage(0); }} className={`rounded-full px-3 py-1.5 text-xs font-bold ${status === value ? 'bg-violet-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>{label}</button>
          ))}
        </div>
      </section>

      <div className="flex items-center justify-between text-sm text-slate-500">
        <span>{total} relatório(s) encontrado(s)</span>
        <span>Página {page + 1} de {totalPages}</span>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><RefreshCw className="animate-spin text-violet-600" size={28} /></div>
      ) : reports.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <Workflow className="mx-auto text-slate-300" size={38} />
          <h2 className="mt-4 text-lg font-bold">Nenhum relatório neste recorte</h2>
          <p className="mt-2 text-sm text-slate-500">Execute um fluxo ou ajuste os filtros. A memória está limpa, não quebrada.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((report) => <ReportCard key={report.id} report={report} onMessage={setMessage} onRefresh={load} />)}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button type="button" disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-40"><ChevronLeft size={17} /> Anterior</button>
          <button type="button" disabled={page + 1 >= totalPages} onClick={() => setPage((value) => value + 1)} className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">Próxima <ChevronRight size={17} /></button>
        </div>
      )}
    </div>
  );
};

export default Reports;
