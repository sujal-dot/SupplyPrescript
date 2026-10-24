import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Clock } from 'lucide-react';

export default function DecisionSuccessBadge({ status = 'PENDING_REVIEW', size = 'md' }) {
  const norm = String(status || 'PENDING_REVIEW').toUpperCase();

  const configs = {
    SUCCESS: {
      label: 'Decision Success',
      bg: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
      icon: CheckCircle2,
      iconColor: 'text-emerald-400',
    },
    PARTIAL_SUCCESS: {
      label: 'Partial Success',
      bg: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
      icon: AlertTriangle,
      iconColor: 'text-amber-400',
    },
    FAILURE: {
      label: 'Decision Failure',
      bg: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
      icon: XCircle,
      iconColor: 'text-rose-400',
    },
    PENDING_REVIEW: {
      label: 'Pending Outcome',
      bg: 'bg-slate-800 text-slate-300 border-slate-700',
      icon: Clock,
      iconColor: 'text-slate-400',
    },
  };

  const current = configs[norm] || configs.PENDING_REVIEW;
  const Icon = current.icon;

  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5 space-x-1',
    md: 'text-xs px-2.5 py-1 space-x-1.5',
    lg: 'text-sm px-3.5 py-1.5 space-x-2',
  }[size] || 'text-xs px-2.5 py-1 space-x-1.5';

  return (
    <span
      className={`inline-flex items-center font-mono font-bold rounded-full border shadow-sm ${current.bg} ${sizeClasses}`}
      title={`Decision Outcome Status: ${current.label}`}
      aria-label={`Decision Success: ${current.label}`}
    >
      <Icon className={`h-3.5 w-3.5 ${current.iconColor} flex-shrink-0`} />
      <span>{current.label}</span>
    </span>
  );
}
