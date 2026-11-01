import React, { useState, useRef, useCallback } from 'react';
import { X, MapPin, Calendar, Bot, Shield, CheckCircle2, Clock, AlertTriangle, Trash2, Camera, ImageIcon, Upload } from 'lucide-react';
import { Hazard } from '../types';
import { api } from '../api/client';

interface HazardModalProps {
  hazard: Hazard | null;
  onClose: () => void;
  onUpdateStatus: (id: number, status: 'new' | 'acknowledged' | 'repaired') => void;
  onDeleteHazard: (id: number) => void;
  userRole: string;
}

export const HazardModal: React.FC<HazardModalProps> = ({
  hazard,
  onClose,
  onUpdateStatus,
  onDeleteHazard,
  userRole,
}) => {
  const [repairPhoto, setRepairPhoto] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [showRepairFlow, setShowRepairFlow] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  if (!hazard) return null;

  const isCritical = hazard.severity_score >= 75;
  const isAdmin = userRole === 'admin';
  const isRepaired = hazard.status === 'repaired';

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
    setRepairPhoto(base64);
  };

  const startCamera = async () => {
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
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setShowCamera(false);
    setCameraReady(false);
  };

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    setRepairPhoto(dataUrl);
    stopCamera();
  };

  /** Upload repair photo for an already-repaired hazard */
  const handleUploadRepairPhoto = async () => {
    if (!repairPhoto) return;
    setUploading(true);
    try {
      await api.uploadRepairPhoto(hazard.id, repairPhoto);
      setRepairPhoto(null);
      // The WebSocket HAZARD_UPDATED event will refresh the hazard data
    } catch (err: any) {
      alert(err.message || 'Failed to upload repair photo');
    }
    setUploading(false);
  };

  /** Mark as repaired + upload repair photo in one flow */
  const handleMarkRepairedWithPhoto = async () => {
    if (!repairPhoto) return;
    setUploading(true);
    try {
      // Step 1: Mark hazard as repaired
      onUpdateStatus(hazard.id, 'repaired');
      // Step 2: Upload repair photo (small delay to let status update propagate)
      await new Promise((resolve) => setTimeout(resolve, 500));
      await api.uploadRepairPhoto(hazard.id, repairPhoto);
      setRepairPhoto(null);
      setShowRepairFlow(false);
      onClose();
    } catch (err: any) {
      alert(err.message || 'Failed to upload repair photo');
    }
    setUploading(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="glass-panel relative w-full max-w-xl rounded-2xl border border-slate-700/80 p-6 shadow-2xl bg-slate-950/95 overflow-hidden max-h-[90vh] overflow-y-auto">
        {/* Hidden canvas for camera */}
        <canvas ref={canvasRef} className="hidden" />

        {/* Camera Overlay */}
        {showCamera && (
          <div className="absolute inset-0 z-[60] bg-black/95 flex flex-col items-center justify-center p-6 rounded-2xl">
            <div className="w-full max-w-sm">
              <div className="text-center mb-3">
                <span className="text-xs font-bold text-white flex items-center justify-center gap-2">
                  <Camera className="h-4 w-4 text-cyan-400" />
                  {cameraReady ? 'Capture the repaired area' : 'Starting camera...'}
                </span>
              </div>
              <div className="relative rounded-xl overflow-hidden border-2 border-cyan-500/40">
                <video ref={videoRef} autoPlay playsInline muted className="w-full aspect-video object-cover bg-slate-900" />
                {!cameraReady && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
                  </div>
                )}
              </div>
              <div className="flex items-center justify-center gap-3 mt-4">
                <button onClick={stopCamera} className="flex items-center gap-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 border border-slate-600 transition-all">
                  <X className="h-3.5 w-3.5" /> Cancel
                </button>
                <button onClick={capturePhoto} disabled={!cameraReady} className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 px-5 py-2 text-xs font-bold text-white shadow-lg transition-all active:scale-95 disabled:opacity-40">
                  <Camera className="h-3.5 w-3.5" /> Capture
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <span
              className={`rounded-lg px-2.5 py-1 text-xs font-bold uppercase tracking-wider ${
                hazard.hazard_class === 'pothole'
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  : hazard.hazard_class === 'crack'
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
              }`}
            >
              {hazard.hazard_class}
            </span>
            <span className="font-mono text-xs text-slate-400">Hazard #{hazard.id}</span>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Snapshot Image */}
        <div className="my-4 relative rounded-xl overflow-hidden border border-slate-800 bg-slate-900 aspect-video flex items-center justify-center">
          {hazard.snapshot_url ? (
            <img
              src={hazard.snapshot_url}
              alt={hazard.hazard_class}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="text-center text-xs text-slate-500">
              <AlertTriangle className="h-8 w-8 mx-auto mb-1 text-slate-600" />
              Snapshot preview unavailable
            </div>
          )}
          <span className="absolute bottom-2 left-2 rounded-md bg-black/70 px-2 py-0.5 text-[10px] font-mono text-cyan-400 border border-cyan-500/30">
            {hazard.reported_by ? 'User Report' : 'YOLOv8 Edge Frame'}
          </span>
        </div>

        {/* Repair Photo Section — for already-repaired hazards */}
        {isRepaired && (
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Repair Evidence</span>
            </div>

            {hazard.repair_snapshot_url ? (
              <div className="rounded-xl overflow-hidden border border-emerald-500/30 bg-slate-900">
                <img
                  src={hazard.repair_snapshot_url}
                  alt="Repaired area"
                  className="w-full h-40 object-cover"
                />
                <div className="px-3 py-1.5 bg-emerald-500/10 border-t border-emerald-500/20">
                  <span className="text-[10px] font-semibold text-emerald-400">✓ Repair photo verified</span>
                </div>
              </div>
            ) : isAdmin ? (
              /* Admin can upload repair photo after the fact */
              <div className="rounded-xl border border-dashed border-emerald-500/30 bg-slate-900/50 p-3">
                {repairPhoto ? (
                  <div className="space-y-2">
                    <div className="relative rounded-lg overflow-hidden border border-emerald-500/30">
                      <img src={repairPhoto} alt="Repair preview" className="w-full h-32 object-cover" />
                      <button
                        onClick={() => setRepairPhoto(null)}
                        className="absolute top-1 right-1 rounded-full bg-black/70 p-1 text-white hover:bg-rose-600 transition-colors"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                    <button
                      onClick={handleUploadRepairPhoto}
                      disabled={uploading}
                      className="w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 py-2 text-xs font-bold text-white shadow-lg shadow-emerald-600/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {uploading ? (
                        <>
                          <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                          <span>Uploading...</span>
                        </>
                      ) : (
                        <>
                          <Upload className="h-3.5 w-3.5" />
                          <span>Upload Repair Photo</span>
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <div>
                    <p className="text-[11px] text-slate-400 mb-2">Upload a photo of the repaired area as proof</p>
                    <div className="flex gap-2">
                      <label className="flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2.5 border border-dashed border-slate-600 bg-slate-900/60 text-slate-400 hover:border-emerald-500 hover:text-emerald-400 cursor-pointer transition-all text-[11px]">
                        <ImageIcon className="h-3.5 w-3.5" />
                        <span>Upload Photo</span>
                        <input type="file" accept="image/*" className="hidden" onChange={handlePhotoSelect} />
                      </label>
                      <button
                        onClick={startCamera}
                        className="flex items-center justify-center gap-1.5 rounded-lg py-2.5 px-4 border border-dashed border-slate-600 bg-slate-900/60 text-slate-400 hover:border-cyan-500 hover:text-cyan-400 transition-all text-[11px]"
                      >
                        <Camera className="h-3.5 w-3.5" />
                        <span>Camera</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/50 p-3 text-center">
                <span className="text-[11px] text-slate-500">No repair photo uploaded yet</span>
              </div>
            )}
          </div>
        )}

        {/* Repair Photo Flow — shown when admin clicks "Mark Repaired" on a non-repaired hazard */}
        {showRepairFlow && !isRepaired && (
          <div className="mb-4 rounded-2xl border-2 border-emerald-500/40 bg-emerald-500/5 p-4 animate-fade-in">
            <div className="flex items-center gap-2 mb-3">
              <Camera className="h-4 w-4 text-emerald-400" />
              <span className="text-sm font-bold text-emerald-400">Repair Photo Required</span>
            </div>
            <p className="text-[11px] text-slate-400 mb-3">
              Take a photo or upload an image of the repaired area as proof before marking this hazard as repaired.
            </p>

            {repairPhoto ? (
              <div className="space-y-3">
                <div className="relative rounded-xl overflow-hidden border border-emerald-500/30 bg-slate-900">
                  <img src={repairPhoto} alt="Repair preview" className="w-full h-40 object-cover" />
                  <button
                    onClick={() => setRepairPhoto(null)}
                    className="absolute top-2 right-2 rounded-full bg-black/70 p-1.5 text-white hover:bg-rose-600 transition-colors"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                  <div className="absolute bottom-2 left-2 rounded-md bg-black/70 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/30">
                    ✓ Photo ready
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setShowRepairFlow(false);
                      setRepairPhoto(null);
                    }}
                    className="flex-1 flex items-center justify-center gap-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 py-2.5 text-xs font-semibold text-slate-300 border border-slate-600 transition-all"
                  >
                    <X className="h-3.5 w-3.5" />
                    <span>Cancel</span>
                  </button>
                  <button
                    onClick={handleMarkRepairedWithPhoto}
                    disabled={uploading}
                    className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 py-2.5 text-xs font-bold text-white shadow-lg shadow-emerald-600/25 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {uploading ? (
                      <>
                        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                        <span>Updating...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Confirm Repaired</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex gap-2">
                  <label className="flex-1 flex items-center justify-center gap-2 rounded-xl py-3 border-2 border-dashed border-slate-600 bg-slate-900/60 text-slate-400 hover:border-emerald-500 hover:text-emerald-400 hover:bg-emerald-500/5 cursor-pointer transition-all text-xs font-semibold">
                    <ImageIcon className="h-4 w-4" />
                    <span>Upload Photo</span>
                    <input type="file" accept="image/*" className="hidden" onChange={handlePhotoSelect} />
                  </label>
                  <button
                    onClick={startCamera}
                    className="flex-1 flex items-center justify-center gap-2 rounded-xl py-3 border-2 border-dashed border-slate-600 bg-slate-900/60 text-slate-400 hover:border-cyan-500 hover:text-cyan-400 hover:bg-cyan-500/5 transition-all text-xs font-semibold"
                  >
                    <Camera className="h-4 w-4" />
                    <span>Take Photo</span>
                  </button>
                </div>
                <button
                  onClick={() => {
                    setShowRepairFlow(false);
                    setRepairPhoto(null);
                  }}
                  className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-slate-800/50 hover:bg-slate-800 py-2 text-[11px] font-semibold text-slate-400 transition-all"
                >
                  <X className="h-3 w-3" />
                  <span>Cancel</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Telemetry Details Grid */}
        <div className="grid grid-cols-2 gap-3 mb-5 text-xs">
          <div className="rounded-xl bg-slate-900/70 p-3 border border-slate-800">
            <div className="text-slate-400 mb-1">Severity Assessment</div>
            <div className={`text-xl font-black ${isCritical ? 'text-rose-400' : 'text-amber-400'}`}>
              {hazard.severity_score} / 100
            </div>
            <div className="text-[11px] text-slate-400">
              {hazard.cluster_count} spatial clusters reported
            </div>
          </div>

          <div className="rounded-xl bg-slate-900/70 p-3 border border-slate-800">
            <div className="text-slate-400 mb-1">Detection Confidence</div>
            <div className="text-xl font-black text-white">
              {(hazard.confidence * 100).toFixed(1)}%
            </div>
            <div className="text-[11px] text-cyan-400 font-mono">
              Model: yolov8n.pt
            </div>
          </div>

          <div className="rounded-xl bg-slate-900/70 p-3 border border-slate-800">
            <div className="flex items-center gap-1.5 text-slate-400 mb-1">
              <MapPin className="h-3.5 w-3.5 text-amber-400" /> GPS Tag
            </div>
            <div className="font-mono text-white text-[11px]">
              {hazard.latitude.toFixed(6)}, {hazard.longitude.toFixed(6)}
            </div>
          </div>

          <div className="rounded-xl bg-slate-900/70 p-3 border border-slate-800">
            <div className="flex items-center gap-1.5 text-slate-400 mb-1">
              <Bot className="h-3.5 w-3.5 text-blue-400" /> {hazard.reported_by ? 'Reported By' : 'Reporting Agent'}
            </div>
            <div className="font-mono text-white text-[11px]">
              {hazard.reported_by ? (
                <span className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-purple-400"></span>
                  <span className="text-purple-300">{hazard.reported_by}</span>
                </span>
              ) : (
                hazard.robot_id
              )}
            </div>
          </div>
        </div>

        {/* Action Triage Toolbar */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <span className="text-xs text-slate-400">
            Current Status: <strong className="text-white capitalize">{hazard.status}</strong>
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                onUpdateStatus(hazard.id, 'acknowledged');
                onClose();
              }}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600/80 hover:bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition-all"
            >
              <Clock className="h-3.5 w-3.5" />
              <span>Acknowledge</span>
            </button>
            {isAdmin && !isRepaired && (
              <button
                onClick={() => setShowRepairFlow(true)}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-white transition-all ${
                  showRepairFlow
                    ? 'bg-emerald-500/30 border border-emerald-500/50 ring-2 ring-emerald-500/20'
                    : 'bg-emerald-600/80 hover:bg-emerald-600'
                }`}
              >
                <Camera className="h-3.5 w-3.5" />
                <span>Mark Repaired</span>
              </button>
            )}
            {isAdmin && (
              <button
                onClick={() => {
                  if (window.confirm(`Delete hazard #${hazard.id} as fake/invalid? This cannot be undone.`)) {
                    onDeleteHazard(hazard.id);
                    onClose();
                  }
                }}
                className="flex items-center gap-1.5 rounded-lg bg-rose-600/80 hover:bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white transition-all"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Delete Fake</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
