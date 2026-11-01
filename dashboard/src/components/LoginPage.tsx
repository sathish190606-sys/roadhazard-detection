import React, { useState } from 'react';
import {
  Radio, Lock, User, ArrowRight, ShieldAlert,
  Eye, EyeOff, UserPlus, LogIn, CheckCircle2,
  Cpu, Wifi, MapPin, Activity
} from 'lucide-react';
import { api } from '../api/client';

interface AuthPageProps {
  onLoginSuccess: (user: any) => void;
}

/* ──────────────────────────────────────────────
   Animated background particles
────────────────────────────────────────────── */
const ParticleField: React.FC = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    {/* Glow orbs */}
    <div className="absolute top-[-10%] left-[20%] h-[500px] w-[500px] rounded-full bg-cyan-600/8 blur-[140px]" />
    <div className="absolute bottom-[-10%] right-[10%] h-[400px] w-[400px] rounded-full bg-blue-700/10 blur-[120px]" />
    <div className="absolute top-[40%] left-[-5%] h-[300px] w-[300px] rounded-full bg-indigo-600/8 blur-[100px]" />

    {/* Grid lines */}
    <div
      className="absolute inset-0 opacity-[0.03]"
      style={{
        backgroundImage: `linear-gradient(rgba(6,182,212,1) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(6,182,212,1) 1px, transparent 1px)`,
        backgroundSize: '60px 60px',
      }}
    />

    {/* Scanning line */}
    <div className="absolute left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent animate-[scan_4s_ease-in-out_infinite]"
      style={{ top: '30%' }}
    />
  </div>
);

/* ──────────────────────────────────────────────
   Stat badges shown beside the form
────────────────────────────────────────────── */
const StatBadge: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({ icon, label, value }) => (
  <div className="flex items-center gap-3 rounded-xl bg-slate-900/60 border border-slate-800/70 px-4 py-3 backdrop-blur-sm">
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-400">
      {icon}
    </div>
    <div>
      <p className="text-[10px] text-slate-500 uppercase tracking-widest">{label}</p>
      <p className="text-xs font-bold text-slate-200">{value}</p>
    </div>
  </div>
);

/* ──────────────────────────────────────────────
   Input field with icon
────────────────────────────────────────────── */
const InputField: React.FC<{
  id: string;
  label: string;
  icon: React.ReactNode;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  extra?: React.ReactNode;
  hint?: string;
}> = ({ id, label, icon, type, value, onChange, placeholder, extra, hint }) => (
  <div>
    <label htmlFor={id} className="block text-xs font-semibold text-slate-300 mb-1.5">
      {label}
    </label>
    <div className="relative">
      <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500">{icon}</span>
      <input
        id={id}
        type={type}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl bg-slate-950/80 border border-slate-800 pl-10 pr-10 py-2.5 text-sm text-white
                   placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50
                   transition-all duration-200"
      />
      {extra && <span className="absolute right-3.5 top-1/2 -translate-y-1/2">{extra}</span>}
    </div>
    {hint && <p className="mt-1 text-[10px] text-slate-500">{hint}</p>}
  </div>
);

/* ──────────────────────────────────────────────
   Password strength meter
────────────────────────────────────────────── */
const StrengthMeter: React.FC<{ password: string }> = ({ password }) => {
  const strength = (() => {
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return score;
  })();

  const labels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
  const colors = ['', 'bg-rose-500', 'bg-amber-400', 'bg-lime-500', 'bg-emerald-500'];
  const textColors = ['', 'text-rose-400', 'text-amber-400', 'text-lime-400', 'text-emerald-400'];

  if (!password) return null;

  return (
    <div className="mt-1.5">
      <div className="flex gap-1 mb-1">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              i <= strength ? colors[strength] : 'bg-slate-800'
            }`}
          />
        ))}
      </div>
      {strength > 0 && (
        <p className={`text-[10px] ${textColors[strength]}`}>
          {labels[strength]} password
        </p>
      )}
    </div>
  );
};

/* ══════════════════════════════════════════════
   Main Auth Page Component
══════════════════════════════════════════════ */
export const LoginPage: React.FC<AuthPageProps> = ({ onLoginSuccess }) => {
  const [mode, setMode] = useState<'login' | 'signup'>('login');

  // Login state
  const [loginUsername, setLoginUsername] = useState('admin');
  const [loginPassword, setLoginPassword] = useState('admin123');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [showLoginPw, setShowLoginPw] = useState(false);

  // Sign-up state
  const [regUsername, setRegUsername] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState<string | null>(null);
  const [regSuccess, setRegSuccess] = useState(false);
  const [showRegPw, setShowRegPw] = useState(false);
  const [showRegConfirm, setShowRegConfirm] = useState(false);

  /* ---- Login handler ---- */
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError(null);
    try {
      const data = await api.login(loginUsername, loginPassword);
      api.setAuthToken(data.access_token);
      const user = await api.getCurrentUser();
      onLoginSuccess(user);
    } catch (err: any) {
      setLoginError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoginLoading(false);
    }
  };

  /* ---- Register handler ---- */
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegError(null);

    if (regUsername.length < 3) {
      setRegError('Username must be at least 3 characters.');
      return;
    }
    if (regPassword.length < 6) {
      setRegError('Password must be at least 6 characters.');
      return;
    }
    if (regPassword !== regConfirm) {
      setRegError('Passwords do not match.');
      return;
    }

    setRegLoading(true);
    try {
      await api.register(regUsername, regPassword);
      setRegSuccess(true);
      // Auto-switch to login after 2.5s
      setTimeout(() => {
        setMode('login');
        setLoginUsername(regUsername);
        setLoginPassword('');
        setRegSuccess(false);
        setRegUsername('');
        setRegPassword('');
        setRegConfirm('');
      }, 2500);
    } catch (err: any) {
      setRegError(err.message || 'Registration failed. Please try again.');
    } finally {
      setRegLoading(false);
    }
  };

  const switchMode = (m: 'login' | 'signup') => {
    setMode(m);
    setLoginError(null);
    setRegError(null);
    setRegSuccess(false);
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4 bg-slate-950 selection:bg-cyan-500 selection:text-white overflow-hidden">
      <ParticleField />

      <div className="relative z-10 flex w-full max-w-5xl items-center gap-12">

        {/* ── Left hero column ── */}
        <div className="hidden lg:flex flex-col flex-1 gap-6">
          {/* Logo / title */}
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-600 shadow-xl shadow-cyan-500/30">
              <Radio className="h-5 w-5 text-white animate-pulse" />
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight text-white leading-none">RoadBot AI</h1>
              <p className="text-[10px] text-slate-500 tracking-widest uppercase">Fleet Operations Center</p>
            </div>
          </div>

          <h2 className="text-4xl font-black leading-tight text-white">
            Real-Time Road<br />
            <span className="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              Hazard Intelligence
            </span>
          </h2>
          <p className="text-sm text-slate-400 max-w-sm leading-relaxed">
            Monitor autonomous robot fleets detecting potholes, cracks, and animal hazards in real-time using YOLOv8 edge AI on your live operations map.
          </p>

          {/* Live system stats */}
          <div className="grid grid-cols-1 gap-3 mt-2">
            <StatBadge icon={<Cpu className="h-4 w-4" />} label="AI Model" value="YOLOv8 Nano — 12.7 FPS Edge" />
            <StatBadge icon={<Wifi className="h-4 w-4" />} label="Uplink" value="MQTT + WebSocket Live Stream" />
            <StatBadge icon={<MapPin className="h-4 w-4" />} label="Detection" value="Pothole · Crack · Animal" />
            <StatBadge icon={<Activity className="h-4 w-4" />} label="Coverage" value="Algorithm 1 — Patrol & Avoid" />
          </div>

          {/* Divider */}
          <div className="h-px bg-gradient-to-r from-cyan-500/30 via-blue-500/20 to-transparent" />
          <p className="text-[10px] text-slate-600">
            Secured with JWT Bearer Auth · Real-time WebSocket events · PostgreSQL / SQLite backend
          </p>
        </div>

        {/* ── Right card column ── */}
        <div className="w-full max-w-md shrink-0">
          {/* Tab switcher */}
          <div className="flex rounded-2xl bg-slate-900/70 border border-slate-800 p-1 mb-5 backdrop-blur-sm">
            <button
              id="tab-login"
              onClick={() => switchMode('login')}
              className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-xs font-bold transition-all duration-200 ${
                mode === 'login'
                  ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-600/20'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <LogIn className="h-3.5 w-3.5" />
              Sign In
            </button>
            <button
              id="tab-signup"
              onClick={() => switchMode('signup')}
              className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-xs font-bold transition-all duration-200 ${
                mode === 'signup'
                  ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-600/20'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <UserPlus className="h-3.5 w-3.5" />
              Create Account
            </button>
          </div>

          {/* Card */}
          <div className="rounded-3xl border border-slate-800/80 bg-slate-900/70 p-8 shadow-2xl backdrop-blur-2xl">

            {/* Mobile logo */}
            <div className="flex lg:hidden items-center gap-3 mb-6">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600">
                <Radio className="h-4 w-4 text-white animate-pulse" />
              </div>
              <div>
                <h1 className="text-sm font-black text-white">RoadBot AI</h1>
                <p className="text-[9px] text-slate-500 uppercase tracking-widest">Operations Center</p>
              </div>
            </div>

            {/* ── LOGIN FORM ── */}
            {mode === 'login' && (
              <>
                <div className="mb-7">
                  <h2 className="text-xl font-black text-white">Welcome back</h2>
                  <p className="text-xs text-slate-400 mt-1">Sign in to access the live operations dashboard.</p>
                </div>

                {loginError && (
                  <div className="mb-5 flex items-start gap-2.5 rounded-xl bg-rose-500/10 border border-rose-500/25 px-4 py-3 text-xs text-rose-300">
                    <ShieldAlert className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                    <span>{loginError}</span>
                  </div>
                )}

                <form id="login-form" onSubmit={handleLogin} className="space-y-4">
                  <InputField
                    id="login-username"
                    label="Username"
                    icon={<User className="h-4 w-4" />}
                    type="text"
                    value={loginUsername}
                    onChange={setLoginUsername}
                    placeholder="Enter username"
                  />

                  <InputField
                    id="login-password"
                    label="Password"
                    icon={<Lock className="h-4 w-4" />}
                    type={showLoginPw ? 'text' : 'password'}
                    value={loginPassword}
                    onChange={setLoginPassword}
                    placeholder="Enter password"
                    extra={
                      <button
                        type="button"
                        onClick={() => setShowLoginPw(!showLoginPw)}
                        className="text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        {showLoginPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    }
                  />

                  <button
                    id="login-submit-btn"
                    type="submit"
                    disabled={loginLoading}
                    className="w-full mt-2 flex items-center justify-center gap-2 rounded-xl
                               bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500
                               py-3 text-sm font-bold text-white shadow-lg shadow-cyan-600/25
                               transition-all duration-200 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loginLoading ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                        <span>Authenticating...</span>
                      </>
                    ) : (
                      <>
                        <span>Sign In to Console</span>
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                </form>

                <div className="mt-6 pt-5 border-t border-slate-800/60 text-center">
                  <p className="text-[11px] text-slate-500">
                    Default credentials:{' '}
                    <code className="text-cyan-400 font-mono">admin</code>
                    {' / '}
                    <code className="text-cyan-400 font-mono">admin123</code>
                  </p>
                  <button
                    onClick={() => switchMode('signup')}
                    className="mt-3 text-xs text-slate-400 hover:text-cyan-400 transition-colors"
                  >
                    Don't have an account? <span className="text-cyan-400 font-semibold">Create one →</span>
                  </button>
                </div>
              </>
            )}

            {/* ── SIGN UP FORM ── */}
            {mode === 'signup' && (
              <>
                <div className="mb-7">
                  <h2 className="text-xl font-black text-white">Create account</h2>
                  <p className="text-xs text-slate-400 mt-1">Register as a new operator to access the dashboard.</p>
                </div>

                {/* Success state */}
                {regSuccess && (
                  <div className="mb-5 flex items-center gap-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 px-4 py-4 text-sm text-emerald-300">
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
                    <div>
                      <p className="font-bold text-emerald-300">Account created!</p>
                      <p className="text-[11px] text-emerald-400/80 mt-0.5">Redirecting to sign in...</p>
                    </div>
                  </div>
                )}

                {regError && (
                  <div className="mb-5 flex items-start gap-2.5 rounded-xl bg-rose-500/10 border border-rose-500/25 px-4 py-3 text-xs text-rose-300">
                    <ShieldAlert className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                    <span>{regError}</span>
                  </div>
                )}

                {!regSuccess && (
                  <form id="signup-form" onSubmit={handleRegister} className="space-y-4">
                    <InputField
                      id="reg-username"
                      label="Username"
                      icon={<User className="h-4 w-4" />}
                      type="text"
                      value={regUsername}
                      onChange={setRegUsername}
                      placeholder="Choose a username"
                      hint="Minimum 3 characters"
                    />

                    <div>
                      <InputField
                        id="reg-password"
                        label="Password"
                        icon={<Lock className="h-4 w-4" />}
                        type={showRegPw ? 'text' : 'password'}
                        value={regPassword}
                        onChange={setRegPassword}
                        placeholder="Create a password"
                        extra={
                          <button
                            type="button"
                            onClick={() => setShowRegPw(!showRegPw)}
                            className="text-slate-500 hover:text-slate-300 transition-colors"
                          >
                            {showRegPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        }
                      />
                      <StrengthMeter password={regPassword} />
                    </div>

                    <InputField
                      id="reg-confirm-password"
                      label="Confirm Password"
                      icon={<Lock className="h-4 w-4" />}
                      type={showRegConfirm ? 'text' : 'password'}
                      value={regConfirm}
                      onChange={setRegConfirm}
                      placeholder="Re-enter password"
                      extra={
                        <button
                          type="button"
                          onClick={() => setShowRegConfirm(!showRegConfirm)}
                          className="text-slate-500 hover:text-slate-300 transition-colors"
                        >
                          {showRegConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      }
                    />

                    {/* Password match indicator */}
                    {regConfirm && (
                      <p className={`text-[11px] flex items-center gap-1.5 ${
                        regPassword === regConfirm ? 'text-emerald-400' : 'text-rose-400'
                      }`}>
                        {regPassword === regConfirm
                          ? <><CheckCircle2 className="h-3.5 w-3.5" /> Passwords match</>
                          : <><ShieldAlert className="h-3.5 w-3.5" /> Passwords do not match</>
                        }
                      </p>
                    )}

                    <button
                      id="signup-submit-btn"
                      type="submit"
                      disabled={regLoading}
                      className="w-full mt-2 flex items-center justify-center gap-2 rounded-xl
                                 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500
                                 py-3 text-sm font-bold text-white shadow-lg shadow-cyan-600/25
                                 transition-all duration-200 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {regLoading ? (
                        <>
                          <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                          <span>Creating Account...</span>
                        </>
                      ) : (
                        <>
                          <UserPlus className="h-4 w-4" />
                          <span>Create Account</span>
                        </>
                      )}
                    </button>
                  </form>
                )}

                <div className="mt-6 pt-5 border-t border-slate-800/60 text-center">
                  <button
                    onClick={() => switchMode('login')}
                    className="text-xs text-slate-400 hover:text-cyan-400 transition-colors"
                  >
                    Already have an account? <span className="text-cyan-400 font-semibold">Sign in →</span>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
