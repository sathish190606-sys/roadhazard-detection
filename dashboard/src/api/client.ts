import { Hazard, RobotStatus, Stats, User } from '../types';

const BASE_URL = '';

export const api = {
  getAuthToken(): string | null {
    return localStorage.getItem('roadbot_token');
  },

  setAuthToken(token: string) {
    localStorage.setItem('roadbot_token', token);
  },

  clearAuthToken() {
    localStorage.removeItem('roadbot_token');
  },

  getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    const token = this.getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  },

  async getHazards(params?: {
    hazard_class?: string;
    status?: string;
    min_confidence?: number;
    min_severity?: number;
  }): Promise<Hazard[]> {
    const query = new URLSearchParams();
    if (params?.hazard_class) query.append('hazard_class', params.hazard_class);
    if (params?.status) query.append('status', params.status);
    if (params?.min_confidence) query.append('min_confidence', params.min_confidence.toString());
    if (params?.min_severity) query.append('min_severity', params.min_severity.toString());

    const res = await fetch(`/api/hazards?${query.toString()}`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch hazards');
    return res.json();
  },

  async updateHazardStatus(id: number, status: 'new' | 'acknowledged' | 'repaired'): Promise<Hazard> {
    const res = await fetch(`/api/hazards/${id}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error('Failed to update hazard status');
    return res.json();
  },

  async getRobots(): Promise<RobotStatus[]> {
    const res = await fetch('/api/robots/status', {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch robot status');
    return res.json();
  },

  async getStats(): Promise<Stats> {
    const res = await fetch('/api/stats', {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
  },

  async login(username: string, password: string): Promise<{ access_token: string; role: string; username: string }> {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error('Invalid credentials');
    return res.json();
  },

  async getCurrentUser(): Promise<User> {
    const res = await fetch('/api/auth/me', {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error('Unauthorized');
    return res.json();
  },

  async register(username: string, password: string): Promise<{ username: string; role: string }> {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Registration failed');
    return data;
  },

  async reportHazard(data: {
    hazard_class: string;
    latitude: number;
    longitude: number;
    description?: string;
    snapshot_base64?: string;
  }): Promise<Hazard> {
    const res = await fetch('/api/hazards/report', {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to report hazard' }));
      throw new Error(err.detail || 'Failed to report hazard');
    }
    return res.json();
  },

  async deleteHazard(id: number): Promise<{ id: number; detail: string }> {
    const res = await fetch(`/api/hazards/${id}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });
    // 404 means hazard was already deleted (e.g. by another tab or WS broadcast) – treat as success
    if (res.status === 404) {
      return { id, detail: 'Hazard already deleted' };
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to delete hazard' }));
      throw new Error(err.detail || 'Failed to delete hazard');
    }
    return res.json();
  },

  async uploadRepairPhoto(id: number, snapshotBase64: string): Promise<Hazard> {
    const res = await fetch(`/api/hazards/${id}/repair-photo`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ snapshot_base64: snapshotBase64 }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to upload repair photo' }));
      throw new Error(err.detail || 'Failed to upload repair photo');
    }
    return res.json();
  },
};


export class LiveSocket {
  private ws: WebSocket | null = null;
  private onMessageCallback: (data: any) => void;
  private reconnectInterval = 3000;
  private pingInterval: any = null;

  constructor(onMessage: (data: any) => void) {
    this.onMessageCallback = onMessage;
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/live`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[LiveSocket] Connected to WebSocket hub');
        this.pingInterval = setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send('ping');
          }
        }, 15000);
      };

      this.ws.onmessage = (event) => {
        if (event.data === 'pong') return;
        try {
          const payload = JSON.parse(event.data);
          this.onMessageCallback(payload);
        } catch (e) {
          console.error('[LiveSocket] Error parsing event:', e);
        }
      };

      this.ws.onclose = () => {
        console.warn('[LiveSocket] Disconnected. Reconnecting in 3s...');
        clearInterval(this.pingInterval);
        setTimeout(() => this.connect(), this.reconnectInterval);
      };

      this.ws.onerror = (err) => {
        console.error('[LiveSocket] Error:', err);
        this.ws?.close();
      };
    } catch (e) {
      console.error('[LiveSocket] Connection error:', e);
      setTimeout(() => this.connect(), this.reconnectInterval);
    }
  }

  disconnect() {
    clearInterval(this.pingInterval);
    this.ws?.close();
  }
}
