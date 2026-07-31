import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { translations, type Locale, type TranslationKeys } from '../lib/i18n';

interface UserSettings {
  locale: Locale;
  timezone: string;
  countryCode: string;
  reportStyle: 'technical' | 'executive' | 'mixed';
}

interface SettingsContextType {
  settings: UserSettings;
  t: TranslationKeys;
  updateSettings: (patch: Partial<UserSettings>) => void;
}

const DEFAULTS: UserSettings = {
  locale: 'pt-BR',
  timezone: 'America/Sao_Paulo',
  countryCode: 'BR',
  reportStyle: 'mixed',
};

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<UserSettings>(() => {
    try {
      const stored = localStorage.getItem('arklog_settings');
      return stored ? { ...DEFAULTS, ...JSON.parse(stored) } : DEFAULTS;
    } catch {
      return DEFAULTS;
    }
  });

  const updateSettings = useCallback((patch: Partial<UserSettings>) => {
    setSettings((previous) => {
      const next = { ...previous, ...patch };
      localStorage.setItem('arklog_settings', JSON.stringify(next));
      return next;
    });
  }, []);

  useEffect(() => {
    document.documentElement.lang = settings.locale;
  }, [settings.locale]);

  const t = translations[settings.locale] as TranslationKeys;

  return (
    <SettingsContext.Provider value={{ settings, t, updateSettings }}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) throw new Error('useSettings must be used within SettingsProvider');
  return context;
};
