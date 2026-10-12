import React from 'react';
import { ChevronRight, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function PageHeader({
  title,
  subtitle,
  breadcrumbs = [],
  actions,
  lastUpdated,
  className = '',
}) {
  return (
    <div className={`mb-8 ${className}`}>
      {breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="flex items-center space-x-1.5 text-xs text-slate-400 mb-3">
          <Link to="/" className="hover:text-cyan-300 transition-colors">
            Home
          </Link>
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={idx}>
              <ChevronRight className="h-3 w-3 text-slate-600" />
              {crumb.href ? (
                <Link to={crumb.href} className="hover:text-cyan-300 transition-colors">
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-slate-300 font-medium">{crumb.label}</span>
              )}
            </React.Fragment>
          ))}
        </nav>
      )}

      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="text-sm text-slate-400 mt-1 max-w-3xl leading-relaxed">
              {subtitle}
            </p>
          )}
          {lastUpdated && (
            <div className="flex items-center space-x-1.5 text-[11px] text-cyan-300/80 font-mono mt-2">
              <Clock className="h-3 w-3" />
              <span>Telemetry synchronized: {lastUpdated}</span>
            </div>
          )}
        </div>

        {actions && <div className="flex items-center space-x-2.5 shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
