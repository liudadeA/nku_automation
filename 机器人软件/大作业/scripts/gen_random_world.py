#!/usr/bin/env python3
"""
Generate a Gazebo world with randomly placed red/green/blue blocks,
and a matching PGM map for navigation.

Usage:
  python3 gen_random_world.py [world_file] [map_prefix] [seed]
"""

import sys
import os
import random
import numpy as np
from PIL import Image

# --- Config ---
MAP_SIZE_X = 8.0   # meters, total map width
MAP_SIZE_Y = 6.0   # meters, total map height
RESOLUTION = 0.05   # meters/pixel
WALL_THICKNESS = 0.2
BLOCK_SIZE = 0.25   # meters, cube side (big enough for Kinect to see)

# World boundaries (inner area where blocks can be placed)
# Robot starts at (0,0), blocks should be reachable
X_MIN, X_MAX = 0.5, 3.0
Y_MIN, Y_MAX = -1.5, 1.5

WALL_COLOR = '0.5 0.5 0.5 1'

BLOCK_COLORS = {
    'red':   ('1 0 0 1', 'Red'),
    'green': ('0 1 0 1', 'Green'),
    'blue':  ('0 0 1 1', 'Blue'),
}


def gen_world(blocks, world_path):
    """Generate a Gazebo .world file with walls and colored blocks."""
    # SDF header
    sdf = f"""<sdf version="1.6">
  <world name="random_blocks_world">
    <include><uri>model://sun</uri></include>
    <include><uri>model://ground_plane</uri></include>

    <!-- Walls: create a bounded arena -->
    <!-- Left wall -->
    <model name="wall_left"><static>true</static>
      <pose>{(X_MAX+X_MIN)/2-1} {Y_MAX+WALL_THICKNESS/2} 0.5 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry><box><size>{(X_MAX-X_MIN)+4} {WALL_THICKNESS} 1.0</size></box></geometry>
          <material><ambient>{WALL_COLOR}</ambient><diffuse>{WALL_COLOR}</diffuse></material>
        </visual>
        <collision name="collision">
          <geometry><box><size>{(X_MAX-X_MIN)+4} {WALL_THICKNESS} 1.0</size></box></geometry>
        </collision>
      </link>
    </model>

    <!-- Right wall -->
    <model name="wall_right"><static>true</static>
      <pose>{(X_MAX+X_MIN)/2-1} {Y_MIN-WALL_THICKNESS/2} 0.5 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry><box><size>{(X_MAX-X_MIN)+4} {WALL_THICKNESS} 1.0</size></box></geometry>
          <material><ambient>{WALL_COLOR}</ambient><diffuse>{WALL_COLOR}</diffuse></material>
        </visual>
        <collision name="collision">
          <geometry><box><size>{(X_MAX-X_MIN)+4} {WALL_THICKNESS} 1.0</size></box></geometry>
        </collision>
      </link>
    </model>

    <!-- Front wall (near robot start) -->
    <model name="wall_front"><static>true</static>
      <pose>{X_MIN-1-WALL_THICKNESS/2} 0 0.5 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry><box><size>{WALL_THICKNESS} {Y_MAX-Y_MIN+WALL_THICKNESS*2} 1.0</size></box></geometry>
          <material><ambient>{WALL_COLOR}</ambient><diffuse>{WALL_COLOR}</diffuse></material>
        </visual>
        <collision name="collision">
          <geometry><box><size>{WALL_THICKNESS} {Y_MAX-Y_MIN+WALL_THICKNESS*2} 1.0</size></box></geometry>
        </collision>
      </link>
    </model>

    <!-- Back wall -->
    <model name="wall_back"><static>true</static>
      <pose>{X_MAX+1+WALL_THICKNESS/2} 0 0.5 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry><box><size>{WALL_THICKNESS} {Y_MAX-Y_MIN+WALL_THICKNESS*2} 1.0</size></box></geometry>
          <material><ambient>{WALL_COLOR}</ambient><diffuse>{WALL_COLOR}</diffuse></material>
        </visual>
        <collision name="collision">
          <geometry><box><size>{WALL_THICKNESS} {Y_MAX-Y_MIN+WALL_THICKNESS*2} 1.0</size></box></geometry>
        </collision>
      </link>
    </model>
"""

    for color_name, (pos, z) in blocks.items():
        rgba, label = BLOCK_COLORS[color_name]
        x, y = pos
        sdf += f"""
    <!-- {label} block at ({x:.2f}, {y:.2f}) -->
    <model name="{color_name}_block"><static>true</static>
      <pose>{x:.2f} {y:.2f} {z:.2f} 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry><box><size>{BLOCK_SIZE} {BLOCK_SIZE} {BLOCK_SIZE}</size></box></geometry>
          <material><ambient>{rgba}</ambient><diffuse>{rgba}</diffuse></material>
        </visual>
        <collision name="collision">
          <geometry><box><size>{BLOCK_SIZE} {BLOCK_SIZE} {BLOCK_SIZE}</size></box></geometry>
        </collision>
      </link>
    </model>"""

    sdf += "\n  </world>\n</sdf>\n"

    with open(world_path, 'w') as f:
        f.write(sdf)
    print(f"World saved: {world_path}")


def gen_map(blocks, map_yaml_path, map_pgm_path):
    """Generate a PGM map matching the world geometry."""
    # Map origin: bottom-left corner of the arena area
    ox = -(MAP_SIZE_X / 2)
    oy = -(MAP_SIZE_Y / 2)
    w = int(MAP_SIZE_X / RESOLUTION)
    h = int(MAP_SIZE_Y / RESOLUTION)

    # All free space (254 = free)
    img = np.full((h, w), 254, dtype=np.uint8)

    def world_to_pixel(wx, wy):
        px = int((wx - ox) / RESOLUTION)
        py = int((wy - oy) / RESOLUTION)
        # Flip Y for image coordinates
        return px, h - 1 - py

    def draw_rect(x0, y0, x1, y1):
        """Draw occupied rectangle in world coords."""
        px0, py0 = world_to_pixel(x0, y0)
        px1, py1 = world_to_pixel(x1, y1)
        px0, px1 = sorted([px0, px1])
        py0, py1 = sorted([py0, py1])
        px0 = max(0, px0); px1 = min(w - 1, px1)
        py0 = max(0, py0); py1 = min(h - 1, py1)
        img[py0:py1 + 1, px0:px1 + 1] = 0

    # Walls
    wx0 = X_MIN - 1 - WALL_THICKNESS
    wx1 = X_MAX + 1 + WALL_THICKNESS
    wy0 = Y_MIN - WALL_THICKNESS
    wy1 = Y_MAX + WALL_THICKNESS

    # Left wall
    draw_rect(wx0, Y_MAX, wx1, Y_MAX + WALL_THICKNESS)
    # Right wall
    draw_rect(wx0, Y_MIN - WALL_THICKNESS, wx1, Y_MIN)
    # Front wall
    draw_rect(X_MIN - 1 - WALL_THICKNESS, wy0, X_MIN - 1, wy1)
    # Back wall
    draw_rect(X_MAX + 1, wy0, X_MAX + 1 + WALL_THICKNESS, wy1)

    # Save PGM
    Image.fromarray(img).save(map_pgm_path)

    # Write YAML
    yaml = f"""image: {os.path.basename(map_pgm_path)}
resolution: {RESOLUTION}
origin: [{ox}, {oy}, 0.000000]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
"""
    with open(map_yaml_path, 'w') as f:
        f.write(yaml)
    print(f"Map saved: {map_yaml_path} ({w}x{h} px)")


def main():
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else random.randint(0, 9999)
    world_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/random_blocks.world'
    map_prefix = sys.argv[2] if len(sys.argv) > 2 else '/tmp/random_blocks'

    random.seed(seed)
    print(f"Seed: {seed}")

    # Generate random positions for 3 blocks (ensure minimum separation)
    block_size = BLOCK_SIZE
    positions = {}
    for color in ['red', 'green', 'blue']:
        for _ in range(100):
            x = random.uniform(X_MIN + 0.5, X_MAX - 0.5)
            y = random.uniform(Y_MIN + 0.5, Y_MAX - 0.5)
            # Check separation from other blocks (min 0.5m apart)
            ok = True
            for other_pos in positions.values():
                dx = x - other_pos[0]
                dy = y - other_pos[1]
                if dx*dx + dy*dy < 0.5 * 0.5:
                    ok = False
                    break
            if ok:
                positions[color] = (x, y)
                break
        else:
            positions[color] = (random.uniform(X_MIN, X_MAX),
                                random.uniform(Y_MIN, Y_MAX))

        print(f"  {color}: ({positions[color][0]:.2f}, {positions[color][1]:.2f})")

    # Block Z height (elevated so camera can see them)
    blocks_with_z = {c: (pos, BLOCK_SIZE/2 + 0.05) for c, pos in positions.items()}

    gen_world(blocks_with_z, world_path)
    gen_map(blocks_with_z, map_prefix + '.yaml', map_prefix + '.pgm')

    # Also save positions as a text file for reference
    with open(map_prefix + '_positions.txt', 'w') as f:
        for color, (pos, z) in blocks_with_z.items():
            f.write(f"{color}: x={pos[0]:.2f} y={pos[1]:.2f} z={z:.2f}\n")
    print(f"Positions saved: {map_prefix}_positions.txt")


if __name__ == '__main__':
    main()
