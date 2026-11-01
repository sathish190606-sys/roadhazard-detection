import math
import time
import random
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import List, Tuple

class SimulatedRobot2D:
    def __init__(self, x: float = 50.0, y: float = 20.0, heading_deg: float = 90.0):
        self.x = x
        self.y = y
        self.heading = heading_deg  # 0 = East, 90 = North
        self.width = 18.0
        self.length = 24.0
        self.speed = 0.0
        self.turn_speed = 0.0

        # Sensor offsets and orientations relative to robot heading
        self.sensor_angles = {
            "front": 0.0,
            "left": 45.0,
            "right": -45.0
        }
        self.max_sensor_range = 100.0  # cm
        self.min_safety_dist = 30.0   # cm (threshold from requirements)

        # State machine
        self.state = "PATROL"  # PATROL, AVOID_STOP, AVOID_BACKUP, AVOID_STEER
        self.state_timer = 0.0

    def get_sensor_distances(self, obstacles: List[Tuple[float, float, float]]) -> dict:
        """Computes distance to closest obstacle in direction of front, left, right sensor cones."""
        distances = {"front": self.max_sensor_range, "left": self.max_sensor_range, "right": self.max_sensor_range}

        rad_heading = math.radians(self.heading)
        for s_name, angle_offset in self.sensor_angles.items():
            s_rad = rad_heading + math.radians(angle_offset)
            # Ray direction vector
            dx = math.cos(s_rad)
            dy = math.sin(s_rad)

            closest_dist = self.max_sensor_range
            for ox, oy, radius in obstacles:
                # Vector from robot to obstacle
                vx = ox - self.x
                vy = oy - self.y
                # Projection on ray
                proj = vx * dx + vy * dy
                if proj > 0:
                    # Perpendicular distance to ray
                    perp_dist = abs(vx * (-dy) + vy * dx)
                    if perp_dist <= radius:
                        # Collision along ray
                        hit_dist = max(0.0, proj - radius)
                        if hit_dist < closest_dist:
                            closest_dist = hit_dist

            distances[s_name] = round(closest_dist, 1)

        return distances

    def update_navigation(self, sensor_dists: dict, dt: float = 0.1):
        """Executes Algorithm 1: Obstacle avoidance & Patrol logic."""
        f_dist = sensor_dists["front"]
        l_dist = sensor_dists["left"]
        r_dist = sensor_dists["right"]

        if self.state == "PATROL":
            if min(f_dist, l_dist, r_dist) < self.min_safety_dist:
                # Emergency trigger
                self.state = "AVOID_STOP"
                self.state_timer = 0.3
                self.speed = 0.0
            else:
                self.speed = 12.0
                self.turn_speed = 0.0

        elif self.state == "AVOID_STOP":
            self.speed = 0.0
            self.turn_speed = 0.0
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "AVOID_BACKUP"
                self.state_timer = 0.6

        elif self.state == "AVOID_BACKUP":
            self.speed = -8.0
            self.turn_speed = 0.0
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "AVOID_STEER"
                self.state_timer = 1.0
                # Steer towards open side
                if l_dist > r_dist:
                    self.turn_speed = 45.0  # Turn left
                else:
                    self.turn_speed = -45.0 # Turn right

        elif self.state == "AVOID_STEER":
            self.speed = 4.0
            self.state_timer -= dt
            if self.state_timer <= 0 and f_dist >= self.min_safety_dist:
                self.state = "PATROL"
                self.turn_speed = 0.0

        # Integrate motion
        self.heading = (self.heading + self.turn_speed * dt) % 360.0
        rad = math.radians(self.heading)
        self.x += self.speed * math.cos(rad) * dt
        self.y += self.speed * math.sin(rad) * dt

def run_simulation_view(max_steps: int = 150):
    robot = SimulatedRobot2D(x=50.0, y=10.0, heading_deg=90.0)
    obstacles = [
        (50.0, 50.0, 8.0),   # Obstacle 1 directly in path
        (35.0, 90.0, 7.0),   # Obstacle 2 on left
        (65.0, 120.0, 9.0),  # Obstacle 3 on right
        (50.0, 160.0, 8.0),  # Obstacle 4
    ]

    plt.ion()
    fig, ax = plt.subplots(figsize=(7, 9))

    trajectory_x = []
    trajectory_y = []

    for step in range(max_steps):
        ax.clear()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 200)
        ax.set_title(f"Algorithm 1 Navigation Simulation | State: {robot.state} | Step: {step}", fontsize=11, fontweight="bold")
        ax.set_xlabel("X Distance (cm)")
        ax.set_ylabel("Y Distance (cm)")
        ax.grid(True, linestyle="--", alpha=0.5)

        # Draw road boundaries
        ax.axvline(x=15, color="gray", linestyle="-", linewidth=3)
        ax.axvline(x=85, color="gray", linestyle="-", linewidth=3)
        ax.axvline(x=50, color="gold", linestyle="--", linewidth=1.5)

        # Draw obstacles
        for ox, oy, r in obstacles:
            circ = patches.Circle((ox, oy), r, color="crimson", alpha=0.7)
            ax.add_patch(circ)
            ax.text(ox - 3, oy - 2, "OBST", color="white", fontsize=7, fontweight="bold")

        # Update sensors and navigation
        sensor_dists = robot.get_sensor_distances(obstacles)
        robot.update_navigation(sensor_dists, dt=0.1)

        trajectory_x.append(robot.x)
        trajectory_y.append(robot.y)
        ax.plot(trajectory_x, trajectory_y, color="royalblue", linestyle=":", alpha=0.6, label="Patrol Trail")

        # Draw Robot body
        rad = math.radians(robot.heading)
        hx = robot.x + 12.0 * math.cos(rad)
        hy = robot.y + 12.0 * math.sin(rad)
        ax.arrow(robot.x, robot.y, hx - robot.x, hy - robot.y, head_width=4, head_length=4, fc="blue", ec="blue")
        rect = patches.Rectangle((robot.x - 7, robot.y - 7), 14, 14, angle=robot.heading - 45, color="navy", alpha=0.8)
        ax.add_patch(rect)

        # Draw sensor range cones
        for s_name, angle_offset in robot.sensor_angles.items():
            dist = sensor_dists[s_name]
            s_rad = rad + math.radians(angle_offset)
            sx = robot.x + dist * math.cos(s_rad)
            sy = robot.y + dist * math.sin(s_rad)
            color = "red" if dist < robot.min_safety_dist else "green"
            ax.plot([robot.x, sx], [robot.y, sy], color=color, linestyle="--", linewidth=1.5)
            ax.text(sx + 1, sy + 1, f"{s_name}: {dist}cm", fontsize=7, color=color)

        plt.pause(0.02)
        if robot.y > 190.0:
            print("Robot reached end of test course successfully!")
            break

    plt.ioff()
    plt.close()

if __name__ == "__main__":
    print("Launching 2D top-down obstacle avoidance simulation...")
    run_simulation_view(max_steps=50)
