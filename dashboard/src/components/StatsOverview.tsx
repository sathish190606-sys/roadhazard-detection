import React from 'react';
import { AlertTriangle, Disc, Zap, Activity, CheckCircle2, Bot } from 'lucide-react';
import { Stats } from '../types';

interface StatsOverviewProps {
  stats: Stats | null;
}

export const StatsOverview: React.FC<StatsOverviewProps> = ({ stats }) => {
  if (!stats) return null;

  const cards = [
    {
      title: 'Total Hazards',
      value: stats.total_hazards,
      subtitle: `${stats.by_status.new || 0} active triage`,
      icon: AlertTriangle,
      color: 'from-amber-500/20 to-orange-500/10',
      iconColor: 'text-amber-400',
      borderColor: 'border-amber-500/20',
    },
    {
      title: 'Potholes Detected',
      value: stats.by_class.pothole || 0,
      subtitle: 'Critical road damage',
      icon: Disc,
      color: 'from-rose-500/20 to-red-500/10',
      iconColor: 'text-rose-400',
      borderColor: 'border-rose-500/20',
    },
    {
      title: 'Cracks Detected',
      value: stats.by_class.crack || 0,
      subtitle: 'Surface degradation',
      icon: Zap,
      color: 'from-yellow-500/20 to-amber-500/10',
      iconColor: 'text-yellow-400',
      borderColor: 'border-yellow-500/20',
    },
    {
      title: 'Animal Hazards',
      value: stats.by_class.animal || 0,
      subtitle: 'Dynamic collision risks',
      icon: Activity,
      color: 'from-cyan-500/20 to-blue-500/10',
      iconColor: 'text-cyan-400',
      borderColor: 'border-cyan-500/20',
    },
    {
      title: 'Avg Severity',
      value: `${stats.average_severity.toFixed(1)}/100`,
      subtitle: `${stats.by_status.repaired || 0} repaired`,
      icon: CheckCircle2,
      color: 'from-purple-500/20 to-indigo-500/10',
      iconColor: 'text-purple-400',
      borderColor: 'border-purple-500/20',
    },
    {
      title: 'Active Fleet',
      value: `${stats.active_robots} / ${stats.total_robots || 1}`,
      subtitle: stats.active_robots > 0 ? 'Robots patrolling' : 'Standby / charging',
      icon: Bot,
      color: 'from-emerald-500/20 to-teal-500/10',
      iconColor: 'text-emerald-400',
      borderColor: 'border-emerald-500/20',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5 mb-6">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <div
            key={i}
            className={`glass-panel glass-panel-hover rounded-xl p-4 border ${c.borderColor} bg-gradient-to-br ${c.color}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-400 tracking-wide">{c.title}</span>
              <Icon className={`h-4 w-4 ${c.iconColor}`} />
            </div>
            <div className="text-2xl font-extrabold tracking-tight text-white">{c.value}</div>
            <div className="text-[11px] font-medium text-slate-400 mt-1 flex items-center gap-1">
              {c.subtitle}
            </div>
          </div>
        );
      })}
    </div>
  );
};
