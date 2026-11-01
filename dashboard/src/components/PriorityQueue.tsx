import React from 'react';
import { Flame, AlertOctagon, ArrowUpRight, CheckCircle2 } from 'lucide-react';
import { Hazard } from '../types';

interface PriorityQueueProps {
  hazards: Hazard[];
  onSelectHazard: (h: Hazard) => void;
  onUpdateStatus: (id: number, status: 'new' | 'acknowledged' | 'repaired') => void;
  userRole: string;
}

export const PriorityQueue: React.FC<PriorityQueueProps> = ({
  hazards,
  onSelectHazard,
  onUpdateStatus,
  userRole,
}) => {
  const isAdmin = userRole === 'admin';
  // Only non-repaired hazards, sorted descending by severity_score
  const activeQueue = hazards
    .filter((h) => h.status !== 'repaired')
    .sort((a, b) => b.severity_score - a.severity_score)
    .slice(0, 5);

  return (
    <div className="glass-panel rounded-2xl p-5 border border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-rose-500/10 p-1.5 border border-rose-500/20 text-rose-400">
            <Flame className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Repair Priority Queue</h3>
            <p className="text-[11px] text-slate-400">Automated triage by impact & frequency</p>
          </div>
        </div>
        <span className="rounded-full bg-rose-500/10 px-2.5 py-0.5 text-[10px] font-bold text-rose-400 border border-rose-500/20">
          Urgent Attention
        </span>
      </div>

      <div className="space-y-2.5">
        {activeQueue.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-500">
            No pending repairs in queue! Road condition clear.
          </div>
        ) : (
          activeQueue.map((h, idx) => {
            const isCritical = h.severity_score >= 75;
            return (
              <div
                key={h.id}
                onClick={() => onSelectHazard(h)}
                className="group flex items-center justify-between p-3 rounded-xl bg-slate-900/60 hover:bg-slate-850/80 border border-slate-800/80 hover:border-slate-700 transition-all cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`flex h-6 w-6 items-center justify-center rounded-lg text-xs font-black ${
                      idx === 0
                        ? 'bg-rose-500 text-white shadow-md shadow-rose-500/30'
                        : idx === 1
                        ? 'bg-amber-500 text-slate-950 font-bold'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    #{idx + 1}
                  </span>

                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white uppercase tracking-wider">
                        {h.hazard_class}
                      </span>
                      {h.cluster_count > 1 && (
                        <span className="rounded bg-cyan-500/10 px-1.5 py-0.2 text-[9px] font-bold text-cyan-400 border border-cyan-500/20">
                          {h.cluster_count}x Cluster
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] font-mono text-slate-400">
                      Lat {h.latitude.toFixed(4)}, Lon {h.longitude.toFixed(4)}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className={`text-xs font-black ${isCritical ? 'text-rose-400' : 'text-amber-400'}`}>
                      Score {h.severity_score}
                    </div>
                    <div className="text-[9px] text-slate-500 uppercase font-medium">{h.status}</div>
                  </div>

                  {isAdmin && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onUpdateStatus(h.id, 'repaired');
                      }}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-emerald-500/20 hover:text-emerald-400 transition-colors"
                      title="Mark as Repaired"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
