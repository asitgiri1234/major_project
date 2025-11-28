# av_sim_names.py
import pygame
import pygame_menu
import osmnx as ox
import networkx as nx
import math
import random
import time
import matplotlib
import string
import sys

# Force non-interactive backend for matplotlib if used elsewhere
matplotlib.use("Agg")

# --- CONFIGURATION ---
WIDTH, HEIGHT = 1800, 950
FPS = 60

LOCATIONS = {
    "Delhi (Connaught Place)": (28.6304, 77.2177),
    "Mumbai (Bandra West)": (19.0544, 72.8402),
    "Bangalore (Indiranagar)": (12.9719, 77.6412),
    "Jaipur (Pink City)": (26.9124, 75.7873),
    "Hyderabad (Hitech City)": (17.4435, 78.3772),
    "Chennai (T. Nagar)": (13.0418, 80.2341),
    "Chandigarh (Sector 17)": (30.7414, 76.7681)
}

# --- THEMES ---
THEMES = {
    'Cyber': {
        'BG': (5, 8, 12),
        'MAP_BG': (10, 12, 18),
        'ROAD': (30, 40, 50),
        'PATH_FUTURE': (255, 255, 0), # Yellow
        'PATH_OK': (0, 255, 255),     # Cyan
        'PATH_SLOW': (255, 140, 0),   # Orange
        'PATH_JAM': (255, 0, 50),     # Red
        'BOT_BODY': (100, 100, 120),
        'AV_BODY': (255, 255, 255),
        'BLOCK': (200, 50, 50),
        'NODE_FILL': (20, 30, 40),
        'NODE_OUTLINE': (0, 255, 200),
        'TEXT': (220, 240, 255),
        'UI_PANEL': (20, 25, 35, 220),
        'UI_BORDER': (0, 100, 100)
    },
    'Neon': {
        'BG': (12, 0, 20),
        'MAP_BG': (10, 6, 18),
        'ROAD': (40, 25, 60),
        'PATH_FUTURE': (0, 255, 128),
        'PATH_OK': (255, 0, 255),
        'PATH_SLOW': (255, 200, 0),
        'PATH_JAM': (255, 60, 80),
        'BOT_BODY': (220, 100, 255),
        'AV_BODY': (0, 255, 200),
        'BLOCK': (255, 40, 120),
        'NODE_FILL': (30, 10, 40),
        'NODE_OUTLINE': (0, 240, 200),
        'TEXT': (200, 255, 230),
        'UI_PANEL': (30, 20, 40, 210),
        'UI_BORDER': (180, 0, 200)
    },
    'Classic': {
        'BG': (235, 235, 235),
        'MAP_BG': (245, 245, 245),
        'ROAD': (80, 80, 80),
        'PATH_FUTURE': (200, 180, 0),
        'PATH_OK': (0, 100, 220),
        'PATH_SLOW': (180, 100, 0),
        'PATH_JAM': (180, 0, 0),
        'BOT_BODY': (80, 80, 120),
        'AV_BODY': (30, 30, 30),
        'BLOCK': (160, 0, 0),
        'NODE_FILL': (230, 230, 230),
        'NODE_OUTLINE': (50, 50, 50),
        'TEXT': (20, 20, 20),
        'UI_PANEL': (240, 240, 240, 230),
        'UI_BORDER': (100, 100, 100)
    }
}

# Debug / tuning
DEBUG_HEAVY = False  # turn on for extra prints (slows performance)
# --- ASSETS ---
def create_detailed_car_surf(color):
    w, h = 40, 20
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, color, (0, 0, w, h), border_radius=4)
    pygame.draw.rect(s, (255, 255, 255), (0, 0, w, h), 2, border_radius=4)
    pygame.draw.rect(s, (0, 0, 0), (w-12, 2, 8, h-4), border_radius=2)
    pygame.draw.circle(s, (255, 255, 200), (w-2, 4), 3)
    pygame.draw.circle(s, (255, 255, 200), (w-2, h-4), 3)
    pygame.draw.circle(s, (255, 0, 0), (2, 4), 2)
    pygame.draw.circle(s, (255, 0, 0), (2, h-4), 2)
    return s

# --- UI CLASSES ---
class Panel:
    def __init__(self, x, y, w, h, title, theme, font_title):
        self.rect = pygame.Rect(x, y, w, h)
        self.title = title
        self.theme = theme
        self.surface = pygame.Surface((w, h), pygame.SRCALPHA)
        self.font_title = font_title
        self.render_bg()
    def render_bg(self):
        self.surface.fill((0,0,0,0))
        pygame.draw.rect(self.surface, self.theme['UI_PANEL'], (0,0,self.rect.w, self.rect.h), border_radius=12)
        pygame.draw.rect(self.surface, self.theme['UI_BORDER'], (0,0,self.rect.w, self.rect.h), 2, border_radius=12)
    def draw(self, screen):
        screen.blit(self.surface, self.rect.topleft)
        if self.title:
            t_surf = self.font_title.render(self.title, True, self.theme['TEXT'])
            t_rect = t_surf.get_rect(midtop=(self.rect.centerx, self.rect.y + 10))
            pygame.draw.rect(screen, self.theme['BG'], t_rect.inflate(20, 4), border_radius=4)
            screen.blit(t_surf, t_rect)

class Popup:
    def __init__(self, text, color, duration=2.0):
        self.text = text
        self.color = color
        self.duration = duration
        self.timer = duration
        self.font = pygame.font.SysFont("Arial", 32, bold=True)
        self.active = True

    def update(self, dt):
        self.timer -= dt / 1000.0
        if self.timer <= 0:
            self.active = False

    def draw(self, screen):
        if not self.active: return
        
        # Create text surface
        txt_surf = self.font.render(self.text, True, (255, 255, 255))
        padding = 20
        w = txt_surf.get_width() + padding * 2
        h = txt_surf.get_height() + padding * 2
        
        # Center of screen
        cx, cy = screen.get_width() // 2, screen.get_height() // 2
        rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
        
        # Draw box
        # Shadow
        pygame.draw.rect(screen, (0,0,0, 100), rect.move(4, 4), border_radius=10)
        # Background
        pygame.draw.rect(screen, (20, 20, 30), rect, border_radius=10)
        # Border (using the specific alert color)
        pygame.draw.rect(screen, self.color, rect, 3, border_radius=10)
        
        # Draw text
        screen.blit(txt_surf, txt_surf.get_rect(center=rect.center))

class SimpleSlider:
    def __init__(self, x, y, w, h, min_val, max_val, initial, label, font):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = min_val; self.max_val = max_val
        self.val = initial; self.label = label
        self.dragging = False
        self.font = font
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.inflate(10,10).collidepoint(event.pos): self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP: self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mx = max(self.rect.left, min(event.pos[0], self.rect.right))
            ratio = (mx - self.rect.left) / self.rect.width
            self.val = self.min_val + ratio * (self.max_val - self.min_val)
    def draw(self, screen, theme):
        lbl = self.font.render(f"{self.label}: {int(self.val)}", True, theme['TEXT'])
        screen.blit(lbl, (self.rect.x, self.rect.y - 20))
        pygame.draw.rect(screen, (50,50,50), self.rect, border_radius=5)
        ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width * ratio, self.rect.height)
        pygame.draw.rect(screen, theme['PATH_OK'], fill_rect, border_radius=5)
        pygame.draw.circle(screen, (255,255,255), (int(self.rect.x + self.rect.width*ratio), self.rect.centery), 8)

# --- GLOBAL LAYOUT ---
class Layout:
    def __init__(self, w, h):
        self.update(w, h)
    def update(self, w, h):
        self.screen_w = w; self.screen_h = h
        self.map_w = int(w * 0.50)
        self.graph_w = int(w * 0.25)
        self.dash_w = w - self.map_w - self.graph_w
        self.map_rect = pygame.Rect(0, 0, self.map_w, h)
        self.graph_rect = pygame.Rect(self.map_w, 0, self.graph_w, h)
        self.dash_rect = pygame.Rect(self.map_w + self.graph_w, 0, self.dash_w, h)

# --- TRAFFIC & MAP (with caches) ---
class TrafficBot:
    def __init__(self, map_eng):
        self.map = map_eng
        self.curr = random.choice(list(map_eng.nodes.keys()))
        self.pos = list(map_eng.nodes[self.curr])
        self.target = None
    def update(self, speed_mod):
        if not self.target:
            nbrs = list(self.map.G_proj.neighbors(self.curr))
            if nbrs: self.target = random.choice(nbrs)
            else: return
        tx, ty = self.map.nodes[self.target]
        dx, dy = tx - self.pos[0], ty - self.pos[1]
        dist = math.hypot(dx, dy)
        msp = speed_mod * 0.5
        if dist < msp:
            self.curr = self.target; self.pos = [tx, ty]; self.target = None
        else:
            self.pos[0] += (dx/dist)*msp; self.pos[1] += (dy/dist)*msp

class MapEngine:
    def __init__(self, location, layout):
        print(f"Loading {location}...")
        # Adjust 'dist' to control graph size (lower dist => faster load + higher FPS)
        self.G = ox.graph_from_point(LOCATIONS[location], dist=1000, network_type='drive')
        self.G_proj = ox.project_graph(self.G)
        self.nodes = {}; self.layout = layout
        self.min_x, self.max_x, self.min_y, self.max_y = 0,0,0,0
        self.normalize_coords()
        self.bots = []
        self.edge_density = {}
        self.blocked_edges = []
        self.cached_edges = list(self.G_proj.edges(keys=True, data=True))
        # Caching helpers
        self.phys_path_cache = {}   # {(u,v): [node_sequence], ...} key sorted (u,v)
        self._G_abs_cached = None
        self._last_edge_density_snapshot = {}
    def normalize_coords(self):
        xs = [d['x'] for n, d in self.G_proj.nodes(data=True)]
        ys = [d['y'] for n, d in self.G_proj.nodes(data=True)]
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)
        avail_w = max(200, self.layout.map_w)
        avail_h = max(200, self.layout.screen_h)
        # keep small margin, scale to fit
        scale = min(avail_w / (self.max_x - self.min_x), avail_h / (self.max_y - self.min_y)) * 0.9
        off_x = (avail_w - (self.max_x - self.min_x) * scale) / 2
        off_y = (avail_h - (self.max_y - self.min_y) * scale) / 2
        self.scale = scale; self.off_x = off_x; self.off_y = off_y
        for n, d in self.G_proj.nodes(data=True):
            sx = (d['x'] - self.min_x)*scale + off_x
            sy = self.layout.screen_h - ((d['y'] - self.min_y)*scale + off_y)
            self.nodes[n] = (sx, sy)
    def get_phys_path(self, u, v):
        key = tuple(sorted((u, v)))
        if key in self.phys_path_cache:
            return self.phys_path_cache[key]
        try:
            path = nx.shortest_path(self.G_proj, u, v, weight='length')
            self.phys_path_cache[key] = path
            return path
        except Exception:
            return None
    def invalidate_phys_cache(self):
        self.phys_path_cache.clear()
        self._G_abs_cached = None
    def build_abstract_graph(self, graph_sys, force=False):
        # Rebuild G_abs only when edge_density changed or forced
        if not force and self._last_edge_density_snapshot == self.edge_density and self._G_abs_cached is not None:
            return self._G_abs_cached
        G_abs = nx.Graph()
        for u, v in graph_sys.connections:
            phys_path = self.get_phys_path(u, v)
            if not phys_path: continue
            traffic = 0
            for k in range(len(phys_path)-1):
                key = tuple(sorted((phys_path[k], phys_path[k+1])))
                traffic += self.edge_density.get(key, 0)
            cost = len(phys_path) * (1 + (traffic ** 3))
            G_abs.add_edge(u, v, weight=cost)
        self._G_abs_cached = G_abs
        self._last_edge_density_snapshot = dict(self.edge_density)
        return G_abs
    def update(self, speed, target_bots, dt):
        while len(self.bots) < target_bots: self.bots.append(TrafficBot(self))
        while len(self.bots) > target_bots: self.bots.pop()
        self.edge_density = {}
        for b in self.bots:
            b.update(speed)
            if b.target:
                k = tuple(sorted((b.curr, b.target)))
                self.edge_density[k] = self.edge_density.get(k, 0) + 1
        # we don't automatically invalidate phys cache for edge_density changes,
        # only for structural changes like blocked edges. build_abstract_graph checks edge_density snapshot.
    def block_at(self, pos, cam):
        wx, wy = cam.to_world(*pos)
        best_e, min_d = None, 50/cam.zoom
        for u, v, k, d in self.cached_edges:
            p1 = self.nodes[u]; p2 = self.nodes[v]
            mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
            d_ = math.hypot(wx-mx, wy-my)
            if d_ < min_d:
                min_d = d_; best_e = (u,v,k)
        if best_e:
            if best_e in self.blocked_edges: self.blocked_edges.remove(best_e)
            else: self.blocked_edges.append(best_e)
            self.invalidate_phys_cache()
    def draw(self, screen, cam, theme, abstract_graph, path=None, waypoints=None, av=None):
        t = theme
        pygame.draw.rect(screen, t['MAP_BG'], self.layout.map_rect)
        view_rect = self.layout.map_rect
        # Roads
        for u, v, k, d in self.cached_edges:
            s1 = cam.to_screen(*self.nodes[u])
            s2 = cam.to_screen(*self.nodes[v])
            if not view_rect.collidepoint(s1) and not view_rect.collidepoint(s2): continue
            if (u,v,k) in self.blocked_edges:
                pygame.draw.line(screen, t['BLOCK'], s1, s2, 5)
                continue
            k_dens = tuple(sorted((u,v)))
            crowd = self.edge_density.get(k_dens, 0)
            color = t['ROAD']
            width = max(1, int(2 * cam.zoom))
            if crowd > 2: color = t['PATH_SLOW']
            if crowd > 6: color = t['PATH_JAM']
            pygame.draw.line(screen, color, s1, s2, width)
        # Draw PROJECTED PATH on Map (FUTURE)
        if av and av.active and len(av.projected_path) > 1:
            pts = []
            for i in range(len(av.projected_path)-1):
                u, v = av.projected_path[i], av.projected_path[i+1]
                phys_path = self.get_phys_path(u, v)
                if phys_path:
                    segment_pts = [cam.to_screen(*self.nodes[n]) for n in phys_path]
                    pts.extend(segment_pts)
            if len(pts) > 1:
                pygame.draw.lines(screen, t['PATH_FUTURE'], False, pts, int(2*cam.zoom))
        # Active Path Glow (Cyan)
        if path and len(path) > 1:
            pts = [cam.to_screen(*p) for p in path]
            if len(pts) > 1:
                pygame.draw.lines(screen, t['PATH_OK'], False, pts, int(6*cam.zoom))
                pygame.draw.lines(screen, (255, 255, 255), False, pts, int(2*cam.zoom))
        # Traffic bots
        for b in self.bots:
            sx, sy = cam.to_screen(*b.pos)
            if view_rect.collidepoint((sx,sy)):
                pygame.draw.circle(screen, t['BOT_BODY'], (int(sx), int(sy)), int(2*cam.zoom))
        # Abstract node markers (small)
        font = pygame.font.SysFont("Arial", 14, bold=True)
        for n, label in abstract_graph.node_mapping.items():
            if n not in self.nodes: continue
            sx, sy = cam.to_screen(*self.nodes[n])
            if view_rect.collidepoint((sx,sy)):
                selected = n in waypoints
                bg_col = (255, 255, 255) if not selected else t['PATH_FUTURE']
                if av and n == av.current_node: bg_col = t['PATH_OK']
                
                # Draw Node Circle
                pygame.draw.circle(screen, bg_col, (int(sx), int(sy)), 6)
                if selected: pygame.draw.circle(screen, (0,0,0), (int(sx), int(sy)), 8, 2)
                
                # Draw Node Label with Background
                lbl_surf = font.render(f"{label}", True, t['TEXT'])
                lbl_rect = lbl_surf.get_rect(midbottom=(sx, sy - 10))
                
                # Background box for text
                pygame.draw.rect(screen, t['BG'], lbl_rect.inflate(8, 4), border_radius=4)
                pygame.draw.rect(screen, t['NODE_OUTLINE'], lbl_rect.inflate(8, 4), 1, border_radius=4)
                
                screen.blit(lbl_surf, lbl_rect)

# --- ABSTRACT GRAPH ---
class AbstractGraph:
    def __init__(self, map_eng, max_nodes=12):
        self.map = map_eng
        self.max_nodes = max_nodes
        self.abstract_nodes = []
        self.node_mapping = {}
        self.connections = []
        self.generate_abstraction()
    def generate_abstraction(self):
        # pick nodes with degree > 2 as candidates
        candidates = sorted([n for n in self.map.G_proj.nodes() if self.map.G_proj.degree(n) > 2],
                            key=lambda n: self.map.G_proj.degree(n), reverse=True)
        selected = []
        min_dist = 250
        for c in candidates:
            if len(selected) >= self.max_nodes: break
            cx, cy = self.map.nodes[c]
            if all(math.hypot(cx-self.map.nodes[s][0], cy-self.map.nodes[s][1]) > min_dist for s in selected):
                selected.append(c)
        self.abstract_nodes = selected
        labels = list(string.ascii_uppercase)
        self.node_mapping = {n: labels[i] for i, n in enumerate(self.abstract_nodes)}
        self.connections = []
        for i, u in enumerate(self.abstract_nodes):
            for j, v in enumerate(self.abstract_nodes):
                if i >= j: continue
                # build connection only if physical path is reasonably short
                phys_path = self.map.get_phys_path(u, v)
                if phys_path and len(phys_path) < 70:
                    self.connections.append((u, v))
    def get_abstract_node_at(self, pos, cam):
        wx, wy = cam.to_world(*pos)
        best, min_d = None, 60 / cam.zoom
        for n in self.abstract_nodes:
            nx_, ny_ = self.map.nodes[n]
            d = math.hypot(nx_-wx, ny_-wy)
            if d < min_d: min_d = d; best = n
        return best
    def draw(self, screen, rect, theme, av, waypoints, map_eng):
        pygame.draw.rect(screen, (15, 18, 25), rect)
        if not self.abstract_nodes: return
        xs = [self.map.nodes[n][0] for n in self.abstract_nodes]
        ys = [self.map.nodes[n][1] for n in self.abstract_nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        margin = 60
        scale_x = (rect.width - 2*margin) / ((max_x - min_x) if max_x!=min_x else 1)
        scale_y = (rect.height - 2*margin) / ((max_y - min_y) if max_y!=min_y else 1)
        def to_gs(nid):
            rx, ry = self.map.nodes[nid]
            sx = rect.left + margin + (rx - min_x) * scale_x
            sy = rect.top + margin + (ry - min_y) * scale_y
            return int(sx), int(sy)
        font_l = pygame.font.SysFont("Arial", 16, bold=True)
        font_s = pygame.font.SysFont("Arial", 10)
        for u, v in self.connections:
            s1 = to_gs(u); s2 = to_gs(v)
            is_active_leg = False; is_future_leg = False
            if av.active and av.state == "MOVING":
                curr_start = av.current_node
                curr_target = av.next_node_target
                if (u == curr_start and v == curr_target) or (u == curr_target and v == curr_start):
                    is_active_leg = True
            if av.active and len(av.projected_path) > 1:
                for k in range(len(av.projected_path) - 1):
                    pu, pv = av.projected_path[k], av.projected_path[k+1]
                    if (u == pu and v == pv) or (u == pv and v == pu):
                        if not is_active_leg: is_future_leg = True
            crowd_score = 0; dist_score = 0
            phys_path = map_eng.get_phys_path(u, v)
            if phys_path:
                dist_score = len(phys_path)
                for k in range(len(phys_path)-1):
                    key = tuple(sorted((phys_path[k], phys_path[k+1])))
                    crowd_score += map_eng.edge_density.get(key, 0)
            col = (60, 80, 100); width = 2
            if crowd_score > 2: col = theme['PATH_SLOW']
            if crowd_score > 8: col = theme['PATH_JAM']
            if is_active_leg:
                col = theme['PATH_OK']; width = 5
            elif is_future_leg:
                col = theme['PATH_FUTURE']; width = 3
            pygame.draw.line(screen, col, s1, s2, width)
            mid = ((s1[0]+s2[0])//2, (s1[1]+s2[1])//2)
            pygame.draw.circle(screen, theme['BG'], mid, 12)
            pygame.draw.circle(screen, col, mid, 12, 1)
            weight_val = int(dist_score/10 + crowd_score * 5)
            t_col = (200, 200, 200)
            if crowd_score > 5: t_col = (255, 100, 100)
            t = font_s.render(str(weight_val), True, t_col)
            screen.blit(t, t.get_rect(center=mid))
        for n in self.abstract_nodes:
            sx, sy = to_gs(n)
            is_start = False; is_end = False; is_on_path = False
            if av.active:
                if n == av.final_dest: is_end = True
                if n in av.projected_path: is_on_path = True
                if n == av.current_node: is_start = True
            fill = theme['NODE_FILL']
            if is_on_path: fill = theme['PATH_FUTURE']
            if is_start: fill = theme['PATH_OK']
            if is_end: fill = (255, 200, 200)
            rad = 20 if (is_start or is_end) else 16
            if is_start and av.state == "MOVING":
                pulse = (math.sin(time.time()*10)+1)*0.5
                rad = 20 + int(3*pulse)
            pygame.draw.circle(screen, fill, (sx, sy), rad)
            pygame.draw.circle(screen, theme['NODE_OUTLINE'], (sx, sy), rad, 2)
            lbl = self.node_mapping[n]
            txt_col = (0,0,0) if (is_start or is_end or is_on_path) else (255,255,255)
            txt = font_l.render(lbl, True, txt_col)
            screen.blit(txt, txt.get_rect(center=(sx, sy)))

# --- CAMERA ---
class Camera:
    def __init__(self, layout):
        self.off_x = 0; self.off_y = 0; self.zoom = 1.0
        self.layout = layout; self.drag_start = None
    def to_screen(self, wx, wy):
        sx = (wx * self.zoom) + self.off_x
        sy = (wy * self.zoom) + self.off_y
        return sx, sy
    def to_world(self, sx, sy):
        wx = (sx - self.off_x) / self.zoom
        wy = (sy - self.off_y) / self.zoom
        return wx, wy
    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.layout.map_rect.collidepoint(event.pos):
                if event.button == 2: self.drag_start = event.pos
                elif event.button == 4: # Zoom in
                    mx, my = event.pos
                    wx, wy = self.to_world(mx, my)
                    self.zoom = min(self.zoom * 1.1, 5.0)
                    self.off_x = mx - wx * self.zoom
                    self.off_y = my - wy * self.zoom
                elif event.button == 5: # Zoom out
                    mx, my = event.pos
                    wx, wy = self.to_world(mx, my)
                    self.zoom = max(self.zoom * 0.9, 0.5)
                    self.off_x = mx - wx * self.zoom
                    self.off_y = my - wy * self.zoom
        elif event.type == pygame.MOUSEBUTTONUP: self.drag_start = None
        elif event.type == pygame.MOUSEMOTION and self.drag_start:
            self.off_x += event.pos[0] - self.drag_start[0]
            self.off_y += event.pos[1] - self.drag_start[1]
            self.drag_start = event.pos

# --- DASHBOARD ---
class Dashboard:
    def __init__(self, layout, theme):
        self.layout = layout
        self.theme = theme
        self.font_h = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_b = pygame.font.SysFont("Courier New", 12, bold=True)
        r = layout.dash_rect
        self.p_ctrl = Panel(r.x + 10, 20, r.w - 20, 150, "CONTROLS", theme, self.font_h)
        self.p_leg = Panel(r.x + 10, 180, r.w - 20, 180, "LEGEND", theme, self.font_h)
        self.p_mat = Panel(r.x + 10, 370, r.w - 20, r.h - 390, "CONNECTIVITY MATRIX", theme, self.font_h)
        self.slider_speed = SimpleSlider(r.x + 30, 60, r.w - 60, 20, 1, 10, 4, "Speed", self.font_b)
        self.slider_crowd = SimpleSlider(r.x + 30, 110, r.w - 60, 20, 0, 200, 60, "Traffic", self.font_b)
    def handle_input(self, event):
        self.slider_speed.handle_event(event)
        self.slider_crowd.handle_event(event)
    def draw(self, screen, abstract_graph, map_eng, av):
        self.p_ctrl.draw(screen)
        self.p_leg.draw(screen)
        self.p_mat.draw(screen)
        self.slider_speed.draw(screen, self.theme)
        self.slider_crowd.draw(screen, self.theme)
        lx = self.p_leg.rect.x + 20
        ly = self.p_leg.rect.y + 40
        items = [
            (self.theme['PATH_OK'], "Active Path"),
            (self.theme['PATH_FUTURE'], "Future Leg"),
            (self.theme['PATH_JAM'], "Traffic Jam"),
            ((255, 255, 255), "Nodes"),
        ]
        for col, txt in items:
            pygame.draw.circle(screen, col, (lx, ly), 6)
            s = self.font_b.render(txt, True, self.theme['TEXT'])
            screen.blit(s, (lx + 20, ly - 7))
            ly += 25
        if av.active:
            s_txt = f"Status: {av.alert}"
            screen.blit(self.font_h.render(s_txt, True, self.theme['PATH_OK']), (lx, ly+10))
        mx = self.p_mat.rect.x + 15
        my = self.p_mat.rect.y + 50
        nodes = abstract_graph.abstract_nodes[:8]
        cell_s = 28
        for i, n in enumerate(nodes):
            lbl = abstract_graph.node_mapping[n]
            t = self.font_b.render(lbl, True, self.theme['TEXT'])
            screen.blit(t, (mx + (i+1)*cell_s + 10, my))
            screen.blit(t, (mx, my + (i+1)*cell_s))
        for r, u in enumerate(nodes):
            for c, v in enumerate(nodes):
                cr = pygame.Rect(mx + (c+1)*cell_s, my + (r+1)*cell_s, cell_s, cell_s)
                is_connected = (u,v) in abstract_graph.connections or (v,u) in abstract_graph.connections
                if u == v:
                    color = (50, 50, 60); val = ""
                elif is_connected:
                    try:
                        phys_path = map_eng.get_phys_path(u, v)
                        dist = (len(phys_path)//10) if phys_path else 0
                        traffic = 0
                        if phys_path:
                            for k in range(len(phys_path)-1):
                                key = tuple(sorted((phys_path[k], phys_path[k+1])))
                                traffic += map_eng.edge_density.get(key, 0)
                        val = str(dist + traffic*5)
                        if traffic > 10: color = self.theme['PATH_JAM']
                        elif traffic > 2: color = self.theme['PATH_SLOW']
                        else: color = (0, 100, 50)
                    except:
                        color = (30, 30, 30); val = "?"
                else:
                    color = (20, 20, 25); val = ""
                pygame.draw.rect(screen, color, cr)
                pygame.draw.rect(screen, (60,60,60), cr, 1)
                if val:
                    t = self.font_b.render(val, True, (255,255,255))
                    screen.blit(t, (cr.x+4, cr.y+6))

# --- AV LOGIC (with periodic reroute checks) ---
class AV:
    def __init__(self, map_eng, cam):
        self.map = map_eng; self.cam = cam
        self.pos = [0,0]; self.active = False
        self.current_node = None
        self.next_node_target = None
        self.final_dest = None
        self.projected_path = []
        self.path_coords = []
        self.coord_idx = 0
        self.angle = 0; self.state = "IDLE"
        self.wait_timer = 0
        self.alert = "Idle"
        self.sprite = create_detailed_car_surf((0, 255, 255))
        self.recalc_interval = 0.5
        self._last_recalc_t = time.time()
        self.events = [] # List to store popup events: (text, color)
        
    def start(self, user_waypoints):
        if len(user_waypoints) < 2: return
        self.current_node = user_waypoints[0]
        self.final_dest = user_waypoints[-1]
        self.pos = list(self.map.nodes[self.current_node])
        self.active = True
        self.calculate_mission_and_go()
    def calculate_mission_and_go(self):
        graph_sys = self.map.layout.graph_sys
        G_abs = self.map.build_abstract_graph(graph_sys, force=False)
        if G_abs is None or self.current_node not in G_abs.nodes or self.final_dest not in G_abs.nodes:
            # try forced rebuild
            G_abs = self.map.build_abstract_graph(graph_sys, force=True)
            if G_abs is None or self.current_node not in G_abs.nodes or self.final_dest not in G_abs.nodes:
                self.alert = "No Route!"; self.active = False; return
        # shortest on abstract
        try:
            raw_proj = nx.shortest_path(G_abs, self.current_node, self.final_dest, weight='weight')
        except Exception:
            self.alert = "No Route!"; self.active = False; return
        if len(raw_proj) < 2:
            self.state = "FINISHED"; self.alert = "Arrived"; self.active = False
            self.events.append(("DESTINATION REACHED!", (50, 255, 50))) # Success Event
            return
        # evaluate best neighbor greedily using current G_abs (fast)
        try:
            best_total = None; best_neighbor = None
            for nbr in G_abs.neighbors(self.current_node):
                edge_cost = G_abs[self.current_node][nbr]['weight']
                try:
                    rem_cost = nx.shortest_path_length(G_abs, nbr, self.final_dest, weight='weight')
                except:
                    rem_cost = float('inf')
                total = edge_cost + rem_cost
                if best_total is None or total < best_total:
                    best_total = total; best_neighbor = nbr
            chosen_next = raw_proj[1]
            switched = False
            if best_neighbor is not None and best_neighbor != chosen_next:
                # attempt to use best_neighbor instead
                phys_nodes = self.map.get_phys_path(self.current_node, best_neighbor)
                if phys_nodes:
                    try:
                        tail = nx.shortest_path(G_abs, best_neighbor, self.final_dest, weight='weight')
                        self.projected_path = [self.current_node] + tail
                        chosen_next = best_neighbor
                        switched = True
                    except:
                        self.projected_path = raw_proj
                else:
                    self.projected_path = raw_proj
            else:
                self.projected_path = raw_proj
            self.next_node_target = chosen_next
            # Build human-readable alert
            labels = [graph_sys.node_mapping.get(n, '?') for n in self.projected_path]
            self.alert = "Route: " + " > ".join(labels[:6])
            if switched: self.alert += " (rerouted locally)"
        except Exception:
            self.alert = "Routing Error"; self.active = False; return
        # Build physical coordinates for first leg with dynamic costs
        try:
            # annotate edges with curr_cost for heavy edges
            for u_node, v_node, k, d in self.map.G_proj.edges(keys=True, data=True):
                t = self.map.edge_density.get(tuple(sorted((u_node, v_node))), 0)
                d['curr_cost'] = d.get('length', 1) * (1 + (t**3))
            phys_nodes = nx.shortest_path(self.map.G_proj, self.current_node, self.next_node_target, weight='curr_cost')
            self.path_coords = [self.map.nodes[n] for n in phys_nodes]
            self.coord_idx = 0
            lbl_next = graph_sys.node_mapping.get(self.next_node_target, "?")
            self.alert = f"Routing to {lbl_next} | {self.alert}"
            self.state = "MOVING"
        except Exception:
            # blocked or no path
            self.alert = "Road Blocked"; self.active = False
    def check_dynamic_reroute(self):
        """Check if a better neighbor exists; if so, switch mid-leg (cheap, uses caches)"""
        graph_sys = self.map.layout.graph_sys
        G_abs = self.map.build_abstract_graph(graph_sys, force=False)
        if G_abs is None or self.current_node not in G_abs.nodes: return False
        try:
            raw_proj = nx.shortest_path(G_abs, self.current_node, self.final_dest, weight='weight')
        except:
            return False
        best_total = None; best_neighbor = None
        for nbr in G_abs.neighbors(self.current_node):
            edge_cost = G_abs[self.current_node][nbr]['weight']
            try:
                rem_cost = nx.shortest_path_length(G_abs, nbr, self.final_dest, weight='weight')
            except:
                rem_cost = float('inf')
            total = edge_cost + rem_cost
            if best_total is None or total < best_total:
                best_total = total; best_neighbor = nbr
        chosen_next = raw_proj[1]
        if best_neighbor is not None and best_neighbor != chosen_next:
            phys_nodes = self.map.get_phys_path(self.current_node, best_neighbor)
            if phys_nodes:
                self.path_coords = [self.map.nodes[n] for n in phys_nodes]
                self.coord_idx = 0
                self.next_node_target = best_neighbor
                self.projected_path = nx.shortest_path(G_abs, self.current_node, self.final_dest, weight='weight')
                self.alert = f"Rerouted -> {graph_sys.node_mapping.get(best_neighbor,'?')} (mid-leg)"
                return True
        return False
    def update(self, speed, dt):
        if not self.active: return
        now = time.time()
        if self.state == "WAITING":
            self.wait_timer -= dt / 1000.0
            lbl = self.map.layout.graph_sys.node_mapping[self.current_node]
            self.alert = f"Scanning at {lbl}... {int(self.wait_timer)}"
            if self.wait_timer <= 0:
                # recalc with fresh traffic snapshot
                self.calculate_mission_and_go()
            return
        if self.state == "MOVING":
            # periodic mid-leg check
            if now - self._last_recalc_t > self.recalc_interval:
                self._last_recalc_t = now
                # build_abstract_graph will only rebuild if edge_density changed snapshot
                try:
                    self.check_dynamic_reroute()
                except Exception:
                    pass
            if self.coord_idx >= len(self.path_coords) - 1:
                # arrived at the end of the current physical leg
                self.current_node = self.next_node_target
                
                # Check if this is the final destination
                if self.current_node == self.final_dest:
                    self.state = "FINISHED"; self.alert = "Arrived"; self.active = False
                    self.events.append(("DESTINATION REACHED!", (50, 255, 50))) # Success Event
                    return
                
                # Arrived at intermediate node
                node_lbl = self.map.layout.graph_sys.node_mapping.get(self.current_node, "?")
                self.events.append((f"Reached Node {node_lbl}", (255, 255, 0))) # Intermediate Event
                
                self.state = "WAITING"
                self.wait_timer = 1.0
                return
            target = self.path_coords[self.coord_idx + 1]
            dx, dy = target[0]-self.pos[0], target[1]-self.pos[1]
            dist = math.hypot(dx, dy)
            current_speed = (speed * 2)
            if dist <= current_speed:
                self.pos = list(target); self.coord_idx += 1
            else:
                self.pos[0] += (dx/dist)*current_speed
                self.pos[1] += (dy/dist)*current_speed
                target_angle = -math.degrees(math.atan2(dy, dx))
                diff = (target_angle - self.angle + 180) % 360 - 180
                self.angle += diff * 0.2
    def draw(self, screen, theme):
        if not self.active: return
        sx, sy = self.cam.to_screen(*self.pos)
        if self.cam.layout.map_rect.collidepoint((sx,sy)):
            rot_sprite = pygame.transform.rotate(self.sprite, self.angle)
            screen.blit(rot_sprite, rot_sprite.get_rect(center=(sx,sy)))
            # small text using a shared font
            font = pygame.font.SysFont("Arial", 12, bold=True)
            txt = font.render(self.alert, True, (255, 255, 255))
            screen.blit(txt, (sx - txt.get_width()//2, sy - 30))

# --- MAIN / UI flow ---
def run_sim(location):
    pygame.init()
    layout = Layout(WIDTH, HEIGHT)
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption(f"Advanced AV Network - {location}")
    clock = pygame.time.Clock()
    theme = THEMES['Cyber']
    map_eng = MapEngine(location, layout)
    abstract_graph = AbstractGraph(map_eng)
    layout.graph_sys = abstract_graph
    cam = Camera(layout)
    av = AV(map_eng, cam)
    dash = Dashboard(layout, theme)
    running = True
    user_selection = []
    
    # Popup management
    current_popup = None
    
    last_fps_report = time.time()
    while running:
        dt = clock.tick(FPS)
        sim_speed = dash.slider_speed.val
        target_bots = int(dash.slider_crowd.val)
        map_eng.update(sim_speed, target_bots, dt)
        av.update(sim_speed, dt)
        
        # Check for AV events to trigger popups
        if av.events:
            msg, color = av.events.pop(0)
            # Duration: longer for final destination, shorter for intermediate
            duration = 3.0 if "DESTINATION" in msg else 1.0 
            current_popup = Popup(msg, color, duration)
        
        if current_popup:
            current_popup.update(dt)
            if not current_popup.active:
                current_popup = None

        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            if e.type == pygame.VIDEORESIZE:
                layout.update(e.w, e.h)
                map_eng.normalize_coords()
                # regenerate UI panels with new layout
                dash = Dashboard(layout, theme)
            dash.handle_input(e)
            cam.handle_input(e)
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 3:
                    mx, my = e.pos
                    if layout.map_rect.collidepoint((mx,my)):
                        n = abstract_graph.get_abstract_node_at((mx,my), cam)
                        if n:
                            if n in user_selection: user_selection.remove(n)
                            else: user_selection.append(n)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE: av.start(user_selection)
                if e.key == pygame.K_r: user_selection = []; av.active = False
                if e.key == pygame.K_b:
                    map_eng.block_at(pygame.mouse.get_pos(), cam)
                # theme switch
                if e.key == pygame.K_1: theme = THEMES['Cyber']; dash.theme = theme
                if e.key == pygame.K_2: theme = THEMES['Neon']; dash.theme = theme
                if e.key == pygame.K_3: theme = THEMES['Classic']; dash.theme = theme
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False
        screen.fill(theme['BG'])
        path_seg = av.path_coords if av.active and av.state == "MOVING" else []
        map_eng.draw(screen, cam, theme, abstract_graph, path_seg, user_selection, av)
        av.draw(screen, theme)
        abstract_graph.draw(screen, layout.graph_rect, theme, av, user_selection, map_eng)
        dash.draw(screen, abstract_graph, map_eng, av)
        
        # Draw popup if active (on top of everything)
        if current_popup:
            current_popup.draw(screen)

        # separators
        pygame.draw.line(screen, theme['UI_BORDER'], (layout.map_w, 0), (layout.map_w, layout.screen_h), 2)
        pygame.draw.line(screen, theme['UI_BORDER'], (layout.map_w + layout.graph_w, 0), (layout.map_w + layout.graph_w, layout.screen_h), 2)
        fps_txt = pygame.font.SysFont("Arial", 12).render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0))
        screen.blit(fps_txt, (10, 10))
        pygame.display.flip()
        # occasional debug print
        if DEBUG_HEAVY and time.time() - last_fps_report > 3.0:
            last_fps_report = time.time()
            print(f"[debug] fps={clock.get_fps():.1f}, bots={len(map_eng.bots)}, edge_density_len={len(map_eng.edge_density)}")
    pygame.quit()
    sys.exit()

def menu():
    pygame.init()
    s = pygame.display.set_mode((700, 520))
    pygame.display.set_caption("AV Simulator - Select City / Theme")
    m = pygame_menu.Menu('Select City', 700, 520, theme=pygame_menu.themes.THEME_DARK)
    for l in LOCATIONS:
        m.add.button(l, run_sim, l)
    m.add.label("Themes in-sim: press 1=Cyber  2=Neon  3=Classic")
    m.add.label("Controls: Right-click nodes to select, SPACE to start, B to block edge, R to reset")
    m.add.button('Exit', pygame_menu.events.EXIT)
    m.mainloop(s)

if __name__ == "__main__":
    menu()