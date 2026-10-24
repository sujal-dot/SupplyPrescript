import React from 'react';

export function GlassInput({
  label,
  error,
  icon: Icon,
  className = '',
  id,
  ...props
}) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-medium text-slate-300">
          {label}
        </label>
      )}
      <div className="relative">
        {Icon && (
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <Icon className="h-4 w-4" />
          </div>
        )}
        <input
          id={inputId}
          className={`glass-input w-full py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none transition-all ${
            Icon ? 'pl-10 pr-3.5' : 'px-3.5'
          } ${error ? 'border-rose-400/50 focus:border-rose-400' : ''} ${className}`}
          {...props}
        />
      </div>
      {error && <p className="text-xs text-rose-400 mt-1">{error}</p>}
    </div>
  );
}

export function GlassSelect({
  label,
  error,
  options = [],
  className = '',
  id,
  children,
  ...props
}) {
  const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label htmlFor={selectId} className="block text-xs font-medium text-slate-300">
          {label}
        </label>
      )}
      <select
        id={selectId}
        className={`glass-input w-full py-2 px-3.5 text-sm text-slate-100 bg-[#16070B] focus:outline-none transition-all cursor-pointer ${
          error ? 'border-rose-400/50' : ''
        } ${className}`}
        {...props}
      >
        {children ||
          options.map((opt) => (
            <option
              key={opt.value !== undefined ? opt.value : opt}
              value={opt.value !== undefined ? opt.value : opt}
              className="bg-[#16070B] text-slate-100"
            >
              {opt.label || opt}
            </option>
          ))}
      </select>
      {error && <p className="text-xs text-rose-400 mt-1">{error}</p>}
    </div>
  );
}

export default GlassInput;
