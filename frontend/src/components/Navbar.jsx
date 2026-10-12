import React, { useState, useEffect } from 'react';
import { Menu, Activity, Sparkles, Terminal, Bell, Search } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { measureApiLatency } from '../services/api';

export default function Navbar({ onMenuToggle }) {
  const [latency, setLatency] = useState(null);
  const location = useLocation();

  useEffect(() => {
    let isMounted = true;
    const testPing = async () => {
      const res = await measureApiLatency();
      if (isMounted) {
        if (typeof res === 'number') {
          setLatency(`${res}ms`);
        } else if (res?.latency) {
          setLatency(`${res.latency}ms (down)`);
        } else {
          setLatency('Offline');
        }
      }
    };
    testPing();
    const interval = setInterval(testPing, 20000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="glass-nav sticky top-0 z-30 h-16 flex items-center justify-between px-4 sm:px-6 lg:px-8">
      <div className="flex items-center space-x-3">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="hidden sm:flex items-center space-x-2 text-xs font-mono text-cyan-300/80 bg-white/[0.04] px-3 py-1.5 rounded-xl border border-white/[0.08]">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span>Autonomous Supply Chain Control Matrix</span>
        </div>
      </div>

      <div className="flex items-center space-x-3 sm:space-x-4">
        {/* Latency telemetry pill */}
        <Link
          to="/health"
          className="flex items-center space-x-2 px-3 py-1.5 rounded-xl text-xs font-mono bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-cyan-400/30 transition-all text-slate-300"
          title="Telemetry roundtrip latency to FastAPI backend"
        >
          <Activity className="h-3.5 w-3.5 text-cyan-400" />
          <span className="text-slate-400 hidden xs:inline">Latency:</span>
          <span className="text-cyan-300 font-semibold">{latency || 'Pinging...'}</span>
        </Link>

        {/* Prescriptions Quick Action */}
        <Link
          to="/prescriptions"
          className="glass-button-primary hidden sm:inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-white shadow-sm shadow-cyan-500/20"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>AI Prescriptions</span>
        </Link>

        {/* API Docs link */}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 rounded-xl text-slate-400 hover:text-cyan-300 hover:bg-white/[0.08] border border-transparent hover:border-white/10 transition-colors"
          title="FastAPI Swagger Documentation"
        >
          <Terminal className="h-4 w-4" />
        </a>
      </div>
    </header>
  );
}
