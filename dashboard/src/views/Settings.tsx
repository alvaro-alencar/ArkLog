import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { User, Globe, Cpu, Link2, AlertTriangle, Check, Copy, ChevronDown } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';
import { COUNTRIES, LOCALE_NAMES, type Locale } from '../lib/i18n';
import api from '../lib/api';

const WEBHOOK_URL = `${window.location.origin}/api/v1/webhooks/github`;

const Section: React.FC<{ icon: React.ReactNode; title: string; desc: string; children: React.ReactNode }> = ({ icon, title, desc, children }) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    className="glass-card p-6 space-y-5"
  >
    <div className="flex items-start gap-3 pb-4 border-b border-white/5">
      <div className="text-purple-400 mt-0.5">{icon}</div>
      <div>
        <h3 className="text-sm font-bold text-white">{title}</h3>
        <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
      </div>
    </div>
    {children}
  </motion.div>
);

const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="grid grid-cols-3 items-center gap-4">
    <label className="text-xs text-gray-400 font-medium">{label}</label>
    <div className="col-span-2">{children}</div>
  </div>
);

const Settings: React.FC = () => {
  const { user } = useAuth();
  const { settings, t, updateSettings } = useSettings();

  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const [copied, setCopied] = useState(false);
  const [selectedCountry, setSelectedCountry] = useState(
    COUNTRIES.find(c => c.code === settings.countryCode) ?? COUNTRIES[0]
  );

  const handleCountryChange = (code: string) => {
    const country = COUNTRIES.find(c => c.code === code);
    if (!country) return;
    setSelectedCountry(country);
    updateSettings({ countryCode: country.code, locale: country.locale, timezone: country.timezone });
  };

  const handleSave = async () => {
    setSaveState('saving');
    try {
      await api.patch('/users/me', {
        timezone: settings.timezone,
        language: settings.locale,
      });
    } catch {
      // preferences saved locally regardless
    }
    setSaveState('saved');
    setTimeout(() => setSaveState('idle'), 2000);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(WEBHOOK_URL);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const s = t.settings;

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">{s.title}</h2>
        <p className="text-gray-400 mt-1">{s.subtitle}</p>
      </div>

      {/* Profile */}
      <Section icon={<User size={16} />} title={s.profile} desc={s.profileDesc}>
        <Field label={s.username}>
          <div className="flex items-center gap-3">
            {user?.avatar_url && (
              <img src={user.avatar_url} alt={user.username} className="w-8 h-8 rounded-full border border-white/10" />
            )}
            <span className="text-sm text-white font-medium">@{user?.username}</span>
          </div>
        </Field>
        <Field label={s.email}>
          <span className="text-sm text-gray-400">{s.notProvided}</span>
        </Field>
      </Section>

      {/* Language & Region */}
      <Section icon={<Globe size={16} />} title={s.langRegion} desc={s.langRegionDesc}>
        <Field label={s.country}>
          <div className="relative">
            <select
              className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white appearance-none focus:outline-none focus:border-purple-500 transition-all pr-8"
              value={selectedCountry.code}
              onChange={e => handleCountryChange(e.target.value)}
            >
              {COUNTRIES.map(c => (
                <option key={c.code} value={c.code}>
                  {c.flag} {c.nameEn}
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-3 text-gray-500 pointer-events-none" />
          </div>
        </Field>

        <Field label={s.language}>
          <div className="flex items-center gap-2 px-3 py-2 bg-black/30 border border-white/5 rounded-lg">
            <span className="text-lg">{selectedCountry.flag}</span>
            <span className="text-sm text-white">{LOCALE_NAMES[settings.locale as Locale]}</span>
          </div>
        </Field>

        <Field label={s.timezone}>
          <div className="px-3 py-2 bg-black/30 border border-white/5 rounded-lg text-sm text-gray-300 font-mono">
            {settings.timezone}
          </div>
        </Field>
      </Section>

      {/* AI Preferences */}
      <Section icon={<Cpu size={16} />} title={s.aiPrefs} desc={s.aiPrefsDesc}>
        <Field label={s.reportStyle}>
          <div className="grid grid-cols-2 gap-2">
            {(['technical', 'executive'] as const).map(style => (
              <button
                key={style}
                onClick={() => updateSettings({ reportStyle: style })}
                className={`p-3 rounded-lg border text-left transition-all ${
                  settings.reportStyle === style
                    ? 'bg-purple-500/20 border-purple-500/50 text-white'
                    : 'bg-black/30 border-white/5 text-gray-400 hover:border-white/20'
                }`}
              >
                <p className="text-xs font-bold">{s[style]}</p>
                <p className="text-[10px] mt-0.5 text-gray-500">{s[`${style}Desc`]}</p>
              </button>
            ))}
          </div>
        </Field>
      </Section>

      {/* Integrations */}
      <Section icon={<Link2 size={16} />} title={s.integrations} desc={s.integrationsDesc}>
        <Field label={s.webhookUrl}>
          <div className="flex gap-2">
            <input
              readOnly
              value={WEBHOOK_URL}
              className="flex-1 bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-xs text-gray-300 font-mono focus:outline-none"
            />
            <button
              onClick={handleCopy}
              className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-gray-400 hover:text-white hover:border-white/20 transition-all"
            >
              {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
            </button>
          </div>
        </Field>
        <p className="text-[11px] text-gray-600 col-span-3 pl-0">{s.webhookInstructions}</p>
      </Section>

      {/* Save */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saveState !== 'idle'}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-bold transition-all ${
            saveState === 'saved'
              ? 'bg-green-500/20 border border-green-500/30 text-green-400'
              : 'bg-white text-black hover:bg-gray-200 disabled:opacity-60'
          }`}
        >
          {saveState === 'saving' && <div className="w-3.5 h-3.5 border-2 border-black/30 border-t-black rounded-full animate-spin" />}
          {saveState === 'saved' && <Check size={14} />}
          {s[saveState === 'idle' ? 'save' : saveState === 'saving' ? 'saving' : 'saved']}
        </button>
      </div>

      {/* Danger Zone */}
      <Section icon={<AlertTriangle size={16} className="text-red-400" />} title={s.dangerZone} desc={s.dangerZoneDesc}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-red-400">{s.deleteAccount}</p>
            <p className="text-xs text-gray-600 mt-0.5">{s.deleteWarning}</p>
          </div>
          <button
            onClick={() => {
              if (window.confirm(s.deleteWarning)) {
                alert('Feature coming soon.');
              }
            }}
            className="px-4 py-2 text-xs font-bold text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/10 transition-all"
          >
            {s.deleteAccount}
          </button>
        </div>
      </Section>
    </div>
  );
};

export default Settings;
