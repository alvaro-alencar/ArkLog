import React, { useEffect, useState } from 'react';
import { CheckCircle2, LoaderCircle, TriangleAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';

const TrelloCallback: React.FC = () => {
  const navigate = useNavigate();
  const [error, setError] = useState('');

  useEffect(() => {
    const finish = async () => {
      const state = new URLSearchParams(window.location.search).get('state') || '';
      const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ''));
      const token = fragment.get('token') || '';
      const providerError = fragment.get('error') || '';
      if (providerError || !state || !token) {
        setError(providerError || 'O Trello não devolveu uma autorização válida.');
        return;
      }
      try {
        await api.post('/connections/trello/callback', { token, state });
        window.history.replaceState({}, document.title, `${import.meta.env.BASE_URL}connections?connected=trello`);
        navigate('/connections?connected=trello', { replace: true });
      } catch (caught: any) {
        setError(caught?.response?.data?.detail || 'Não foi possível concluir a conexão do Trello.');
      }
    };
    void finish();
  }, [navigate]);

  return (
    <div className="mx-auto max-w-xl rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      {error ? (
        <>
          <TriangleAlert className="mx-auto text-red-600" size={38} />
          <h1 className="mt-4 text-xl font-bold">A conexão do Trello não foi concluída</h1>
          <p className="mt-2 text-sm text-slate-500">{error}</p>
        </>
      ) : (
        <>
          <LoaderCircle className="mx-auto animate-spin text-violet-600" size={38} />
          <h1 className="mt-4 text-xl font-bold">Protegendo sua conexão Trello</h1>
          <p className="mt-2 text-sm text-slate-500">O token está sendo transferido diretamente para o cofre criptografado do ArkLog.</p>
          <CheckCircle2 className="mx-auto mt-5 text-emerald-500" size={22} />
        </>
      )}
    </div>
  );
};

export default TrelloCallback;
