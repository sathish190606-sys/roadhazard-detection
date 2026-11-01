import React from 'react';
import { Activity, Shield, LogOut, Radio, RefreshCw } from 'lucide-react';
import { User } from '../types';

interface HeaderProps {
  user: User | null;
  wsConnected: boolean;
  onRefresh: () => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  wsConnected,
  onRefresh,
  onLogout,
}) => {
  return (
    <header className="glass-panel sticky top-0 z-40 border-b border-slate-800/80 px-6 py-3.5 backdrop-blur-xl">
      <div className="flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-600 shadow-lg shadow-cyan-500/20">
            <Radio className="h-5 w-5 text-white animate-pulse" />
            <span className="absolute -bottom-0.5 -right-0.5 flex h-3 w-3">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${wsConnected ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
              <span className={`relative inline-flex rounded-full h-3 w-3 ${wsConnected ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
                RoadBot AI
                <span className="rounded-md bg-cyan-500/10 px-2 py-0.5 text-xs font-semibold text-cyan-400 border border-cyan-500/20">
                  YOLOv8-Nano Edge
                </span>
              </h1>
            </div>
            <p className="text-xs text-slate-400">
              Autonomous Road Hazard Patrol & Real-Time Telemetry
            </p>
          </div>
        </div>

        {/* Status & Actions */}
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 rounded-full bg-slate-900/80 px-3 py-1 text-xs border border-slate-800">
            <span className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-rose-400 animate-pulse'}`}></span>
            <span className="text-slate-300">
              {wsConnected ? 'Live Socket Connected' : 'Reconnecting Hub...'}
            </span>
          </div>

          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 rounded-lg bg-slate-850 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-all border border-slate-700/60"
            title="Refresh All Data"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Sync</span>
          </button>

          {user && (
            <div className="flex items-center gap-3 pl-2 border-l border-slate-800">
              <div className="text-right">
                <div className="text-xs font-medium text-slate-200">{user.username}</div>
                <div className="flex items-center justify-end gap-1 text-[10px] text-cyan-400 font-semibold uppercase tracking-wider">
                  <Shield className="h-2.5 w-2.5" />
                  {user.role}
                </div>
              </div>
              <button
                onClick={onLogout}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
