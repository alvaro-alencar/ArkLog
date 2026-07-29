import React, { FormEvent, useState } from 'react';
import { ArrowLeft, GitBranch, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';

const TrialProject: React.FC = () => {
  const navigate = useNavigate();
  const [repo, setRepo] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      const cleanRepo = repo.trim().replace(/^https?:\/\/github\.com\//i, '').replace(/\.git$/i, '').replace(/\/$/, '');
      await api.post('/projects', {
        name: name.trim() || cleanRepo.replace('/', ' · '),
        repo_full_name: cleanRepo,
        description,
        report_style: 'misto',
        tech_stack: [],
        business_context: '',
        reports: [],
      });
      navigate('/');
    } catch (caught: any) {
      setError(String(caught?.response?.data?.detail || 'Não foi possível adicionar o projeto.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-10">
      <button onClick={() => navigate('/')} className="text-sm text-slate-500 flex items-center gap-2 mb-7"><ArrowLeft size={16} /> Voltar</button>
      <div className="bg-white border border-slate-200 rounded-3xl p-7 sm:p-9 shadow-sm">
        <div className="w-12 h-12 rounded-2xl bg-violet-100 text-violet-700 flex items-center justify-center"><GitBranch /></div>
        <h1 className="text-3xl font-bold mt-5">Adicionar repositório de teste</h1>
        <p className="text-slate-600 mt-3">Por segurança, o teste gratuito aceita somente um repositório público e não cria automações externas.</p>
        <form onSubmit={submit} className="space-y-5 mt-8">
          <label className="block text-sm font-semibold">Repositório público
            <input required value={repo} onChange={(e) => setRepo(e.target.value)} placeholder="proprietario/projeto" className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-violet-500" />
          </label>
          <label className="block text-sm font-semibold">Nome no ArkLog <span className="font-normal text-slate-400">(opcional)</span>
            <input value={name} onChange={(e) => setName(e.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-violet-500" />
          </label>
          <label className="block text-sm font-semibold">Contexto curto <span className="font-normal text-slate-400">(opcional)</span>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-violet-500" />
          </label>
          <div className="flex items-start gap-3 rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-sm text-emerald-900"><ShieldCheck className="shrink-0" size={20} /> A chave da OpenRouter não é enviada ao navegador, ao GitHub nem ao relatório.</div>
          {error && <div className="rounded-xl bg-red-50 border border-red-200 text-red-700 p-4 text-sm">{error}</div>}
          <button disabled={saving} className="w-full rounded-xl bg-slate-950 text-white py-3.5 font-bold disabled:opacity-50">{saving ? 'Validando...' : 'Adicionar projeto público'}</button>
        </form>
      </div>
    </div>
  );
};

export default TrialProject;
