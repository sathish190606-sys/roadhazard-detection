export interface Hazard {
  id: number;
  robot_id: string;
  hazard_class: 'pothole' | 'crack' | 'animal';
  confidence: number;
  latitude: number;
  longitude: number;
  bbox_x1?: number;
  bbox_y1?: number;
  bbox_x2?: number;
  bbox_y2?: number;
  snapshot_url?: string;
  repair_snapshot_url?: string;
  severity_score: number;
  cluster_count: number;
  status: 'new' | 'acknowledged' | 'repaired';
  reported_by?: string;
  created_at: string;
  updated_at: string;
}

export interface RobotStatus {
  robot_id: string;
  status: 'online' | 'offline' | 'patrol' | 'emergency_stop';
  battery_percentage: number;
  current_latitude?: number;
  current_longitude?: number;
  speed: number;
  ip_address?: string;
  last_seen: string;
  is_online: boolean;
}

export interface Stats {
  total_hazards: number;
  by_class: {
    pothole: number;
    crack: number;
    animal: number;
  };
  by_status: {
    new: number;
    acknowledged: number;
    repaired: number;
  };
  average_severity: number;
  active_robots: number;
  total_robots: number;
  hazards_per_day: Array<{
    date: string;
    count: number;
  }>;
}

export interface User {
  id: number;
  username: string;
  role: 'admin' | 'viewer';
  is_active: boolean;
}
