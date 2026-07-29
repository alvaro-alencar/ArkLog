import axios from 'axios';
import { ARK_SESSION_KEY, clearArkSession } from './ark-auth';

const apiBase = import.meta.env.VITE_ARKLOG_API_BASE
  || (import.meta.env.PROD ? '/api/arklog/v1' : '/api/v1');

const api = axios.create({ baseURL: apiBase });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ARK_SESSION_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearArkSession();
      window.dispatchEvent(new Event('ark-auth-expired'));
    }
    return Promise.reject(error);
  },
);

export default api;
