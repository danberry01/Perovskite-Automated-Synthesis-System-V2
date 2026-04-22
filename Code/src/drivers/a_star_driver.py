"""A simple A* planner for XY path planning around axis-aligned box obstacles.

This planner operates in the XY plane and returns a list of XY waypoints
that avoid rectangular obstacle footprints. Z is handled by callers
(e.g., raising to a safe Z before following the XY path).

The obstacle file format supported: a list of entries where each entry is
either a dict with keys `name,x1,y1,z1,x2,y2,z2` or a list:
  [name, x1, y1, z1, x2, y2, z2]

This implementation is intentionally simple and uses a coarse grid-based
representation. It's suitable for short-range planning around a few boxes.
"""
import math
import heapq
from typing import List, Tuple, Optional

from drivers.procedure_file_driver import ProcedureFile


class AStarPlanner:
    def __init__(self, resolution: float = 10.0, clearance: float = 5.0, max_nodes: int = 20000):
        """Create a planner.

        Args:
            resolution: grid cell size in mm
            clearance: additional padding around obstacles in mm
            max_nodes: node exploration limit to avoid pathological runs
        """
        self.resolution = float(resolution)
        self.clearance = float(clearance)
        self.max_nodes = int(max_nodes)

    def _normalize_obstacles(self, raw):
        obs = []
        if not raw:
            return obs
        for entry in raw:
            try:
                if isinstance(entry, dict):
                    name = entry.get('name') or ''
                    x1 = float(entry.get('x1', 0))
                    y1 = float(entry.get('y1', 0))
                    z1 = float(entry.get('z1', 0))
                    x2 = float(entry.get('x2', x1))
                    y2 = float(entry.get('y2', y1))
                    z2 = float(entry.get('z2', z1))
                elif isinstance(entry, (list, tuple)) and len(entry) >= 7:
                    name = entry[0]
                    x1 = float(entry[1]); y1 = float(entry[2]); z1 = float(entry[3])
                    x2 = float(entry[4]); y2 = float(entry[5]); z2 = float(entry[6])
                else:
                    # skip unknown formats
                    continue

                xmin = min(x1, x2) - self.clearance
                xmax = max(x1, x2) + self.clearance
                ymin = min(y1, y2) - self.clearance
                ymax = max(y1, y2) + self.clearance
                zmin = min(z1, z2)
                zmax = max(z1, z2)
                obs.append({'name': name, 'x1': xmin, 'y1': ymin, 'x2': xmax, 'y2': ymax, 'z1': zmin, 'z2': zmax})
            except Exception:
                continue
        return obs

    def _xy_to_idx(self, x, y, min_x, min_y):
        ix = int(round((x - min_x) / self.resolution))
        iy = int(round((y - min_y) / self.resolution))
        return ix, iy

    def _idx_to_xy(self, ix, iy, min_x, min_y):
        x = min_x + ix * self.resolution
        y = min_y + iy * self.resolution
        return x, y

    def _build_occupancy(self, min_x, min_y, nx, ny, obstacles):
        blocked = set()
        for ob in obstacles:
            # compute index ranges
            ix1, iy1 = self._xy_to_idx(ob['x1'], ob['y1'], min_x, min_y)
            ix2, iy2 = self._xy_to_idx(ob['x2'], ob['y2'], min_x, min_y)
            # ensure ordering
            sx = min(ix1, ix2); ex = max(ix1, ix2)
            sy = min(iy1, iy2); ey = max(iy1, iy2)
            for ix in range(sx, ex + 1):
                for iy in range(sy, ey + 1):
                    if 0 <= ix < nx and 0 <= iy < ny:
                        blocked.add((ix, iy))
        return blocked

    def _filter_obstacles_for_travel_z(self, obstacles, travel_z: Optional[float]):
        if travel_z is None:
            return obstacles
        return [ob for ob in obstacles if ob['z1'] <= float(travel_z) <= ob['z2']]

    def plan(self, start: Tuple[float, float, float], goal: Tuple[float, float, float], raw_obstacles: Optional[List] = None, travel_z: Optional[float] = None) -> Optional[List[Tuple[float, float]]]:
        """Plan an XY path from start to goal avoiding obstacles.

        Args:
            start: (x,y,z)
            goal: (x,y,z)
            raw_obstacles: raw list loadable from YAML (see docstring)

        Returns:
            list of (x,y) waypoints including start and goal, or None if planning failed.
        """
        sx, sy, sz = float(start[0]), float(start[1]), float(start[2])
        gx, gy, gz = float(goal[0]), float(goal[1]), float(goal[2])

        obstacles = self._normalize_obstacles(raw_obstacles)
        travel_obstacles = self._filter_obstacles_for_travel_z(obstacles, travel_z)

        # Quick check: if start or goal inside an obstacle (including clearance), planning fails
        for ob in obstacles:
            if ob['x1'] <= sx <= ob['x2'] and ob['y1'] <= sy <= ob['y2'] and ob['z1'] <= sz <= ob['z2']:
                raise ValueError("Start is inside an obstacle")
            if ob['x1'] <= gx <= ob['x2'] and ob['y1'] <= gy <= ob['y2'] and ob['z1'] <= gz <= ob['z2']:
                raise ValueError("Goal is inside an obstacle")

        # If no obstacles, return straight-line path
        if not travel_obstacles:
            return [(sx, sy), (gx, gy)]

        # Bounding box
        min_x = min(sx, gx, min(o['x1'] for o in travel_obstacles) - self.resolution)
        max_x = max(sx, gx, max(o['x2'] for o in travel_obstacles) + self.resolution)
        min_y = min(sy, gy, min(o['y1'] for o in travel_obstacles) - self.resolution)
        max_y = max(sy, gy, max(o['y2'] for o in travel_obstacles) + self.resolution)

        nx = int(math.ceil((max_x - min_x) / self.resolution)) + 1
        ny = int(math.ceil((max_y - min_y) / self.resolution)) + 1

        # Clamp grid size to avoid huge planning maps
        if nx * ny > 200000:
            raise RuntimeError("Planning grid too large; increase resolution or reduce obstacle extents")

        blocked = self._build_occupancy(min_x, min_y, nx, ny, travel_obstacles)

        start_idx = self._xy_to_idx(sx, sy, min_x, min_y)
        goal_idx = self._xy_to_idx(gx, gy, min_x, min_y)

        # If start or goal index is blocked, abort
        if start_idx in blocked:
            raise ValueError("Start index is inside blocked cell")
        if goal_idx in blocked:
            raise ValueError("Goal index is inside blocked cell")

        # A* search
        def heuristic(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1])

        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]

        open_set = []
        heapq.heappush(open_set, (0 + heuristic(start_idx, goal_idx), 0, start_idx))
        came_from = {}
        gscore = {start_idx: 0}

        nodes_explored = 0
        while open_set:
            _, current_g, current = heapq.heappop(open_set)
            nodes_explored += 1
            if nodes_explored > self.max_nodes:
                raise RuntimeError("A* exploration limit reached")

            if current == goal_idx:
                # reconstruct
                path_idx = [current]
                while path_idx[-1] in came_from:
                    path_idx.append(came_from[path_idx[-1]])
                path_idx.reverse()
                # convert indices to XY
                path_xy = [self._idx_to_xy(ix, iy, min_x, min_y) for (ix, iy) in path_idx]
                # ensure final point is exact goal
                if path_xy and (path_xy[-1][0] != gx or path_xy[-1][1] != gy):
                    path_xy.append((gx, gy))
                return path_xy

            # expand
            for dx, dy in neighbors:
                neighbor = (current[0] + dx, current[1] + dy)
                if neighbor[0] < 0 or neighbor[1] < 0 or neighbor[0] >= nx or neighbor[1] >= ny:
                    continue
                if neighbor in blocked:
                    continue
                if dx != 0 and dy != 0:
                    side_a = (current[0] + dx, current[1])
                    side_b = (current[0], current[1] + dy)
                    if side_a in blocked or side_b in blocked:
                        continue
                tentative_g = current_g + heuristic(current, neighbor)
                if neighbor not in gscore or tentative_g < gscore[neighbor]:
                    gscore[neighbor] = tentative_g
                    f = tentative_g + heuristic(neighbor, goal_idx)
                    heapq.heappush(open_set, (f, tentative_g, neighbor))
                    came_from[neighbor] = current

        # No path found
        return None


def load_obstacles_file(path: str):
    try:
        data = ProcedureFile().Open(path)
        return data
    except Exception:
        return None
