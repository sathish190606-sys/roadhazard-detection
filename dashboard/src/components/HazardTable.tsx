import React, { useState } from 'react';
import { Search, Download, Filter, CheckCircle2, Clock, AlertCircle, Eye, Trash2 } from 'lucide-react';
import { Hazard } from '../types';

interface HazardTableProps {
  hazards: Hazard[];
  onSelectHazard: (h: Hazard) => void;
  onUpdateStatus: (id: number, status: 'new' | 'acknowledged' | 'repaired') => void;
  onDeleteHazard: (id: number) => void;
  userRole: string;
}

export const HazardTable: React.FC<HazardTableProps> = ({
  hazards,
  onSelectHazard,
  onUpdateStatus,
  onDeleteHazard,
  userRole,
}) => {
  const isAdmin = userRole === 'admin';
  const [searchTerm, setSearchTerm] = useState('');
  const [classFilter, setClassFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortField, setSortField] = useState<'severity' | 'date' | 'confidence'>('severity');

  // Filter & Search
  const filtered = hazards.filter((h) => {
    const matchesSearch =
      h.robot_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      h.hazard_class.toLowerCase().includes(searchTerm.toLowerCase()) ||
      h.id.toString().includes(searchTerm);
    const matchesClass = classFilter === 'all' || h.hazard_class === classFilter;
    const matchesStatus = statusFilter === 'all' || h.status === statusFilter;
    return matchesSearch && matchesClass && matchesStatus;
  });

  // Sort
  const sorted = [...filtered].sort((a, b) => {
    if (sortField === 'severity') return b.severity_score - a.severity_score;
    if (sortField === 'confidence') return b.confidence - a.confidence;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  const exportCSV = () => {
    const headers = ['ID', 'Robot', 'Class', 'Confidence', 'Latitude', 'Longitude', 'Severity', 'Sightings', 'Status', 'Timestamp'];
    const rows = sorted.map((h) => [
      h.id,
      h.robot_id,
      h.hazard_class,
      (h.confidence * 100).toFixed(1) + '%',
      h.latitude,
      h.longitude,
      h.severity_score,
      h.cluster_count,
      h.status,
      h.created_at,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `road_hazards_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="glass-panel rounded-2xl p-5 border border-slate-800">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            Hazard Inspection Ledger
            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300 font-medium">
              {filtered.length} records
            </span>
          </h2>
          <p className="text-xs text-slate-400">Live feed of verified YOLOv8 surface anomalies</p>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search robot, class..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="rounded-lg bg-slate-900 border border-slate-700/80 pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Class Filter */}
          <select
            value={classFilter}
            onChange={(e) => setClassFilter(e.target.value)}
            className="rounded-lg bg-slate-900 border border-slate-700/80 px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Classes</option>
            <option value="pothole">Potholes</option>
            <option value="crack">Cracks</option>
            <option value="animal">Animals</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg bg-slate-900 border border-slate-700/80 px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Statuses</option>
            <option value="new">New</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="repaired">Repaired</option>
          </select>

          {/* Sort By */}
          <select
            value={sortField}
            onChange={(e) => setSortField(e.target.value as any)}
            className="rounded-lg bg-slate-900 border border-slate-700/80 px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="severity">Sort: Severity</option>
            <option value="confidence">Sort: Confidence</option>
            <option value="date">Sort: Time</option>
          </select>

          {/* Export CSV */}
          <button
            onClick={exportCSV}
            className="flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 transition-colors"
          >
            <Download className="h-3.5 w-3.5 text-cyan-400" />
            <span>CSV</span>
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-xl border border-slate-800/80">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider text-[10px] font-semibold border-b border-slate-800">
            <tr>
              <th className="px-3.5 py-2.5">ID / Class</th>
              <th className="px-3.5 py-2.5">Confidence</th>
              <th className="px-3.5 py-2.5">Severity</th>
              <th className="px-3.5 py-2.5">Sightings</th>
              <th className="px-3.5 py-2.5">Location (GPS)</th>
              <th className="px-3.5 py-2.5">Robot / Reporter</th>
              <th className="px-3.5 py-2.5">Status</th>
              <th className="px-3.5 py-2.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-8 text-slate-500">
                  No hazards match the current filters.
                </td>
              </tr>
            ) : (
              sorted.map((h) => {
                const isHigh = h.severity_score >= 75;
                return (
                  <tr
                    key={h.id}
                    className="hover:bg-slate-850/50 transition-colors cursor-pointer group"
                    onClick={() => onSelectHazard(h)}
                  >
                    <td className="px-3.5 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-slate-500">#{h.id}</span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                            h.hazard_class === 'pothole'
                              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              : h.hazard_class === 'crack'
                              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                              : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                          }`}
                        >
                          {h.hazard_class}
                        </span>
                      </div>
                    </td>
                    <td className="px-3.5 py-3 whitespace-nowrap font-medium text-slate-300">
                      {(h.confidence * 100).toFixed(1)}%
                    </td>
                    <td className="px-3.5 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              isHigh ? 'bg-rose-500' : 'bg-amber-400'
                            }`}
                            style={{ width: `${Math.min(100, h.severity_score)}%` }}
                          />
                        </div>
                        <span className={`font-bold ${isHigh ? 'text-rose-400' : 'text-slate-300'}`}>
                          {h.severity_score}
                        </span>
                      </div>
                    </td>
                    <td className="px-3.5 py-3 whitespace-nowrap text-slate-400">
                      {h.cluster_count > 1 ? (
                        <span className="text-cyan-400 font-semibold">{h.cluster_count}x</span>
                      ) : (
                        '1x'
                      )}
                    </td>
                    <td className="px-3.5 py-3 whitespace-nowrap font-mono text-[11px] text-slate-400">
                      {h.latitude.toFixed(5)}, {h.longitude.toFixed(5)}
                    </td>
                    <td className="px-3.5 py-3 whitespace-nowrap text-slate-300 font-mono text-xs">
                      {h.reported_by ? (
                        <span className="flex items-center gap-1.5">
                          <span className="h-1.5 w-1.5 rounded-full bg-purple-400"></span>
                          <span className="text-purple-300">{h.reported_by}</span>
                        </span>
                      ) : (
                        h.robot_id
                      )}
                    </td>
                    <td className="px-3.5 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize ${
                          h.status === 'repaired'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : h.status === 'acknowledged'
                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                      >
                        {h.status === 'repaired' ? (
                          <CheckCircle2 className="h-2.5 w-2.5" />
                        ) : h.status === 'acknowledged' ? (
                          <Clock className="h-2.5 w-2.5" />
                        ) : (
                          <AlertCircle className="h-2.5 w-2.5" />
                        )}
                        {h.status}
                      </span>
                    </td>
                    <td
                      className="px-3.5 py-3 whitespace-nowrap text-right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => onSelectHazard(h)}
                          className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
                          title="Inspect Details"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </button>
                        {h.status !== 'acknowledged' && (
                          <button
                            onClick={() => onUpdateStatus(h.id, 'acknowledged')}
                            className="rounded px-2 py-0.5 text-[10px] font-medium bg-blue-600/80 hover:bg-blue-600 text-white transition-colors"
                          >
                            Ack
                          </button>
                        )}
                        {h.status !== 'repaired' && isAdmin && (
                          <button
                            onClick={() => onUpdateStatus(h.id, 'repaired')}
                            className="rounded px-2 py-0.5 text-[10px] font-medium bg-emerald-600/80 hover:bg-emerald-600 text-white transition-colors"
                          >
                            Repaired
                          </button>
                        )}
                        {isAdmin && (
                          <button
                            onClick={() => {
                              if (window.confirm(`Delete hazard #${h.id} as fake/invalid? This cannot be undone.`)) {
                                onDeleteHazard(h.id);
                              }
                            }}
                            className="rounded p-1 text-slate-400 hover:bg-rose-500/20 hover:text-rose-400 transition-colors"
                            title="Delete fake hazard"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
