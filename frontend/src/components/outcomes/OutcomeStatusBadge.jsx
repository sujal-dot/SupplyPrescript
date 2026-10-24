import React from 'react';
import { CheckCircle2, Clock, AlertTriangle, XCircle, ShieldCheck, HelpCircle } from 'lucide-react';

export default function OutcomeStatusBadge({ status = 'RECORDED' }) {
  const norm = String(status || '').toUpperCase();

  if (norm === 'DELIVERED' || norm === 'SUCCESS') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
        <CheckCircle2 className="h-3 w-3 inline text-emerald-400" />
        <span>DELIVERED</span>
      </span>
    );
  }

  if (norm === 'AWAITING_DELIVERY' || norm === 'PENDING') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
        <Clock className="h-3 w-3 inline text-amber-400" />
        <span>AWAITING DELIVERY</span>
      </span>
    );
  }

  if (norm === 'PARTIAL SUCCESS' || norm === 'PARTIAL') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30">
        <AlertTriangle className="h-3 w-3 inline text-rose-400" />
        <span>PARTIAL OUTCOME</span>
      </span>
    );
  }

  if (norm === 'CANCELLED' || norm === 'FAILURE') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30">
        <XCircle className="h-3 w-3 inline text-rose-400" />
        <span>CANCELLED</span>
      </span>
    );
  }

  if (norm === 'DISPUTED') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30">
        <AlertTriangle className="h-3 w-3 inline text-purple-400" />
        <span>DISPUTED</span>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-red-500/15 text-red-300 border border-red-500/30">
      <ShieldCheck className="h-3 w-3 inline text-red-400" />
      <span>{status || 'RECORDED'}</span>
    </span>
  );
}
