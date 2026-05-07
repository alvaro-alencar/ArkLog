import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../lib/api';

// Module-level set persists across StrictMode remounts, preventing the same
// one-time GitHub code from being exchanged twice.
const usedCodes = new Set<string>();

const OAuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code) {
      navigate('/login');
      return;
    }

    if (usedCodes.has(code)) return;
    usedCodes.add(code);

    api.get(`/auth/callback/github?code=${code}`)
      .then(response => {
        const { access_token, user } = response.data;
        login(access_token, user);
        navigate('/');
      })
      .catch(error => {
        usedCodes.delete(code);
        console.error('OAuth callback failed', error);
        navigate('/login');
      });
  }, [searchParams, login, navigate]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-black gap-4">
      <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
      <p className="text-gray-400 animate-pulse">Authenticating with GitHub...</p>
    </div>
  );
};

export default OAuthCallback;
