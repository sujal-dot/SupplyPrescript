import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  TrendingUp,
  Package,
  Truck,
  Sparkles,
  Database,
  Activity,
  ChevronLeft,
  ChevronRight,
  Radio,
  Layers,
  ExternalLink,
} from 'lucide-react';
import { getBackendHealth } from '../services/api';

const navItems = [
  { path: '/', label: 'Overview Dashboard', icon: LayoutDashboard },
  { path: '/forecasting', label: 'Demand Forecasting', icon: TrendingUp },
  { path: '/inventory', label: 'Inventory Optimization', icon: Package },
  { path: '/shipments', label: 'Shipments & Logistics', icon: Truck },
  { path: '/prescriptions', label: 'Prescriptive Analytics', icon: Sparkles, badge: 'AI' },
  { path: '/data', label: 'Data Management', icon: Database },
  { path: '/health', label: 'System Health', icon: Activity },
];

export default function Sidebar({ isOpen, setIsOpen, isMobile, closeMobile }) {
  const [collapsed, setCollapsed] = useState(false);
  const [isBackendHealthy, setIsBackendHealthy] = useState(null);
  const location = useLocation();

  useEffect(() => {
    let isMounted = true;
    const checkLiveHealth = async () => {
      try {
        await getBackendHealth();
        if (isMounted) setIsBackendHealthy(true);
      } catch {
        if (isMounted) setIsBackendHealthy(false);
      }
    };
    checkLiveHealth();
    const interval = setInterval(checkLiveHealth, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <aside
      className={`fixed top-0 bottom-0 left-0 z-40 transition-all duration-300 ease-in-out glass-sidebar flex flex-col ${
        isMobile
          ? isOpen
            ? 'translate-x-0 w-72'
            : '-translate-x-full w-72'
          : collapsed
          ? 'w-20'
          : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-5 border-b border-white/[0.08]">
        <NavLink
          to="/"
          onClick={isMobile ? closeMobile : undefined}
          className="flex items-center space-x-3 group overflow-hidden"
        >
          <div className="h-10 w-10 rounded-2xl bg-gradient-to-tr from-cyan-500 via-sky-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/25 border border-white/20 shrink-0 group-hover:scale-105 transition-transform">
            <Layers className="h-5 w-5 text-white" />
          </div>
          {(!collapsed || isMobile) && (
            <div className="leading-none transition-opacity duration-200">
              <span className="text-base font-bold text-white tracking-tight">
                Supply<span className="text-cyan-400">Prescript</span>
              </span>
              <span className="block text-[10px] text-cyan-300/80 font-mono tracking-wider mt-1 uppercase">
                Enterprise AI
              </span>
            </div>
          )}
        </NavLink>

        {!isMobile && (
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        )}
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-5 px-3 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={isMobile ? closeMobile : undefined}
              className={`flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group relative ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-400/30 shadow-[inset_0_1px_1px_rgba(34,211,238,0.25)]'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.05] border border-transparent'
              }`}
              title={collapsed && !isMobile ? item.label : undefined}
            >
              <Icon
                className={`h-5 w-5 shrink-0 transition-transform duration-200 ${
                  isActive
                    ? 'text-cyan-400'
                    : 'text-slate-400 group-hover:text-slate-200 group-hover:scale-105'
                }`}
              />
              {(!collapsed || isMobile) && (
                <span className="truncate flex-1">{item.label}</span>
              )}

              {(!collapsed || isMobile) && item.badge && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-cyan-500/20 text-cyan-300 border border-cyan-400/30 shrink-0 font-bold">
                  {item.badge}
                </span>
              )}

              {/* Collapsed Tooltip on Hover */}
              {collapsed && !isMobile && (
                <div className="absolute left-full ml-3 px-2.5 py-1 rounded-lg glass-card text-xs text-white opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 border border-white/20">
                  {item.label}
                </div>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Backend Status Footer Bar */}
      <div className="p-4 border-t border-white/[0.08]">
        <NavLink
          to="/health"
          onClick={isMobile ? closeMobile : undefined}
          className="flex items-center space-x-2.5 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-cyan-400/30 transition-all group"
        >
          <div
            className={`w-2.5 h-2.5 rounded-full shrink-0 ${
              isBackendHealthy === true
                ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]'
                : isBackendHealthy === false
                ? 'bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.8)]'
                : 'bg-amber-400 animate-pulse'
            }`}
          />
          {(!collapsed || isMobile) && (
            <div className="truncate flex-1 text-left">
              <div className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300">
                {isBackendHealthy === true
                  ? 'Core Online'
                  : isBackendHealthy === false
                  ? 'Core Offline'
                  : 'Probing Core...'}
              </div>
              <div className="text-[10px] text-slate-500 font-mono">
                FastAPI Port 8000
              </div>
            </div>
          )}
        </NavLink>
      </div>
    </aside>
  );
}
