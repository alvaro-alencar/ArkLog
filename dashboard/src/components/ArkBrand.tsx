import React from 'react';

const ArkBrand: React.FC<{ compact?: boolean; inverse?: boolean }> = ({ compact = false, inverse = false }) => (
  <div className={`inline-flex items-center ${compact ? 'gap-2.5' : 'gap-3.5'}`}>
    <img
      src={`${import.meta.env.BASE_URL}ark-system-logo.svg`}
      alt="ArkSystem"
      className={`${compact ? 'h-7' : 'h-9'} w-auto object-contain`}
    />
    <span
      className={`${compact ? 'h-7' : 'h-9'} w-px ${inverse ? 'bg-white/20' : 'bg-slate-200'}`}
      aria-hidden="true"
    />
    <span className={`${compact ? 'text-xl' : 'text-2xl'} font-black leading-none tracking-tight ${inverse ? 'text-white' : 'text-slate-950'}`}>
      ArkLog
    </span>
  </div>
);

export default ArkBrand;
