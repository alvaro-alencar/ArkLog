import React, { useMemo, useState } from 'react';
import {
  Building2,
  Check,
  ExternalLink,
  Gauge,
  Globe2,
  KeyRound,
  Plug,
  RefreshCw,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  User,
  Workflow,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';
import { COUNTRIES, LOCALE_NAMES, type Locale } from '../lib/i18n';
import api from '../lib/api';

const Section: React.FC<{
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}> = ({ icon, title, description, children }) => (
  <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
    <div className="flex items-start gap-3 border-b border-slate-100 pb-5">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-100 text-violet-700">{icon}</div>
      <div>
        <h2 className="text-lg font-bold text-slate-950">{title}</h2>
        <p className="mt-1 text-sm leading-relaxed text-slate-500">{description}</p>
      </div>
    </div>
    <div className="mt-5">{children}</div>
  </section>
);

const LabelValue: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div className="rounded-2xl bg-slate-50 p-4">
    <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">{label}</p>
    <div className="mt-2 text-sm font-semibold text-slate-800">{value}</div>
  </div>
);

const Settings: React.FC = () => {
  const { user, organization, access, refreshAccess } = useAuth();
  const { settings, updateSettings } = useSettings();
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const selectedCountry = useMemo(
    () => COUNTRIES.find((country) => country.code === settings.countryCode) ?? COUNTRIES[0],
    [settings.countryCode],
  );

  const handleCountryChange = (code: string) => {
    const country = COUNTRIES.find((item) => item.code === code);
    if (!country) return;
    updateSettings({
      countryCode: country.code,
      locale: country.locale,
      timezone: country.timezone,
    });
  };

  const handleSave = async () => {
    setSaveState('saving');
    setError('');
    setMessage('');
    try {
      await api.patch('/users/me', {
        timezone: settings.timezone,
        language: settings.locale,
      });
      setSaveState('saved');
      setMessage('Preferências salvas neste navegador e sincronizadas com sua conta ArkLog.');
    } catch (caught: any) {
      setSaveState('idle');
      setError(caught?.response?.data?.detail || 'As preferências ficaram salvas neste navegador, mas não foi possível sincronizá-las agora.');
      return;
    }
    window.setTimeout(() => setSaveState('idle'), 1800);
  };

  const refreshAccount = async () => {
    setRefreshing(true);
    setError('');
    setMessage('');
    try {
      await refreshAccess();
      setMessage('Conta, organização e limites atualizados a partir do ArkSystem.');
    } catch (caught: any) {
      setError(caught?.response?.data?.detail || 'Não foi possível atualizar os dados da conta.');
    } finally {
      setRefreshing(false);
    }
  };

  const usagePercent = access?.reportLimit
    ? Math.min(100, Math.round((access.reportsUsed / access.reportLimit) * 100))
    : 0;

  return (
    <div className="space-y-7">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-[0.18em] text-violet-600">Conta e preferências</span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Configurações</h1>
          <p className="mt-2 max-w-3xl text-slate-500">A conta pertence ao ArkSystem. Aqui ficam apenas preferências reais do ArkLog e um retrato transparente do seu acesso.</p>
        </div>
        <button type="button" disabled={refreshing} onClick={() => void refreshAccount()} className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-700 hover:border-violet-300 hover:text-violet-700 disabled:opacity-50">
          <RefreshCw size={17} className={refreshing ? 'animate-spin' : ''} /> Atualizar conta
        </button>
      </header>

      {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div>}
      {message && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800">{message}</div>}

      <div className="grid gap-5 xl:grid-cols-2">
        <Section icon={<User size={20} />} title="Conta Ark" description="O ArkLog reutiliza a mesma identidade do ecossistema, sem criar um login paralelo.">
          <div className="flex items-center gap-4 rounded-2xl border border-slate-200 p-4">
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="" className="h-14 w-14 rounded-2xl object-cover" />
            ) : (
              <div className="grid h-14 w-14 place-items-center rounded-2xl bg-slate-100 text-slate-500"><User size={24} /></div>
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-lg font-bold text-slate-950">{user?.name || 'Conta Ark'}</p>
              <p className="truncate text-sm text-slate-500">{user?.email || 'E-mail não informado'}</p>
            </div>
            {user?.isPlatformAdmin && <span className="rounded-full bg-violet-100 px-3 py-1 text-xs font-bold text-violet-700">Admin da plataforma</span>}
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <LabelValue label="Identificador" value={user?.id || 'Não informado'} />
            <LabelValue label="Usuário" value={user?.username ? `@${user.username}` : 'Gerenciado pelo ArkSystem'} />
          </div>
        </Section>

        <Section icon={<Building2 size={20} />} title="Organização atual" description="Conexões e fluxos ficam isolados dentro desta organização Ark.">
          <div className="grid gap-3 sm:grid-cols-2">
            <LabelValue label="Organização" value={organization?.name || 'Não informada'} />
            <LabelValue label="Slug" value={organization?.slug || 'Não informado'} />
            <LabelValue label="Plano" value={organization?.plan || 'Padrão'} />
            <LabelValue label="Papel" value={organization?.role || 'Membro'} />
          </div>
        </Section>
      </div>

      <Section icon={<Gauge size={20} />} title="Acesso e consumo" description="O limite conta gerações de relatórios. Pré-testes, edição, clonagem e republicação de conteúdo salvo não consomem cota.">
        <div className="grid gap-4 md:grid-cols-[1fr_1.5fr]">
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-1">
            <LabelValue label="Status" value={<span className={`rounded-full px-3 py-1 text-xs font-bold ${access?.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700' : access?.status === 'TRIAL' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-800'}`}>{access?.status || 'PENDENTE'}</span>} />
            <LabelValue label="Perfil" value={access?.isAdmin ? 'Administrador do ArkLog' : 'Usuário'} />
          </div>
          <div className="rounded-2xl border border-slate-200 p-5">
            <div className="flex items-end justify-between gap-4">
              <div><p className="text-sm font-bold">Relatórios gerados</p><p className="mt-1 text-sm text-slate-500">{access?.reportsUsed ?? 0} usados {access?.remainingReports === null ? '· acesso sem limite' : `· ${access?.remainingReports ?? 0} restantes`}</p></div>
              {access?.reportLimit ? <strong className="text-2xl">{usagePercent}%</strong> : <strong className="text-2xl">∞</strong>}
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-violet-600 transition-all" style={{ width: `${access?.reportLimit ? usagePercent : 100}%` }} /></div>
          </div>
        </div>
      </Section>

      <div className="grid gap-5 xl:grid-cols-2">
        <Section icon={<Globe2 size={20} />} title="Idioma e região" description="O país ajusta idioma e fuso horário. Essas preferências também são persistidas no perfil do ArkLog.">
          <div className="space-y-4">
            <label className="block text-sm font-semibold text-slate-700">País
              <select value={selectedCountry.code} onChange={(event) => handleCountryChange(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-violet-500">
                {COUNTRIES.map((country) => <option key={country.code} value={country.code}>{country.flag} {country.nameEn}</option>)}
              </select>
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <LabelValue label="Idioma" value={LOCALE_NAMES[settings.locale as Locale]} />
              <LabelValue label="Fuso horário" value={<span className="font-mono text-xs">{settings.timezone}</span>} />
            </div>
          </div>
        </Section>

        <Section icon={<SlidersHorizontal size={20} />} title="Padrão para novos fluxos" description="A escolha entra automaticamente no editor quando você abre um novo fluxo. Fluxos existentes não são alterados.">
          <div className="grid gap-3">
            {[
              ['mixed', 'Executivo + técnico', 'Equilibra leitura gerencial com evidências técnicas.'],
              ['executive', 'Executivo', 'Foca impacto, riscos, decisões e próximos passos.'],
              ['technical', 'Técnico', 'Prioriza mudanças, automações, falhas e detalhes de implementação.'],
            ].map(([value, title, description]) => (
              <button key={value} type="button" onClick={() => updateSettings({ reportStyle: value as 'mixed' | 'executive' | 'technical' })} className={`rounded-2xl border p-4 text-left transition ${settings.reportStyle === value ? 'border-violet-400 bg-violet-50 ring-4 ring-violet-100' : 'border-slate-200 hover:border-violet-200'}`}>
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 grid h-5 w-5 place-items-center rounded-full border ${settings.reportStyle === value ? 'border-violet-600 bg-violet-600 text-white' : 'border-slate-300'}`}>{settings.reportStyle === value && <Check size={13} />}</div>
                  <div><p className="font-bold text-slate-900">{title}</p><p className="mt-1 text-sm text-slate-500">{description}</p></div>
                </div>
              </button>
            ))}
          </div>
        </Section>
      </div>

      <Section icon={<ShieldCheck size={20} />} title="Integrações e segurança" description="Não há tokens pessoais globais nem webhook GitHub manual escondido nesta tela.">
        <div className="grid gap-4 md:grid-cols-3">
          <Link to="/connections" className="group rounded-2xl border border-slate-200 p-5 transition hover:border-violet-300 hover:bg-violet-50">
            <Plug size={22} className="text-violet-600" /><p className="mt-4 font-bold">Conexões do usuário</p><p className="mt-2 text-sm text-slate-500">Autorize, teste e revogue serviços pela interface.</p>
          </Link>
          <Link to="/" className="group rounded-2xl border border-slate-200 p-5 transition hover:border-violet-300 hover:bg-violet-50">
            <Workflow size={22} className="text-violet-600" /><p className="mt-4 font-bold">Fluxos isolados</p><p className="mt-2 text-sm text-slate-500">Cada ponta pertence à sua conta e à organização atual.</p>
          </Link>
          <div className="rounded-2xl border border-slate-200 p-5">
            <KeyRound size={22} className="text-violet-600" /><p className="mt-4 font-bold">Cofre criptografado</p><p className="mt-2 text-sm text-slate-500">Credenciais ficam no backend e nunca são exibidas novamente no navegador.</p>
          </div>
        </div>
      </Section>

      <Section icon={<ShieldCheck size={20} />} title="Gerenciamento da conta" description="Criação, senha, sessão e eventual encerramento da conta pertencem ao ArkSystem, não a uma cópia local do ArkLog.">
        <div className="flex flex-col gap-4 rounded-2xl bg-slate-50 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="font-bold text-slate-900">Conta centralizada</p><p className="mt-1 text-sm text-slate-500">O ArkLog não exibe um botão de exclusão fictício. Alterações sensíveis devem acontecer no serviço central da conta Ark.</p></div>
          <a href="https://www.arksystem.net" className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:border-violet-300 hover:text-violet-700">Abrir ArkSystem <ExternalLink size={16} /></a>
        </div>
      </Section>

      <div className="flex justify-end">
        <button type="button" onClick={() => void handleSave()} disabled={saveState === 'saving'} className={`inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-bold transition disabled:opacity-60 ${saveState === 'saved' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-950 text-white hover:bg-violet-700'}`}>
          {saveState === 'saving' ? <RefreshCw size={17} className="animate-spin" /> : saveState === 'saved' ? <Check size={17} /> : <Save size={17} />}
          {saveState === 'saving' ? 'Salvando...' : saveState === 'saved' ? 'Preferências salvas' : 'Salvar preferências'}
        </button>
      </div>
    </div>
  );
};

export default Settings;
