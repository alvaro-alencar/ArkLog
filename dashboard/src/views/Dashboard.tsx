import React, { useEffect, useState } from 'react';
import { Calendar, ExternalLink, GitBranch, Plus, ShieldCheck, Zap } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

interface Project { id: number; name: string; repo_full_name: string; description: string; created_at: string; }
const FULL_WINDOWS = [
  { value: 1, label: 'Última hora' }, { value: 6, label: 'Últimas 6 horas' },
  { value: 24, label: 'Últimas 24 horas' }, { value: 168, label: 'Últimos 7 dias' },
  { value: 720, label: 'Últimos 30 dias' }, { value: -1, label: 'Todo o histórico' },
];

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { access, refreshAccess } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [openProject, setOpenProject] = useState<number | null>(null);
  const [windowHours, setWindowHours] = useState(24);
  const [generating, setGenerating] = useState<number | null>(null);
  const [message, setMessage] = useState<{ projectId: number; text: string; error?: boolean } | null>(null);

  const windows = access?.status === 'TRIAL' ? FULL_WINDOWS.filter((item) => item.value > 0 && item.value <= 168) : FULL_WINDOWS;

  useEffect(() => {
    api.get('/projects').then((response) => setProjects(response.data.projects)).finally(() => setLoading(false));
  }, []);

  const generate = async (projectId: number) => {
    setGenerating(projectId);
    setMessage(null);
    try {
      const response = await api.post(`/projects/${projectId}/instant-report`, { window_hours: windowHours }, {
        headers: { 'Idempotency-Key': crypto.randomUUID() },
      });
      await refreshAccess();
      setMessage({ projectId, text: response.data.report_id ? 'Relatório concluído e salvo.' : 'Relatório processado.' });
      setOpenProject(null);
    } catch (caught: any) {
      await refreshAccess().catch(() => null);
      setMessage({ projectId, error: true, text: String(caught?.response?.data?.detail || 'Não foi possível gerar o relatório.') });
    } finally {
      setGenerating(null);
    }
  };

  return (
    <div className="space-y-7">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div><h1 className="text-3xl font-bold">Projetos</h1><p className="text-slate-500 mt-1">Relatórios gerados com cota e identidade verificadas no servidor.</p></div>
        <Link to="/new" className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 text-white px-4 py-3 font-semibold"><Plus size={18} /> Novo projeto</Link>
      </div>

      <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4 flex flex-col sm:flex-row sm:items-center gap-3">
        <ShieldCheck className="text-violet-700 shrink-0" />
        <div className="flex-1"><p className="font-semibold text-violet-950">Acesso {access?.status === 'TRIAL' ? 'de teste' : 'autorizado'}</p><p className="text-sm text-violet-800">Relatórios restantes: {access?.remainingReports === null ? 'sem limite para administração' : access?.remainingReports}</p></div>
      </div>

      {loading ? <div className="py-20 text-center text-slate-500">Carregando...</div> : projects.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-3xl p-12 text-center"><p className="text-slate-500">Nenhum projeto cadastrado.</p><Link to="/new" className="inline-block mt-5 font-semibold text-violet-700">Adicionar o primeiro</Link></div>
      ) : (
        <div className="grid md:grid-cols-2 gap-5">
          {projects.map((project) => (
            <article key={project.id} className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
              <div className="flex justify-between gap-4"><div><h2 className="text-xl font-bold">{project.name}</h2><p className="text-sm text-slate-500 flex items-center gap-2 mt-1"><GitBranch size={14} />{project.repo_full_name}</p></div><a href={`https://github.com/${project.repo_full_name}`} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-slate-900"><ExternalLink size={19} /></a></div>
              <p className="text-sm text-slate-600 mt-5 min-h-10">{project.description || 'Sem contexto adicional.'}</p>
              {openProject === project.id && <div className="mt-5 p-4 rounded-2xl bg-slate-50 border border-slate-200"><label className="text-xs font-bold uppercase tracking-wide text-slate-500">Período<select value={windowHours} onChange={(event) => setWindowHours(Number(event.target.value))} className="mt-2 block w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5 text-sm text-slate-950">{windows.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label><button disabled={generating === project.id || access?.remainingReports === 0} onClick={() => generate(project.id)} className="mt-3 w-full rounded-xl bg-violet-700 text-white py-2.5 font-bold disabled:opacity-50 flex items-center justify-center gap-2"><Zap size={16} />{generating === project.id ? 'Gerando...' : 'Gerar relatório'}</button></div>}
              {message?.projectId === project.id && <div className={`mt-4 rounded-xl p-3 text-sm ${message.error ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'}`}>{message.text}</div>}
              <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-between"><span className="text-xs text-slate-400 flex items-center gap-2"><Calendar size={13} />{new Date(project.created_at).toLocaleDateString('pt-BR')}</span><div className="flex gap-2"><button onClick={() => setOpenProject(openProject === project.id ? null : project.id)} className="rounded-lg bg-amber-100 text-amber-800 p-2" title="Gerar relatório"><Zap size={16} /></button><button onClick={() => navigate(`/reports?project=${project.id}`)} className="rounded-lg bg-slate-950 text-white px-3 py-2 text-xs font-bold">Relatórios</button></div></div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
