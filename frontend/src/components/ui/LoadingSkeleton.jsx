import React from 'react';

export function LoadingSkeleton({ variant = 'card', count = 1, className = '' }) {
  const items = Array.from({ length: count });

  if (variant === 'card') {
    return (
      <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 ${className}`}>
        {items.map((_, i) => (
          <div key={i} className="glass-card p-6 rounded-2xl animate-pulse space-y-4">
            <div className="flex justify-between items-center">
              <div className="h-3.5 bg-white/10 rounded w-24" />
              <div className="h-8 w-8 bg-white/10 rounded-xl" />
            </div>
            <div className="h-8 bg-white/15 rounded w-20" />
            <div className="h-2.5 bg-white/10 rounded w-32" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className={`glass-card p-6 rounded-2xl animate-pulse space-y-4 ${className}`}>
        <div className="h-5 bg-white/10 rounded w-48 mb-6" />
        <div className="space-y-3">
          {items.map((_, i) => (
            <div key={i} className="flex space-x-4 py-3 border-b border-white/[0.05]">
              <div className="h-4 bg-white/10 rounded flex-1" />
              <div className="h-4 bg-white/10 rounded flex-1" />
              <div className="h-4 bg-white/10 rounded flex-1" />
              <div className="h-4 bg-white/10 rounded w-24" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (variant === 'chart') {
    return (
      <div className={`glass-card p-6 rounded-2xl animate-pulse space-y-4 ${className}`}>
        <div className="flex justify-between">
          <div className="h-5 bg-white/10 rounded w-48" />
          <div className="h-5 bg-white/10 rounded w-24" />
        </div>
        <div className="h-64 bg-white/[0.05] rounded-xl flex items-end p-4 space-x-3">
          {[40, 65, 45, 80, 55, 90, 70, 85].map((h, i) => (
            <div
              key={i}
              className="bg-white/10 rounded-t flex-1"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`glass-card p-6 rounded-2xl animate-pulse space-y-3 ${className}`}>
      <div className="h-4 bg-white/15 rounded w-3/4" />
      <div className="h-4 bg-white/10 rounded w-1/2" />
    </div>
  );
}

export default LoadingSkeleton;
