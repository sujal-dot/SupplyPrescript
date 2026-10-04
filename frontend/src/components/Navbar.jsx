import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Layers, Activity, Home } from 'lucide-react';

export default function Navbar() {
  const location = useLocation();

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center space-x-3 group">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
            <Layers className="h-6 w-6 text-white" />
          </div>
          <div>
            <span className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              SupplyPrescript
            </span>
            <span className="block text-xs text-slate-400 font-medium">Phase 1 Foundation</span>
          </div>
        </Link>

        <nav className="flex items-center space-x-2">
          <Link
            to="/"
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              location.pathname === '/'
                ? 'bg-slate-800 text-cyan-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Home className="h-4 w-4" />
            <span>Overview</span>
          </Link>
          <Link
            to="/health"
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              location.pathname === '/health'
                ? 'bg-slate-800 text-cyan-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Activity className="h-4 w-4" />
            <span>System Health</span>
          </Link>
        </nav>
      </div>
    </header>
  );
}
