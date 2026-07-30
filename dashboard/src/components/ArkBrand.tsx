import React from 'react';

const ArkMark: React.FC<{ size?: number; className?: string }> = ({ size = 42, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" fill="none" aria-hidden="true" className={className}>
    <path d="M6 34 20 6l14 28" stroke="currentColor" strokeWidth="4.6" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M12.6 23h14.8" stroke="currentColor" strokeWidth="4.2" strokeLinecap="round" />
  </svg>
);

const ArkBrand: React.FC<{ compact?: boolean; inverse?: boolean }> = ({ compact = false, inverse = false }) => (
  <div className={`inline-flex items-center ${compact ? 'gap-2.5' : 'gap-3.5'} ${inverse ? 'text-white' : 'text-slate-950'}`}>
    <span className={`grid place-items-center rounded-2xl ${compact ? 'h-11 w-11' : 'h-14 w-14'} ${inverse ? 'bg-white/10 text-violet-300' : 'bg-violet-50 text-violet-600'}`}>
      <ArkMark size={compact ? 32 : 40} />
    </span>
    <span className="leading-none">
      <span className={`${compact ? 'text-xl' : 'text-2xl'} block font-black tracking-tight`}>ArkLog</span>
      <span className={`mt-1 block text-[10px] font-bold uppercase tracking-[0.2em] ${inverse ? 'text-slate-300' : 'text-slate-500'}`}>ArkSystem</span>
    </span>
  </div>
);

export { ArkMark };
export default ArkBrand;
