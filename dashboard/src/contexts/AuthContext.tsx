import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import api from '../lib/api';
import { ARK_SESSION_KEY } from '../lib/ark-auth';

export interface ArkUser {
  id: string;
  name: string;
  email: string;
  isPlatformAdmin?: boolean;
}

export interface ArkOrganization {
  id: string;
  name: string;
  slug: string;
  plan?: string;
  role?: string;
}

export interface ArkLogAccess {
  status: 'PENDING' | 'TRIAL' | 'ACTIVE' | 'BLOCKED';
  reportLimit: number;
  reportsUsed: number;
  remainingReports: number | null;
  isAdmin: boolean;
  approvedAt?: string | null;
  blockedReason?: string | null;
}

export interface ArkAccount {
  user: ArkUser;
  organization: ArkOrganization;
}

export interface ArkAuthenticationResult extends ArkAccount {
  token: string;
  expiresAt?: string;
}

interface AuthContextType {
  user: ArkUser | null;
  organization: ArkOrganization | null;
  access: ArkLogAccess | null;
  token: string | null;
  isLoading: boolean;
  authenticate: (result: ArkAuthenticationResult) => Promise<void>;
  refreshAccess: () => Promise<ArkLogAccess | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function readStoredAccount(): ArkAccount | null {
  try {
    const raw = localStorage.getItem('arklog_account');
    return raw ? (JSON.parse(raw) as ArkAccount) : null;
  } catch {
    return null;
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<ArkUser | null>(null);
  const [organization, setOrganization] = useState<ArkOrganization | null>(null);
  const [access, setAccess] = useState<ArkLogAccess | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clear = useCallback(() => {
    setToken(null);
    setUser(null);
    setOrganization(null);
    setAccess(null);
    localStorage.removeItem(ARK_SESSION_KEY);
    localStorage.removeItem('arklog_account');
  }, []);

  const refreshAccess = useCallback(async (): Promise<ArkLogAccess | null> => {
    const activeToken = localStorage.getItem(ARK_SESSION_KEY);
    if (!activeToken) return null;
    try {
      const response = await api.get('/access/me');
      const nextAccess = response.data.access as ArkLogAccess;
      setAccess(nextAccess);
      if (response.data.user && response.data.organization) {
        const account: ArkAccount = {
          user: response.data.user,
          organization: response.data.organization,
        };
        setUser(account.user);
        setOrganization(account.organization);
        localStorage.setItem('arklog_account', JSON.stringify(account));
      }
      return nextAccess;
    } catch (error: any) {
      if (error?.response?.status === 401) clear();
      throw error;
    }
  }, [clear]);

  const authenticate = useCallback(async (result: ArkAuthenticationResult) => {
    const account: ArkAccount = { user: result.user, organization: result.organization };
    localStorage.setItem(ARK_SESSION_KEY, result.token);
    localStorage.setItem('arklog_account', JSON.stringify(account));
    setToken(result.token);
    setUser(result.user);
    setOrganization(result.organization);
    await refreshAccess();
  }, [refreshAccess]);

  const logout = useCallback(async () => {
    const currentToken = localStorage.getItem(ARK_SESSION_KEY);
    try {
      if (currentToken) {
        await fetch('/api/saas?action=logout', {
          method: 'POST',
          headers: { Authorization: `Bearer ${currentToken}` },
        });
      }
    } finally {
      clear();
    }
  }, [clear]);

  useEffect(() => {
    const savedToken = localStorage.getItem(ARK_SESSION_KEY);
    const savedAccount = readStoredAccount();
    if (!savedToken) {
      setIsLoading(false);
      return;
    }
    setToken(savedToken);
    if (savedAccount) {
      setUser(savedAccount.user);
      setOrganization(savedAccount.organization);
    }
    refreshAccess()
      .catch(() => clear())
      .finally(() => setIsLoading(false));
  }, [clear, refreshAccess]);

  const value = useMemo(() => ({
    user,
    organization,
    access,
    token,
    isLoading,
    authenticate,
    refreshAccess,
    logout,
  }), [user, organization, access, token, isLoading, authenticate, refreshAccess, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
