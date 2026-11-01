import React from 'react';
import { Bot, Battery, Gauge, MapPin, Wifi, Clock } from 'lucide-react';
import { RobotStatus } from '../types';

interface RobotStatusCardProps {
  robots: RobotStatus[];
}

export const RobotStatusCard: React.FC<RobotStatusCardProps> = ({ robots }) => {
  return (
    <div className="glass-panel rounded-2xl p-5 border border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-blue-500/10 p-1.5 border border-blue-500/20 text-blue-400">
            <Bot className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Edge Robot Telemetry</h3>
            <p className="text-[11px] text-slate-400">Raspberry Pi 4 + ESP32 Gateway fleet</p>
          </div>
        </div>
        <span className="rounded-full bg-slate-850 px-2 py-0.5 text-[10px] font-mono text-slate-400 border border-slate-750">
          UART / MQTT
        </span>
      </div>

      <div className="space-y-3">
        {robots.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-500">
            No patrol robots registered. Awaiting heartbeat ping...
          </div>
        ) : (
          robots.map((r) => {
            const isOnline = r.is_online;
            const batteryColor =
              r.battery_percentage > 50
                ? 'bg-emerald-500'
                : r.battery_percentage > 20
                ? 'bg-amber-500'
                : 'bg-rose-500';

            return (
              <div
                key={r.robot_id}
                className="rounded-xl bg-slate-900/60 p-3.5 border border-slate-800/80"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2.5 w-2.5 rounded-full ${
                        isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
                      }`}
                    />
                    <span className="text-xs font-bold font-mono text-white">{r.robot_id}</span>
                  </div>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                      isOnline
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {isOnline ? r.status : 'offline'}
                  </span>
                </div>

                {/* Battery Meter */}
                <div className="mb-2.5">
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                    <span className="flex items-center gap-1">
                      <Battery className="h-3 w-3 text-slate-400" /> Battery Level
                    </span>
                    <span className="font-bold text-white">{r.battery_percentage}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${batteryColor}`}
                      style={{ width: `${Math.min(100, r.battery_percentage)}%` }}
                    />
                  </div>
                </div>

                {/* Telemetry Grid */}
                <div className="grid grid-cols-2 gap-2 text-[10px] pt-1 border-t border-slate-800/80">
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <Gauge className="h-3 w-3 text-blue-400" />
                    <span>Speed: <strong className="text-white">{r.speed.toFixed(1)} m/s</strong></span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <Wifi className="h-3 w-3 text-cyan-400" />
                    <span>{r.ip_address || '192.168.1.105'}</span>
                  </div>
                  <div className="col-span-2 flex items-center gap-1.5 text-slate-400 font-mono text-[9px]">
                    <MapPin className="h-3 w-3 text-amber-400 shrink-0" />
                    <span className="truncate">
                      {r.current_latitude && r.current_longitude
                        ? `${r.current_latitude.toFixed(6)}, ${r.current_longitude.toFixed(6)}`
                        : 'GPS Lock Pending'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
