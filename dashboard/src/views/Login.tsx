import React, { FormEvent, useState } from 'react';
import { Eye, EyeOff, LockKeyhole, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ArkAuthenticationResult, useAuth } from '../contexts/AuthContext';

type Mode = 'login' | 'register';

async function arkAccountRequest(action: Mode, body: Record<string, string>): Promise<ArkAuthenticationResult> {
  const response = await fetch(`/api/saas?action=${action}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(String(payload.error || 'Não foi possível acessar a conta Ark.'));
  return payload as ArkAuthenticationResult;
}

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { authenticate } = useAuth();
  const [mode, setMode] = useState<Mode>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    name: '', organizationName: '', email: '', password: '',
  });

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const result = await arkAccountRequest(mode, form);
      await authenticate(result);
      navigate('/', { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Não foi possível entrar.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f7fb] text-slate-950 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-5xl grid lg:grid-cols-[1.1fr_0.9fr] bg-white rounded-[28px] shadow-2xl shadow-slate-200/70 overflow-hidden border border-slate-200">
        <section className="hidden lg:flex flex-col justify-between p-12 bg-slate-950 text-white relative overflow-hidden">
          <div className="absolute -right-24 -top-24 w-72 h-72 rounded-full bg-violet-600/30 blur-3xl" />
          <div className="relative">
            <img src={`${import.meta.env.BASE_URL}logo_arklog.png`} alt="ArkLog" className="h-28 w-auto object-contain" />
            <h1 className="text-4xl font-bold tracking-tight mt-10">Relatórios técnicos sem abrir a torneira dos seus créditos.</h1>
            <p className="text-slate-300 mt-5 text-lg leading-relaxed">
              A chave da IA permanece no servidor. Cada geração exige conta Ark, autorização do produto e cota disponível.
            </p>
          </div>
          <div className="relative space-y-4 text-sm text-slate-300">
            <p className="flex items-center gap-3"><ShieldCheck className="text-emerald-400" /> Acesso liberado individualmente</p>
            <p className="flex items-center gap-3"><LockKeyhole className="text-violet-400" /> Um relatório no teste gratuito</p>
          </div>
        </section>

        <main className="p-7 sm:p-10 lg:p-12">
          <div className="lg:hidden mb-7">
            <img src={`${import.meta.env.BASE_URL}logo_arklog.png`} alt="ArkLog" className="h-20 w-auto" />
          </div>
          <div className="inline-flex p-1 bg-slate-100 rounded-xl mb-8">
            <button type="button" onClick={() => setMode('login')} className={`px-5 py-2 rounded-lg text-sm font-semibold ${mode === 'login' ? 'bg-white shadow text-slate-950' : 'text-slate-500'}`}>Entrar</button>
            <button type="button" onClick={() => setMode('register')} className={`px-5 py-2 rounded-lg text-sm font-semibold ${mode === 'register' ? 'bg-white shadow text-slate-950' : 'text-slate-500'}`}>Criar conta</button>
          </div>

          <h2 className="text-3xl font-bold">{mode === 'login' ? 'Bem-vindo ao ArkLog' : 'Crie sua conta Ark'}</h2>
          <p className="text-slate-500 mt-2 mb-8">
            {mode === 'login' ? 'Use a mesma conta do ArkConta, ArkEvidence e ArkWall.' : 'O cadastro não libera consumo de IA automaticamente. A autorização vem depois.'}
          </p>

          <form onSubmit={submit} className="space-y-5">
            {mode === 'register' && (
              <>
                <label className="block text-sm font-semibold">Nome
                  <input required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-violet-500" />
                </label>
                <label className="block text-sm font-semibold">Organização
                  <input required minLength={2} value={form.organizationName} onChange={(e) => setForm({ ...form, organizationName: e.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-violet-500" />
                </label>
              </>
            )}
            <label className="block text-sm font-semibold">E-mail
              <input required type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-violet-500" />
            </label>
            <label className="block text-sm font-semibold">Senha
              <div className="relative mt-2">
                <input required minLength={10} type={showPassword ? 'text' : 'password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="w-full rounded-xl border border-slate-300 px-4 py-3 pr-12 outline-none focus:border-violet-500" />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500" aria-label="Mostrar senha">{showPassword ? <EyeOff size={20} /> : <Eye size={20} />}</button>
              </div>
            </label>

            {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
            <button disabled={isSubmitting} className="w-full rounded-xl bg-slate-950 text-white py-3.5 font-bold hover:bg-violet-700 disabled:opacity-50 transition-colors">
              {isSubmitting ? 'Verificando...' : mode === 'login' ? 'Entrar com conta Ark' : 'Criar conta segura'}
            </button>
          </form>
        </main>
      </div>
    </div>
  );
};

export default Login;
