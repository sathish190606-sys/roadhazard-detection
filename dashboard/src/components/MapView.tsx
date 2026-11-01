import React, { useEffect, useState, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { Layers, Navigation, ExternalLink, ShieldAlert, Sparkles, Plus, X, MapPin, Send, Trash2, Map, Satellite, Mountain, PersonStanding, Minimize2, Camera, ImageIcon, LocateFixed } from 'lucide-react';
import { Hazard, RobotStatus } from '../types';
import { LocationSearch } from './LocationSearch';

interface MapViewProps {
  hazards: Hazard[];
  robots: RobotStatus[];
  selectedHazard: Hazard | null;
  onSelectHazard: (h: Hazard) => void;
  onUpdateStatus: (id: number, status: 'new' | 'acknowledged' | 'repaired') => void;
  onDeleteHazard: (id: number) => void;
  onReportHazard: (lat: number, lng: number, hazardClass: string, description?: string, snapshotBase64?: string) => void;
  userRole: string;
}

// Custom Leaflet DivIcons with vivid SVG styling
const createHazardIcon = (hazardClass: string, severity: number, isUserReported?: boolean) => {
  let color = '#ef4444'; // pothole: red
  let ringColor = 'rgba(239, 68, 68, 0.4)';
  if (hazardClass === 'crack') {
    color = '#f59e0b'; // crack: amber
    ringColor = 'rgba(245, 158, 11, 0.4)';
  } else if (hazardClass === 'animal') {
    color = '#06b6d4'; // animal: cyan
    ringColor = 'rgba(6, 182, 212, 0.4)';
  }

  const isHighSeverity = severity >= 75;
  const userBadge = isUserReported
    ? `<div style="position: absolute; top: -4px; right: -4px; width: 12px; height: 12px; border-radius: 50%; background: #a855f7; border: 1.5px solid #fff; display: flex; align-items: center; justify-content: center; font-size: 7px; color: white; font-weight: bold;">U</div>`
    : '';

  return L.divIcon({
    className: 'custom-hazard-marker',
    html: `
      <div style="position: relative; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">
        ${isHighSeverity ? `<div style="position: absolute; width: 36px; height: 36px; border-radius: 50%; background: ${ringColor}; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>` : ''}
        <div style="width: 26px; height: 26px; border-radius: 50%; background: ${color}; border: 2.5px solid #ffffff; box-shadow: 0 4px 10px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: bold;">
          ${hazardClass === 'pothole' ? 'P' : hazardClass === 'crack' ? 'C' : 'A'}
        </div>
        ${userBadge}
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  });
};

const robotIcon = L.divIcon({
  className: 'custom-robot-marker',
  html: `
    <div style="position: relative; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center;">
      <div style="position: absolute; width: 38px; height: 38px; border-radius: 50%; background: rgba(59, 130, 246, 0.35); animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;"></div>
      <div style="width: 28px; height: 28px; border-radius: 8px; background: linear-gradient(135deg, #2563eb, #1d4ed8); border: 2px solid #60a5fa; box-shadow: 0 4px 12px rgba(37,99,235,0.6); display: flex; align-items: center; justify-content: center; color: white;">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m12 2 8 8-8 8-8-8z"/><circle cx="12" cy="10" r="2"/></svg>
      </div>
    </div>
  `,
  iconSize: [38, 38],
  iconAnchor: [19, 19],
  popupAnchor: [0, -20],
});

const reportPinIcon = L.divIcon({
  className: 'custom-report-marker',
  html: `
    <div style="position: relative; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;">
      <div style="position: absolute; width: 40px; height: 40px; border-radius: 50%; background: rgba(168, 85, 247, 0.3); animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
      <div style="width: 30px; height: 30px; border-radius: 50%; background: linear-gradient(135deg, #a855f7, #7c3aed); border: 2.5px solid #fff; box-shadow: 0 4px 16px rgba(168,85,247,0.6); display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; font-weight: bold;">
        +
      </div>
    </div>
  `,
  iconSize: [40, 40],
  iconAnchor: [20, 20],
  popupAnchor: [0, -22],
});

// Custom Pegman icon showing where user is positioned in Street View
const streetViewPegmanIcon = L.divIcon({
  className: 'custom-streetview-marker',
  html: `
    <div style="position: relative; width: 46px; height: 46px; display: flex; align-items: center; justify-content: center; cursor: grab;">
      <!-- Pulsing radar ring -->
      <div style="position: absolute; width: 46px; height: 46px; border-radius: 50%; background: rgba(245, 158, 11, 0.4); animation: ping 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
      <!-- Vision pointer -->
      <div style="position: absolute; top: -10px; width: 0; height: 0; border-left: 7px solid transparent; border-right: 7px solid transparent; border-bottom: 11px solid #fbbf24; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.5));"></div>
      <!-- Pegman Body -->
      <div style="width: 34px; height: 34px; border-radius: 50%; background: linear-gradient(135deg, #f59e0b, #d97706); border: 2.5px solid #ffffff; box-shadow: 0 4px 14px rgba(245, 158, 11, 0.8); display: flex; align-items: center; justify-content: center; color: white;">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="2"/><path d="m9 20 3-6 3 6"/><path d="m6 8 6 2 6-2"/><path d="M12 10v4"/></svg>
      </div>
      <!-- Badge label -->
      <div style="position: absolute; bottom: -18px; background: rgba(15, 23, 42, 0.95); color: #fbbf24; font-size: 9px; font-weight: 800; padding: 1px 6px; border-radius: 4px; border: 1px solid rgba(245, 158, 11, 0.6); white-space: nowrap; pointer-events: none; box-shadow: 0 2px 6px rgba(0,0,0,0.6); letter-spacing: 0.5px;">
        STREET VIEW
      </div>
    </div>
  `,
  iconSize: [46, 46],
  iconAnchor: [23, 23],
  popupAnchor: [0, -26],
});

// User GPS Geolocation icon
const userLocationIcon = L.divIcon({
  className: 'custom-user-location-marker',
  html: `
    <div style="position: relative; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">
      <div style="position: absolute; width: 36px; height: 36px; border-radius: 50%; background: rgba(59, 130, 246, 0.45); animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
      <div style="width: 20px; height: 20px; border-radius: 50%; background: #2563eb; border: 3px solid #ffffff; box-shadow: 0 2px 10px rgba(37,99,235,0.7); display: flex; align-items: center; justify-content: center;">
        <div style="width: 6px; height: 6px; border-radius: 50%; background: #ffffff;"></div>
      </div>
      <div style="position: absolute; bottom: -16px; background: rgba(15, 23, 42, 0.9); color: #60a5fa; font-size: 8px; font-weight: 700; padding: 1px 5px; border-radius: 4px; border: 1px solid rgba(59, 130, 246, 0.4); white-space: nowrap; pointer-events: none;">
        YOU
      </div>
    </div>
  `,
  iconSize: [36, 36],
  iconAnchor: [18, 18],
  popupAnchor: [0, -20],
});

// Helper component to center map smoothly
const MapController: React.FC<{ center: [number, number]; zoom?: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.flyTo(center, zoom || map.getZoom(), { duration: 1.0 });
    }
  }, [center, zoom, map]);
  return null;
};

// Click handler to place a report pin or open street view
const MapClickHandler: React.FC<{
  isReporting: boolean;
  isStreetView: boolean;
  onMapClick: (lat: number, lng: number) => void;
  onStreetViewClick: (lat: number, lng: number) => void;
}> = ({ isReporting, isStreetView, onMapClick, onStreetViewClick }) => {
  useMapEvents({
    click: (e) => {
      if (isStreetView) {
        onStreetViewClick(e.latlng.lat, e.latlng.lng);
      } else if (isReporting) {
        onMapClick(e.latlng.lat, e.latlng.lng);
      }
    },
  });
  return null;
};

export const MapView: React.FC<MapViewProps> = ({
  hazards,
  robots,
  selectedHazard,
  onSelectHazard,
  onUpdateStatus,
  onDeleteHazard,
  onReportHazard,
  userRole,
}) => {
  const [showDensityHeat, setShowDensityHeat] = useState(false);
  const [isReporting, setIsReporting] = useState(false);
  const [reportPin, setReportPin] = useState<[number, number] | null>(null);
  const [reportClass, setReportClass] = useState<string>('pothole');
  const [reportDescription, setReportDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [searchZoom, setSearchZoom] = useState<number | undefined>(undefined);
  const [mapLayer, setMapLayer] = useState<'default' | 'satellite' | 'terrain'>('default');
  const [isStreetView, setIsStreetView] = useState(false);
  const [streetViewCoords, setStreetViewCoords] = useState<[number, number] | null>(null);
  const [reportPhoto, setReportPhoto] = useState<string | null>(null);
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null);
  const [locating, setLocating] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const activeRobot = robots.find((r) => r.is_online) || robots[0];

  const isAdmin = userRole === 'admin';

  // Default coordinate center (fallback to campus center)
  const defaultCenter: [number, number] = [
    activeRobot?.current_latitude || hazards[0]?.latitude || 12.9725,
    activeRobot?.current_longitude || hazards[0]?.longitude || 77.5947,
  ];

  const [mapCenter, setMapCenter] = useState<[number, number]>(defaultCenter);

  useEffect(() => {
    if (selectedHazard) {
      setMapCenter([selectedHazard.latitude, selectedHazard.longitude]);
    }
  }, [selectedHazard]);

  const handleMapClick = (lat: number, lng: number) => {
    setReportPin([lat, lng]);
  };

  const handleFileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const handlePhotoSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      alert('Photo must be under 5MB');
      return;
    }
    const base64 = await handleFileToBase64(file);
    setReportPhoto(base64);
  };

  const startCamera = useCallback(async () => {
    setShowCamera(true);
    setCameraReady(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current?.play();
          setCameraReady(true);
        };
      }
    } catch (err) {
      console.error('Camera error:', err);
      alert('Could not access camera. Please check permissions.');
      setShowCamera(false);
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setShowCamera(false);
    setCameraReady(false);
  }, []);

  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    setReportPhoto(dataUrl);
    stopCamera();
  }, [stopCamera]);

  const handleSubmitReport = async () => {
    if (!reportPin) return;
    setSubmitting(true);
    await onReportHazard(reportPin[0], reportPin[1], reportClass, reportDescription || undefined, reportPhoto || undefined);
    setSubmitting(false);
    setReportPin(null);
    setReportDescription('');
    setReportPhoto(null);
    setIsReporting(false);
  };

  const handleCancelReport = () => {
    setReportPin(null);
    setReportDescription('');
    setReportPhoto(null);
    setIsReporting(false);
  };

  const handleSearchLocation = (lat: number, lng: number, _label: string) => {
    setMapCenter([lat, lng]);
    setSearchZoom(16);
  };

  const handleLocateMe = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords: [number, number] = [pos.coords.latitude, pos.coords.longitude];
        setUserLocation(coords);
        setMapCenter(coords);
        setSearchZoom(18);
        setLocating(false);
        if (isStreetView) {
          setStreetViewCoords(coords);
        }
      },
      (err) => {
        console.warn('Geolocation error:', err);
        alert('Could not access your location. Please check browser location permissions.');
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  return (
    <div className="glass-panel relative h-[560px] w-full rounded-2xl overflow-hidden border border-slate-800 shadow-2xl">
      {/* Hidden canvas for camera capture */}
      <canvas ref={canvasRef} className="hidden" />

      {/* Live Camera Overlay */}
      {showCamera && (
        <div className="absolute inset-0 z-[900] bg-black/95 flex flex-col items-center justify-center">
          <div className="relative w-full max-w-md">
            <div className="text-center mb-3">
              <span className="text-xs font-bold text-white flex items-center justify-center gap-2">
                <Camera className="h-4 w-4 text-cyan-400" />
                {cameraReady ? 'Camera Ready – Position the hazard and capture' : 'Starting camera...'}
              </span>
            </div>
            <div className="relative rounded-xl overflow-hidden border-2 border-cyan-500/40 shadow-2xl shadow-cyan-500/10">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full aspect-video object-cover bg-slate-900"
              />
              {/* Viewfinder crosshair */}
              {cameraReady && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-16 h-16 border-2 border-white/30 rounded-lg" />
                </div>
              )}
              {!cameraReady && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
                </div>
              )}
            </div>
            <div className="flex items-center justify-center gap-4 mt-4">
              <button
                onClick={stopCamera}
                className="flex items-center gap-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 px-5 py-2.5 text-xs font-semibold text-slate-300 border border-slate-600 transition-all"
              >
                <X className="h-4 w-4" />
                Cancel
              </button>
              <button
                onClick={capturePhoto}
                disabled={!cameraReady}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 px-6 py-2.5 text-xs font-bold text-white shadow-lg shadow-cyan-600/30 transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Camera className="h-4 w-4" />
                Capture Photo
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Location Search Bar */}
      <div className="absolute top-4 left-4 z-[600]">
        <LocationSearch onLocationSelect={handleSearchLocation} />
      </div>

      {/* Top Map Action Toolbar */}
      <div className="absolute top-4 right-4 z-[500] flex items-center gap-2">
        {/* Report Pothole Toggle */}
        <button
          onClick={() => {
            if (isReporting) {
              handleCancelReport();
            } else {
              setIsReporting(true);
            }
          }}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold backdrop-blur-md shadow-md border transition-all ${
            isReporting
              ? 'bg-purple-500/30 text-purple-300 border-purple-500/50 ring-2 ring-purple-500/30'
              : 'bg-purple-600/80 text-white border-purple-500/40 hover:bg-purple-500'
          }`}
        >
          {isReporting ? (
            <>
              <X className="h-3.5 w-3.5" />
              <span>Cancel Report</span>
            </>
          ) : (
            <>
              <Plus className="h-3.5 w-3.5" />
              <span>Report Pothole</span>
            </>
          )}
        </button>

        <button
          onClick={() => setShowDensityHeat(!showDensityHeat)}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold backdrop-blur-md shadow-md border transition-all ${
            showDensityHeat
              ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
              : 'bg-slate-900/80 text-slate-300 border-slate-700/80 hover:bg-slate-800'
          }`}
        >
          <Layers className="h-3.5 w-3.5" />
          <span>{showDensityHeat ? 'Heatmap: ON' : 'Hazard Cones'}</span>
        </button>

        {activeRobot?.current_latitude && activeRobot?.current_longitude && (
          <button
            onClick={() => setMapCenter([activeRobot.current_latitude!, activeRobot.current_longitude!])}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600/80 hover:bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur-md shadow-md border border-blue-400/30 transition-all"
          >
            <Navigation className="h-3.5 w-3.5" />
            <span>Center Robot</span>
          </button>
        )}

        {/* Geolocation / My Location Button */}
        <button
          onClick={handleLocateMe}
          disabled={locating}
          className="flex items-center gap-1.5 rounded-lg bg-slate-900/80 hover:bg-slate-800 px-3 py-1.5 text-xs font-semibold text-cyan-300 border border-cyan-500/40 backdrop-blur-md shadow-md transition-all active:scale-95 disabled:opacity-50"
          title="Find my real GPS location"
        >
          <LocateFixed className={`h-3.5 w-3.5 ${locating ? 'animate-spin text-cyan-400' : 'text-cyan-400'}`} />
          <span>{locating ? 'Locating...' : 'My Location'}</span>
        </button>

        {/* Street View Toggle */}
        <button
          onClick={() => {
            if (isStreetView) {
              setIsStreetView(false);
              setStreetViewCoords(null);
            } else {
              setIsStreetView(true);
              setIsReporting(false);
              setReportPin(null);
            }
          }}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold backdrop-blur-md shadow-md border transition-all ${
            isStreetView
              ? 'bg-amber-500/30 text-amber-300 border-amber-500/50 ring-2 ring-amber-500/30'
              : 'bg-slate-900/80 text-slate-300 border-slate-700/80 hover:bg-slate-800'
          }`}
        >
          <PersonStanding className="h-3.5 w-3.5" />
          <span>{isStreetView ? 'Exit Street View' : 'Street View'}</span>
        </button>
      </div>

      {/* Reporting Mode Banner */}
      {isReporting && !reportPin && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-[500] bg-purple-600/90 text-white px-5 py-2.5 rounded-xl text-xs font-semibold backdrop-blur-md shadow-xl border border-purple-400/30 flex items-center gap-2 animate-bounce">
          <MapPin className="h-4 w-4" />
          Click on the map to mark the pothole location
        </div>
      )}

      {/* Street View Mode Banner */}
      {isStreetView && !streetViewCoords && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-[500] bg-amber-600/90 text-white px-5 py-2.5 rounded-xl text-xs font-semibold backdrop-blur-md shadow-xl border border-amber-400/30 flex items-center gap-2 animate-bounce">
          <PersonStanding className="h-4 w-4" />
          Click anywhere on the map to explore Street View
        </div>
      )}

      {/* Embedded Street View Panel */}
      {streetViewCoords && (
        <div className="absolute top-4 left-4 z-[700] w-[420px] rounded-2xl overflow-hidden border border-amber-500/40 shadow-2xl bg-slate-950/95 backdrop-blur-xl">
          <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800 bg-slate-900/80">
            <div className="flex items-center gap-2">
              <PersonStanding className="h-4 w-4 text-amber-400" />
              <span className="text-xs font-bold text-white">Street View</span>
              <span className="text-[10px] font-mono text-slate-400">
                {streetViewCoords[0].toFixed(5)}, {streetViewCoords[1].toFixed(5)}
              </span>
            </div>
            <button
              onClick={() => setStreetViewCoords(null)}
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            >
              <Minimize2 className="h-4 w-4" />
            </button>
          </div>
          <iframe
            className="w-full h-[280px] border-0"
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            src={`https://www.google.com/maps?q=&layer=c&cbll=${streetViewCoords[0]},${streetViewCoords[1]}&cbp=11,0,0,0,0&output=svembed&z=17`}
            allowFullScreen
          />

          {/* Report from Street View */}
          <div className="px-3 py-2.5 border-t border-slate-800 bg-slate-900/60">
            <div className="flex items-center gap-1.5 mb-2">
              <ShieldAlert className="h-3.5 w-3.5 text-purple-400" />
              <span className="text-[11px] font-bold text-white">Report Hazard at This Location</span>
            </div>
            <div className="flex gap-1.5 mb-2">
              {['pothole', 'crack', 'animal'].map((cls) => (
                <button
                  key={cls}
                  onClick={() => setReportClass(cls)}
                  className={`flex-1 rounded-lg py-1.5 text-[10px] font-bold uppercase transition-all border ${
                    reportClass === cls
                      ? cls === 'pothole'
                        ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                        : cls === 'crack'
                        ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                        : 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
                      : 'bg-slate-900 text-slate-400 border-slate-700 hover:border-slate-600'
                  }`}
                >
                  {cls}
                </button>
              ))}
            </div>
            {/* Photo upload in street view */}
            <div className="mb-2">
              {reportPhoto ? (
                <div className="relative rounded-lg overflow-hidden border border-purple-500/30 bg-slate-900">
                  <img src={reportPhoto} alt="Preview" className="w-full h-16 object-cover" />
                  <button
                    onClick={() => setReportPhoto(null)}
                    className="absolute top-1 right-1 rounded-full bg-black/70 p-0.5 text-white hover:bg-rose-600 transition-colors"
                  >
                    <X className="h-2.5 w-2.5" />
                  </button>
                </div>
              ) : (
                <div className="flex gap-1.5">
                  <label className="flex-1 flex items-center justify-center gap-1 rounded-lg py-1.5 border border-dashed border-slate-600 bg-slate-900/50 text-slate-400 hover:border-purple-500 hover:text-purple-400 cursor-pointer transition-all text-[10px]">
                    <ImageIcon className="h-3 w-3" />
                    <span>Photo</span>
                    <input type="file" accept="image/*" className="hidden" onChange={handlePhotoSelect} />
                  </label>
                  <button
                    onClick={startCamera}
                    className="flex items-center justify-center gap-1 rounded-lg py-1.5 px-2 border border-dashed border-slate-600 bg-slate-900/50 text-slate-400 hover:border-cyan-500 hover:text-cyan-400 transition-all text-[10px]"
                  >
                    <Camera className="h-3 w-3" />
                    <span>Camera</span>
                  </button>
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={reportDescription}
                onChange={(e) => setReportDescription(e.target.value)}
                placeholder="Description (optional)..."
                className="flex-1 rounded-lg bg-slate-900/80 border border-slate-700 px-2.5 py-1.5 text-[11px] text-white placeholder-slate-600 focus:outline-none focus:border-purple-500 transition-all min-w-0"
              />
              <button
                onClick={async () => {
                  if (!streetViewCoords) return;
                  setSubmitting(true);
                  await onReportHazard(streetViewCoords[0], streetViewCoords[1], reportClass, reportDescription || undefined, reportPhoto || undefined);
                  setSubmitting(false);
                  setReportDescription('');
                  setReportPhoto(null);
                }}
                disabled={submitting}
                className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-500 hover:to-violet-500 px-3 py-1.5 text-[11px] font-bold text-white shadow-lg shadow-purple-600/20 transition-all active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                {submitting ? (
                  <div className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                ) : (
                  <Send className="h-3 w-3" />
                )}
                <span>{submitting ? 'Sending...' : 'Report'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Report Form Panel */}
      {reportPin && (
        <div className="absolute top-16 left-4 z-[500] w-72 bg-slate-950/95 rounded-2xl border border-purple-500/40 p-4 shadow-2xl backdrop-blur-xl">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <MapPin className="h-4 w-4 text-purple-400" />
              Report Hazard
            </h3>
            <button
              onClick={handleCancelReport}
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Location */}
          <div className="bg-slate-900/80 rounded-lg p-2.5 mb-3 border border-slate-800">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-0.5">Location</div>
            <div className="font-mono text-xs text-purple-300">
              {reportPin[0].toFixed(6)}, {reportPin[1].toFixed(6)}
            </div>
          </div>

          {/* Hazard Class Selection */}
          <div className="mb-3">
            <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1.5">Hazard Type</label>
            <div className="flex gap-1.5">
              {['pothole', 'crack', 'animal'].map((cls) => (
                <button
                  key={cls}
                  onClick={() => setReportClass(cls)}
                  className={`flex-1 rounded-lg py-1.5 text-[11px] font-bold uppercase transition-all border ${
                    reportClass === cls
                      ? cls === 'pothole'
                        ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                        : cls === 'crack'
                        ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                        : 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
                      : 'bg-slate-900 text-slate-400 border-slate-700 hover:border-slate-600'
                  }`}
                >
                  {cls}
                </button>
              ))}
            </div>
          </div>

          {/* Photo Upload */}
          <div className="mb-3">
            <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1.5">Photo Evidence</label>
            {reportPhoto ? (
              <div className="relative rounded-lg overflow-hidden border border-purple-500/30 bg-slate-900">
                <img src={reportPhoto} alt="Preview" className="w-full h-24 object-cover" />
                <button
                  onClick={() => setReportPhoto(null)}
                  className="absolute top-1 right-1 rounded-full bg-black/70 p-1 text-white hover:bg-rose-600 transition-colors"
                >
                  <X className="h-3 w-3" />
                </button>
                <div className="absolute bottom-1 left-1 rounded bg-black/70 px-1.5 py-0.5 text-[9px] text-emerald-400 font-semibold">
                  ✓ Photo attached
                </div>
              </div>
            ) : (
              <div className="flex gap-1.5">
                <label className="flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2 border border-dashed border-slate-600 bg-slate-900/50 text-slate-400 hover:border-purple-500 hover:text-purple-400 cursor-pointer transition-all text-[11px]">
                  <ImageIcon className="h-3.5 w-3.5" />
                  <span>Upload Photo</span>
                  <input type="file" accept="image/*" className="hidden" onChange={handlePhotoSelect} />
                </label>
                <button
                  onClick={startCamera}
                  className="flex items-center justify-center gap-1.5 rounded-lg py-2 px-3 border border-dashed border-slate-600 bg-slate-900/50 text-slate-400 hover:border-cyan-500 hover:text-cyan-400 transition-all text-[11px]"
                >
                  <Camera className="h-3.5 w-3.5" />
                  <span>Camera</span>
                </button>
              </div>
            )}
          </div>

          {/* Description */}
          <div className="mb-3">
            <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1.5">Description (optional)</label>
            <textarea
              value={reportDescription}
              onChange={(e) => setReportDescription(e.target.value)}
              placeholder="e.g., Large pothole near bus stop..."
              rows={2}
              className="w-full rounded-lg bg-slate-900/80 border border-slate-700 px-3 py-2 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/50 resize-none transition-all"
            />
          </div>

          {/* Submit */}
          <button
            onClick={handleSubmitReport}
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-500 hover:to-violet-500 py-2.5 text-xs font-bold text-white shadow-lg shadow-purple-600/25 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <>
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                <span>Submitting...</span>
              </>
            ) : (
              <>
                <Send className="h-3.5 w-3.5" />
                <span>Submit Report</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Map Legend */}
      <div className="absolute bottom-4 left-4 z-[500] flex items-center gap-3 rounded-xl bg-slate-950/85 px-3.5 py-2 text-xs border border-slate-800/80 backdrop-blur-md shadow-lg">
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-rose-500"></span>
          <span className="text-slate-300">Pothole</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-amber-500"></span>
          <span className="text-slate-300">Crack</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-cyan-400"></span>
          <span className="text-slate-300">Animal</span>
        </div>
        <div className="flex items-center gap-1.5 border-l border-slate-800 pl-2">
          <span className="h-2.5 w-2.5 rounded-full bg-purple-500"></span>
          <span className="text-slate-300">User Report</span>
        </div>
        <div className="flex items-center gap-1.5 border-l border-slate-800 pl-2">
          <span className="h-2.5 w-2.5 rounded-sm bg-blue-500"></span>
          <span className="text-slate-300">Robot Live</span>
        </div>
      </div>

      {/* Map Type Switcher – bottom right */}
      <div className="absolute bottom-4 right-4 z-[500] flex items-center rounded-xl bg-slate-950/90 border border-slate-700/60 backdrop-blur-xl shadow-xl overflow-hidden">
        {[
          { id: 'default' as const, label: 'Default', icon: Map },
          { id: 'satellite' as const, label: 'Satellite', icon: Satellite },
          { id: 'terrain' as const, label: 'Terrain', icon: Mountain },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setMapLayer(id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-[11px] font-semibold transition-all ${
              mapLayer === id
                ? 'bg-cyan-500/20 text-cyan-300 shadow-inner'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      <MapContainer
        center={defaultCenter}
        zoom={17}
        maxZoom={21}
        scrollWheelZoom={true}
        className={`h-full w-full ${isReporting ? 'cursor-crosshair' : ''} ${isStreetView ? 'cursor-pointer' : ''}`}
      >
        <MapController center={mapCenter} zoom={searchZoom} />
        <MapClickHandler
          isReporting={isReporting}
          isStreetView={isStreetView}
          onMapClick={handleMapClick}
          onStreetViewClick={(lat, lng) => setStreetViewCoords([lat, lng])}
        />

        {/* Map Tiles – switch based on selected layer, with extended zoom */}
        {mapLayer === 'default' && (
          <TileLayer
            key="default"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxNativeZoom={19}
            maxZoom={21}
          />
        )}
        {mapLayer === 'satellite' && (
          <TileLayer
            key="satellite"
            attribution='Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            maxNativeZoom={19}
            maxZoom={21}
          />
        )}
        {mapLayer === 'terrain' && (
          <TileLayer
            key="terrain"
            attribution='Map data &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)'
            url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
            maxNativeZoom={17}
            maxZoom={21}
          />
        )}

        {/* Hazard Density / Heatmap Circles */}
        {showDensityHeat &&
          hazards.map((h) => (
            <Circle
              key={`heat-${h.id}`}
              center={[h.latitude, h.longitude]}
              radius={18}
              pathOptions={{
                fillColor: h.hazard_class === 'pothole' ? '#ef4444' : h.hazard_class === 'crack' ? '#f59e0b' : '#06b6d4',
                fillOpacity: 0.25,
                color: 'transparent',
              }}
            />
          ))}

        {/* Hazard Markers */}
        {hazards.map((h) => (
          <Marker
            key={h.id}
            position={[h.latitude, h.longitude]}
            icon={createHazardIcon(h.hazard_class, h.severity_score, !!h.reported_by)}
            eventHandlers={{
              click: () => onSelectHazard(h),
            }}
          >
            <Popup className="roadbot-popup">
              <div className="p-1 min-w-[220px]">
                {h.snapshot_url && (
                  <div className="relative mb-2.5 overflow-hidden rounded-lg border border-slate-700 aspect-video bg-slate-900">
                    <img
                      src={h.snapshot_url}
                      alt={h.hazard_class}
                      className="h-full w-full object-cover"
                    />
                    <span className="absolute bottom-1 right-1 rounded bg-black/80 px-1.5 py-0.5 text-[9px] font-mono text-white">
                      {h.reported_by ? 'User Report' : 'YOLOv8'}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-white">
                    {h.hazard_class}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      h.severity_score >= 75
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    Severity: {h.severity_score}
                  </span>
                </div>
                {h.reported_by && (
                  <div className="text-[11px] text-purple-400 mt-1 flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-purple-400"></span>
                    Reported by <span className="font-semibold">{h.reported_by}</span>
                  </div>
                )}
                <div className="text-[11px] text-slate-400 mt-1">
                  Confidence: <span className="text-white font-medium">{(h.confidence * 100).toFixed(1)}%</span>
                  {h.cluster_count > 1 && (
                    <span className="ml-2 text-cyan-400 font-semibold">({h.cluster_count} sightings)</span>
                  )}
                </div>
                <div className="text-[10px] font-mono text-slate-400 mt-1">
                  {h.latitude.toFixed(6)}, {h.longitude.toFixed(6)}
                </div>
                <div className="mt-2.5 flex items-center gap-1.5 border-t border-slate-800 pt-2">
                  <button
                    onClick={() => onUpdateStatus(h.id, 'acknowledged')}
                    className={`flex-1 rounded px-2 py-1 text-[10px] font-medium transition-all ${
                      h.status === 'acknowledged'
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    Acknowledge
                  </button>
                  {isAdmin && (
                    <button
                      onClick={() => onUpdateStatus(h.id, 'repaired')}
                      className={`flex-1 rounded px-2 py-1 text-[10px] font-medium transition-all ${
                        h.status === 'repaired'
                          ? 'bg-emerald-600 text-white'
                          : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      Repaired
                    </button>
                  )}
                  {isAdmin && (
                    <button
                      onClick={() => {
                        if (window.confirm(`Delete hazard #${h.id} as fake/invalid?`)) {
                          onDeleteHazard(h.id);
                        }
                      }}
                      className="rounded px-2 py-1 text-[10px] font-medium bg-rose-500/20 text-rose-400 hover:bg-rose-500 hover:text-white transition-all"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Report Pin Marker */}
        {reportPin && (
          <Marker
            position={reportPin}
            icon={reportPinIcon}
          />
        )}

        {/* Active Robot Markers */}
        {robots.map((r) => {
          if (!r.current_latitude || !r.current_longitude) return null;
          return (
            <Marker
              key={r.robot_id}
              position={[r.current_latitude, r.current_longitude]}
              icon={robotIcon}
            >
              <Popup>
                <div className="p-1">
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    {r.robot_id} (Active Patrol)
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Battery: <span className="text-emerald-400 font-bold">{r.battery_percentage}%</span> | Speed: {r.speed} m/s
                  </div>
                  <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                    GPS: {r.current_latitude.toFixed(6)}, {r.current_longitude.toFixed(6)}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* User GPS Geolocation Pin */}
        {userLocation && (
          <Marker position={userLocation} icon={userLocationIcon}>
            <Popup className="roadbot-popup">
              <div className="p-1">
                <div className="text-xs font-bold text-blue-400 flex items-center gap-1.5">
                  <LocateFixed className="h-3.5 w-3.5" />
                  Your Current GPS Location
                </div>
                <div className="text-[10px] font-mono text-slate-300 mt-1">
                  {userLocation[0].toFixed(6)}, {userLocation[1].toFixed(6)}
                </div>
                <button
                  onClick={() => setStreetViewCoords(userLocation)}
                  className="mt-2 w-full flex items-center justify-center gap-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 py-1 text-[10px] font-bold hover:bg-amber-500/30 transition-all"
                >
                  <PersonStanding className="h-3 w-3" />
                  View Street View Here
                </button>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Street View "Where Are We" Pegman Marker */}
        {streetViewCoords && (
          <>
            <Circle
              center={streetViewCoords}
              radius={24}
              pathOptions={{
                fillColor: '#f59e0b',
                fillOpacity: 0.2,
                color: '#fbbf24',
                weight: 2,
                dashArray: '4, 4',
              }}
            />
            <Marker
              position={streetViewCoords}
              icon={streetViewPegmanIcon}
              draggable={true}
              eventHandlers={{
                dragend: (e) => {
                  const marker = e.target;
                  const pos = marker.getLatLng();
                  setStreetViewCoords([pos.lat, pos.lng]);
                },
              }}
            >
              <Popup className="roadbot-popup">
                <div className="p-1 min-w-[210px]">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400">
                    <PersonStanding className="h-4 w-4" />
                    You Are Here in Street View
                  </div>
                  <div className="text-[10px] font-mono text-slate-300 mt-1">
                    {streetViewCoords[0].toFixed(6)}, {streetViewCoords[1].toFixed(6)}
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1.5 leading-snug">
                    📍 <strong>Drag this Pegman icon</strong> along any road to instantly update the Street View panorama!
                  </p>
                  <div className="mt-2 pt-1.5 border-t border-slate-800 flex gap-1">
                    <button
                      onClick={() => setMapCenter(streetViewCoords)}
                      className="flex-1 rounded bg-slate-800 hover:bg-slate-700 py-1 text-[10px] font-semibold text-slate-300 transition-colors"
                    >
                      Center
                    </button>
                    <button
                      onClick={() => setStreetViewCoords(null)}
                      className="rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 px-2 py-1 text-[10px] font-semibold transition-colors"
                    >
                      Close View
                    </button>
                  </div>
                </div>
              </Popup>
            </Marker>
          </>
        )}
      </MapContainer>
    </div>
  );
};
