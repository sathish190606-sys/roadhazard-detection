import React, { useEffect, useState, useCallback } from 'react';
import { api, LiveSocket } from './api/client';
import { Hazard, RobotStatus, Stats, User } from './types';
import { Header } from './components/Header';
import { StatsOverview } from './components/StatsOverview';
import { MapView } from './components/MapView';
import { HazardTable } from './components/HazardTable';
import { PriorityQueue } from './components/PriorityQueue';
import { RobotStatusCard } from './components/RobotStatusCard';
import { HazardModal } from './components/HazardModal';
import { LoginPage } from './components/LoginPage';
import { BellRing } from 'lucide-react';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [hazards, setHazards] = useState<Hazard[]>([]);
  const [robots, setRobots] = useState<RobotStatus[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [selectedHazard, setSelectedHazard] = useState<Hazard | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [alertBanner, setAlertBanner] = useState<string | null>(null);

  // Check auth session
  useEffect(() => {
    const token = api.getAuthToken();
    if (token) {
      api.getCurrentUser()
        .then((u) => setUser(u))
        .catch(() => {
          api.clearAuthToken();
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const loadAllData = useCallback(async () => {
    try {
      const [hList, rList, sData] = await Promise.all([
        api.getHazards(),
        api.getRobots(),
        api.getStats(),
      ]);
      setHazards(hList);
      setRobots(rList);
      setStats(sData);
    } catch (err) {
      console.error('Error fetching initial dashboard data:', err);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadAllData();
    }
  }, [user, loadAllData]);

  // Handle incoming live WebSocket messages
  const handleLiveMessage = useCallback((msg: { type: string; data: any }) => {
    if (msg.type === 'NEW_HAZARD') {
      const newHazard: Hazard = msg.data;
      setHazards((prev) => [newHazard, ...prev.filter((h) => h.id !== newHazard.id)]);

      // Show alert toast for critical hazard
      if (newHazard.severity_score >= 75) {
        setAlertBanner(
          `URGENT: ${newHazard.hazard_class.toUpperCase()} detected with severity ${newHazard.severity_score}${newHazard.reported_by ? ` by ${newHazard.reported_by}` : ` by ${newHazard.robot_id}`}!`
        );
        setTimeout(() => setAlertBanner(null), 7000);
      }

      // Refresh aggregate stats
      api.getStats().then(setStats).catch(console.error);
    } else if (msg.type === 'HAZARD_UPDATED') {
      const updated: Hazard = msg.data;
      setHazards((prev) => prev.map((h) => (h.id === updated.id ? updated : h)));
      api.getStats().then(setStats).catch(console.error);
    } else if (msg.type === 'HAZARD_DELETED') {
      const deletedId: number = msg.data.id;
      setHazards((prev) => prev.filter((h) => h.id !== deletedId));
      api.getStats().then(setStats).catch(console.error);
    } else if (msg.type === 'ROBOT_HEARTBEAT') {
      const robotHeartbeat: RobotStatus = msg.data;
      setRobots((prev) => {
        const idx = prev.findIndex((r) => r.robot_id === robotHeartbeat.robot_id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = robotHeartbeat;
          return next;
        }
        return [...prev, robotHeartbeat];
      });
    }
  }, []);

  // Connect WebSocket
  useEffect(() => {
    if (!user) return;
    const socket = new LiveSocket(handleLiveMessage);
    socket.connect();
    setWsConnected(true);

    return () => {
      socket.disconnect();
      setWsConnected(false);
    };
  }, [user, handleLiveMessage]);

  const handleUpdateStatus = async (id: number, status: 'new' | 'acknowledged' | 'repaired') => {
    try {
      const updated = await api.updateHazardStatus(id, status);
      setHazards((prev) => prev.map((h) => (h.id === id ? updated : h)));
      api.getStats().then(setStats).catch(console.error);
    } catch (err: any) {
      // Hazard was already deleted – remove from local state silently
      if (err.message?.includes('not found') || err.message?.includes('Not Found')) {
        setHazards((prev) => prev.filter((h) => h.id !== id));
        if (selectedHazard?.id === id) setSelectedHazard(null);
        api.getStats().then(setStats).catch(console.error);
        return;
      }
      // Show user-friendly error for permission denied
      if (err.message?.includes('admin')) {
        setAlertBanner('⛔ Only admins can mark hazards as repaired');
        setTimeout(() => setAlertBanner(null), 4000);
      }
      console.error('Failed to update status:', err);
    }
  };

  const handleDeleteHazard = async (id: number) => {
    // Immediately remove from UI to prevent double-click retries
    setHazards((prev) => prev.filter((h) => h.id !== id));
    if (selectedHazard?.id === id) setSelectedHazard(null);
    try {
      await api.deleteHazard(id);
      api.getStats().then(setStats).catch(console.error);
      setAlertBanner(`🗑️ Hazard #${id} deleted as fake/invalid`);
      setTimeout(() => setAlertBanner(null), 4000);
    } catch (err: any) {
      console.error('Failed to delete hazard:', err);
      setAlertBanner(`❌ ${err.message}`);
      setTimeout(() => setAlertBanner(null), 4000);
      // Re-fetch hazards to restore state if delete truly failed
      api.getHazards().then(setHazards).catch(console.error);
    }
  };

  const handleReportHazard = async (lat: number, lng: number, hazardClass: string, description?: string, snapshotBase64?: string) => {
    try {
      const newHazard = await api.reportHazard({
        hazard_class: hazardClass,
        latitude: lat,
        longitude: lng,
        description,
        snapshot_base64: snapshotBase64,
      });
      setHazards((prev) => [newHazard, ...prev]);
      api.getStats().then(setStats).catch(console.error);
      setAlertBanner(`✅ ${hazardClass.toUpperCase()} reported successfully at ${lat.toFixed(5)}, ${lng.toFixed(5)}`);
      setTimeout(() => setAlertBanner(null), 4000);
    } catch (err: any) {
      console.error('Failed to report hazard:', err);
      setAlertBanner(`❌ Failed to report: ${err.message}`);
      setTimeout(() => setAlertBanner(null), 4000);
    }
  };

  const handleLogout = () => {
    api.clearAuthToken();
    setUser(null);
  };

  const isAdmin = user?.role === 'admin';

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-cyan-400">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
          <span className="text-xs font-mono">Initializing Telemetry Console...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage onLoginSuccess={setUser} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-cyan-500 selection:text-white pb-12">
      <Header
        user={user}
        wsConnected={wsConnected}
        onRefresh={loadAllData}
        onLogout={handleLogout}
      />

      {/* Real-time Alert Banner */}
      {alertBanner && (
        <div className={`sticky top-[61px] z-30 ${alertBanner.startsWith('⛔') || alertBanner.startsWith('❌') ? 'bg-rose-600/90' : alertBanner.startsWith('✅') ? 'bg-emerald-600/90' : 'bg-rose-600/90'} text-white px-6 py-2.5 text-xs font-semibold backdrop-blur-md shadow-lg flex items-center justify-between`}>
          <div className="flex items-center gap-2">
            {!alertBanner.startsWith('⛔') && !alertBanner.startsWith('❌') && !alertBanner.startsWith('✅') && (
              <BellRing className="h-4 w-4 animate-spin" />
            )}
            <span>{alertBanner}</span>
          </div>
          <button
            onClick={() => setAlertBanner(null)}
            className="rounded px-2 py-0.5 bg-black/30 hover:bg-black/50 text-[10px] uppercase font-bold"
          >
            Dismiss
          </button>
        </div>
      )}

      <main className="max-w-[1700px] mx-auto px-6 pt-6">
        {/* KPI Analytics Ribbon */}
        <StatsOverview stats={stats} />

        {/* Map & Live Status Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
          <div className="lg:col-span-3">
            <MapView
              hazards={hazards}
              robots={robots}
              selectedHazard={selectedHazard}
              onSelectHazard={setSelectedHazard}
              onUpdateStatus={handleUpdateStatus}
              onDeleteHazard={handleDeleteHazard}
              onReportHazard={handleReportHazard}
              userRole={user.role}
            />
          </div>

          <div className="space-y-6">
            <RobotStatusCard robots={robots} />
            <PriorityQueue
              hazards={hazards}
              onSelectHazard={setSelectedHazard}
              onUpdateStatus={handleUpdateStatus}
              userRole={user.role}
            />
          </div>
        </div>

        {/* Ledger & Search Table */}
        <HazardTable
          hazards={hazards}
          onSelectHazard={setSelectedHazard}
          onUpdateStatus={handleUpdateStatus}
          onDeleteHazard={handleDeleteHazard}
          userRole={user.role}
        />
      </main>

      {/* Snapshot Inspection Modal */}
      <HazardModal
        hazard={selectedHazard}
        onClose={() => setSelectedHazard(null)}
        onUpdateStatus={handleUpdateStatus}
        onDeleteHazard={handleDeleteHazard}
        userRole={user.role}
      />
    </div>
  );
};
