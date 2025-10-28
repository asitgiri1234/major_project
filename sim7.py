#!/usr/bin/env python3
import sys
import random
import math
import time
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Set

try:
    import pygame
except Exception as e:
    print("This script requires pygame. Install it with: pip install pygame")
    raise

# ---- CONFIG ----
GRID_COLS = 8
GRID_ROWS_ONSCREEN = 8
TOTAL_ROAD_ROWS = 30
CELL = 90
WIDTH = GRID_COLS * CELL
HEIGHT = GRID_ROWS_ONSCREEN * CELL

SCHEM_CELL = 20
SCHEM_WIDTH = GRID_COLS * SCHEM_CELL
SCHEM_HEIGHT = TOTAL_ROAD_ROWS * SCHEM_CELL
SCHEM_OFFSET_Y = (HEIGHT - SCHEM_HEIGHT) // 2
SCHEM_BORDER_THICK = 3

MATRIX_CELL = 20
MATRIX_WIDTH = GRID_COLS * MATRIX_CELL
MATRIX_HEIGHT = TOTAL_ROAD_ROWS * MATRIX_CELL
MATRIX_OFFSET_Y = SCHEM_OFFSET_Y
MATRIX_BORDER_THICK = 3

PLAN_CELL = 30
PLAN_SIZE = 9
PLAN_WIDTH = PLAN_SIZE * PLAN_CELL
PLAN_HEIGHT = PLAN_SIZE * PLAN_CELL
PLAN_OFFSET_Y = (HEIGHT - PLAN_HEIGHT) // 2
PLAN_BORDER_THICK = 3

LOG_PANEL_WIDTH = 300
LOG_PANEL_HEIGHT = HEIGHT
LOG_PANEL_X = WIDTH + SCHEM_WIDTH + MATRIX_WIDTH + PLAN_WIDTH
LOG_PANEL_BG = (18, 18, 18)
LOG_TEXT_COLOR = (220, 220, 220)
LOG_FONT_SIZE = 12

FPS = 60
STEP_SECONDS = 0.5
STEP_FRAMES = max(1, int(FPS * STEP_SECONDS))
SPAWN_PROB = 0.68
POTHOLE_PROB = 0.15
RESET_DELAY = 1.5

# Colors
AV_COLOR = (24, 120, 210)
OBSTACLE_COLOR = (200, 40, 40)
WHITE = (240, 240, 240)
BLACK = (16, 16, 20)
ROAD = (30, 33, 38)
LANE = (110, 110, 110)
HUD_BG = (18, 18, 18, 180)
SHADOW = (10, 10, 15, 100)
BOUNDING = (244, 208, 63)
POTHOLE_COLOR = (255, 215, 0)
POTHOLE_DARK = (20, 20, 20)
CRACK_GRAY = (70, 70, 70)
MATRIX_TEXT = (0, 255, 0)
GRID_LINE = (100, 100, 100)
ARROW_COLOR = (50, 205, 50)
PAUSE_COLOR = (255, 255, 255)

FONT_LABEL_SIZE = 14
TITLE_FONT_SIZE = 16
HUD_FONT_SIZE = 14

def cell_to_pixel(col: float, row: float, road_offset: float) -> Tuple[float, float]:
    x = col * CELL + CELL // 2
    y = (row - road_offset) * CELL + CELL // 2
    return x, y

def inside(col: float, row: float) -> bool:
    return 0 <= int(col) < GRID_COLS and 0 <= int(row) < TOTAL_ROAD_ROWS

def ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)

@dataclass
class Vehicle:
    col: float
    row: float
    kind: str
    dir: int = 0
    target: Optional[Tuple[int, int]] = None
    anim_frame: float = 0.0
    def pos(self) -> Tuple[int, int]:
        return (int(self.col), int(self.row))
    def is_animating(self) -> bool:
        return self.target is not None and self.anim_frame < STEP_FRAMES

def init_pygame_or_exit() -> pygame.Surface:
    pygame.init()
    pygame.font.init()
    try:
        screen = pygame.display.set_mode((WIDTH + SCHEM_WIDTH + MATRIX_WIDTH + PLAN_WIDTH + LOG_PANEL_WIDTH, HEIGHT))
    except pygame.error as e:
        print("Failed to open window:", e)
        sys.exit(1)
    pygame.display.set_caption("Autonomous Vehicle Obstacle Avoidance System")
    return screen

def try_load_images(logs):
    try:
        av_img = pygame.image.load("av_vehicle.png").convert_alpha()
        obstacle_img = pygame.image.load("obstacle_vehicle.png").convert_alpha()
        size = int(CELL * 0.78)
        av_img = pygame.transform.smoothscale(av_img, (size, size))
        obstacle_img = pygame.transform.smoothscale(obstacle_img, (size, size))
        logs.append("Successfully loaded vehicle images")
        return av_img, obstacle_img
    except Exception as e:
        logs.append(f"Failed to load images: {e}. Using fallback shapes.")
        return None, None

def spawn_potholes(occupied: Set[Tuple[int, int]], num_potholes: int, logs) -> Set[Tuple[int, int]]:
    potholes = set()
    available_positions = []
    for r in range(TOTAL_ROAD_ROWS - 1):
        for c in range(GRID_COLS):
            if (c, r) not in occupied:
                available_positions.append((c, r))
    random.shuffle(available_positions)
    for pos in available_positions[:num_potholes]:
        potholes.add(pos)
        occupied.add(pos)
    logs.append(f"Spawned {len(potholes)} potholes")
    return potholes

def spawn_obstacle_vehicles(av_vehicle: Vehicle, occupied: Set[Tuple[int, int]], logs) -> list:
    obstacle_vehicles = []
    for r in range(TOTAL_ROAD_ROWS - 1):
        if random.random() < SPAWN_PROB:
            free_cols = [c for c in range(GRID_COLS) if (c, r) not in occupied]
            if not free_cols:
                continue
            c = random.choice(free_cols)
            occupied.add((c, r))
            direction = random.choice([-1, 1])
            obstacle_vehicles.append(Vehicle(col=float(c), row=float(r), kind="obstacle", dir=direction))
    logs.append(f"Spawned {len(obstacle_vehicles)} obstacle vehicles")
    return obstacle_vehicles

def plan_obstacle_moves(obstacle_vehicles: list, av_pos: Tuple[int, int], potholes: Set[Tuple[int, int]]) -> Tuple[Dict[int, Tuple[int, int]], Set[Tuple[int, int]], Dict[Tuple[int, int], int]]:
    initial_map = {ov.pos(): i for i, ov in enumerate(obstacle_vehicles)}
    planned_map = {}
    planned_targets = set()
    indices = list(range(len(obstacle_vehicles)))
    random.shuffle(indices)

    for i in indices:
        ov = obstacle_vehicles[i]
        curr = ov.pos()
        target_col = int(ov.col) + ov.dir
        target = (target_col, int(ov.row))
        if target_col < 0 or target_col >= GRID_COLS:
            ov.dir *= -1
            planned_map[i] = curr
            planned_targets.add(curr)
            continue
        if (target in initial_map and initial_map[target] != i) or (target in planned_targets) or (target == av_pos) or (target in potholes):
            ov.dir *= -1
            planned_map[i] = curr
            planned_targets.add(curr)
            continue
        planned_map[i] = target
        planned_targets.add(target)
    return planned_map, planned_targets, initial_map

def commit_obstacle_moves(planned_map: Dict[int, Tuple[int, int]], obstacle_vehicles: list):
    for i, target in planned_map.items():
        ov = obstacle_vehicles[i]
        if target != ov.pos():
            ov.target = target
            ov.anim_frame = 0.0
        else:
            ov.target = None
            ov.anim_frame = STEP_FRAMES

def av_decide_and_move(av_vehicle: Vehicle, planned_map: Dict[int, Tuple[int, int]], planned_targets: Set[Tuple[int, int]], initial_map: Dict[Tuple[int, int], int], potholes: Set[Tuple[int, int]]) -> Tuple[int, int]:
    curr_row = int(av_vehicle.row)
    if curr_row == 0:
        return av_vehicle.pos()
    forward = (int(av_vehicle.col), curr_row - 1)

    def will_be_free(cell: Tuple[int, int]) -> bool:
        if cell in potholes:
            return False
        if cell in planned_targets:
            return False
        if cell in initial_map:
            idx = initial_map[cell]
            planned = planned_map.get(idx, cell)
            return planned != cell
        return True

    if inside(*forward) and will_be_free(forward):
        return forward
    sides = [(-1, 0), (1, 0)]
    random.shuffle(sides)
    for dx, dy in sides:
        nc, nr = int(av_vehicle.col) + dx, curr_row + dy
        if inside(nc, nr) and will_be_free((nc, nr)):
            return (nc, nr)
    for dx in (-1, 1):
        nc, nr = int(av_vehicle.col) + dx, curr_row - 1
        if inside(nc, nr) and will_be_free((nc, nr)):
            return (nc, nr)
    return av_vehicle.pos()

def commit_av_move(av_vehicle: Vehicle, target: Tuple[int, int]):
    if target != av_vehicle.pos():
        av_vehicle.target = target
        av_vehicle.anim_frame = 0.0
    else:
        av_vehicle.target = None
        av_vehicle.anim_frame = STEP_FRAMES

def draw_bounding_box(screen, px, py, kind, font, size=CELL*0.76):
    left = int(px - size / 2)
    top = int(py - size / 2)
    width = int(size)
    height = int(size * 0.5)
    rect = pygame.Rect(left, top, width, height)
    pygame.draw.rect(screen, BOUNDING, rect, 2, border_radius=6)
    label = "AV" if kind == "av" else "OV"
    t_surface = font.render(label, True, BOUNDING)
    screen.blit(t_surface, (left+4, top-16))

def vertical_gradient(surface, top_color, bottom_color):
    h = surface.get_height()
    for y in range(h):
        t = y / h
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (surface.get_width(), y))

def road_parallax(surface, offset):
    vertical_gradient(surface, (15, 16, 26), (36, 40, 50))
    for i in range(4):
        y = -20 + int(offset * (0.5 + i * 0.2)) + i * (HEIGHT // 4)
        pygame.draw.rect(surface, (38 + i * 6, 39 + i * 5, 45 + i * 7), (0, y, WIDTH, HEIGHT // 4 + 10), border_radius=20)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((34, 38, 42, 30))
    surface.blit(overlay, (0, 0))

def draw_shadow(screen, px: float, py: float):
    shadow_rect = pygame.Rect(px - CELL // 3, py + CELL // 4, CELL // 1.5, CELL // 6)
    pygame.draw.ellipse(screen, SHADOW, shadow_rect)

def draw_vehicle_sprite_or_shape(screen, vehicle: Vehicle, av_img, obstacle_img, road_offset, label_font):
    if vehicle.target and vehicle.anim_frame < STEP_FRAMES:
        t = ease_in_out(vehicle.anim_frame / STEP_FRAMES)
        start_col, start_row = vehicle.col, vehicle.row
        target_col, target_row = vehicle.target
        curr_col = start_col + (target_col - start_col) * t
        curr_row = start_row + (target_row - start_row) * t
        px, py = cell_to_pixel(curr_col, curr_row, road_offset)
    else:
        px, py = cell_to_pixel(vehicle.col, vehicle.row, road_offset)
    draw_shadow(screen, px, py)
    draw_bounding_box(screen, px, py, vehicle.kind, label_font)
    if vehicle.kind == "av":
        body_rect = pygame.Rect(int(px - CELL * 0.36), int(py - CELL * 0.2), int(CELL * 0.72), int(CELL * 0.4))
        pygame.draw.rect(screen, AV_COLOR, body_rect, border_radius=8)
        window_rect = pygame.Rect(int(px - CELL * 0.32), int(py - CELL * 0.18), int(CELL * 0.64), int(CELL * 0.18))
        pygame.draw.rect(screen, (200, 240, 255), window_rect, border_radius=6)
        wheel_radius = int(CELL * 0.1)
        pygame.draw.circle(screen, BLACK, (int(px - CELL * 0.25), int(py + CELL * 0.15)), wheel_radius)
        pygame.draw.circle(screen, BLACK, (int(px + CELL * 0.25), int(py + CELL * 0.15)), wheel_radius)
    else:
        body_rect = pygame.Rect(int(px - CELL * 0.3), int(py - CELL * 0.15), int(CELL * 0.6), int(CELL * 0.3))
        pygame.draw.rect(screen, OBSTACLE_COLOR, body_rect, border_radius=6)
        window_rect = pygame.Rect(int(px - CELL * 0.25), int(py - CELL * 0.13), int(CELL * 0.5), int(CELL * 0.13))
        pygame.draw.rect(screen, WHITE, window_rect, border_radius=4)
        wheel_radius = int(CELL * 0.08)
        pygame.draw.circle(screen, BLACK, (int(px - CELL * 0.2), int(py + CELL * 0.1)), wheel_radius)
        pygame.draw.circle(screen, BLACK, (int(px + CELL * 0.2), int(py + CELL * 0.1)), wheel_radius)

def draw_pothole(screen, col: int, row: int, road_offset: float):
    px, py = cell_to_pixel(float(col), float(row), road_offset)
    random.seed(col + row * GRID_COLS)
    hole_rect = pygame.Rect(int(px - CELL * 0.3), int(py - CELL * 0.15), int(CELL * 0.6), int(CELL * 0.3))
    pygame.draw.ellipse(screen, POTHOLE_DARK, hole_rect)
    pygame.draw.ellipse(screen, (60, 60, 60), hole_rect, 2)
    for _ in range(3):
        offset_x = random.uniform(-CELL * 0.3, CELL * 0.3)
        offset_y = random.uniform(-CELL * 0.15, CELL * 0.15)
        angle = random.uniform(0, 2 * math.pi)
        length = random.uniform(10, 25)
        end_x = offset_x + math.cos(angle) * length
        end_y = offset_y + math.sin(angle) * length
        gray = 70 + random.randint(-10, 10)
        crack_color = (gray, gray, gray)
        pygame.draw.line(screen, crack_color, (int(px + offset_x), int(py + offset_y)), (int(px + end_x), int(py + end_y)), 1)

def draw_schematic(screen, av_vehicle, obstacle_vehicles, potholes, schem_x, title_font):
    title_text = title_font.render("Schematic Overview", True, WHITE)
    title_x = schem_x + (SCHEM_WIDTH - title_text.get_width()) // 2
    title_y = SCHEM_OFFSET_Y - title_text.get_height() - 8
    screen.blit(title_text, (title_x, title_y))
    
    pygame.draw.rect(screen, BLACK, (schem_x, SCHEM_OFFSET_Y, SCHEM_WIDTH, SCHEM_HEIGHT))
    
    border_rect = pygame.Rect(schem_x + SCHEM_BORDER_THICK // 2, SCHEM_OFFSET_Y + SCHEM_BORDER_THICK // 2, SCHEM_WIDTH - SCHEM_BORDER_THICK, SCHEM_HEIGHT - SCHEM_BORDER_THICK)
    pygame.draw.rect(screen, AV_COLOR, border_rect, SCHEM_BORDER_THICK)
    
    for i in range(1, GRID_COLS):
        x = schem_x + i * SCHEM_CELL
        pygame.draw.line(screen, GRID_LINE, (x, SCHEM_OFFSET_Y), (x, SCHEM_OFFSET_Y + SCHEM_HEIGHT), 1)
    for i in range(1, TOTAL_ROAD_ROWS):
        y = SCHEM_OFFSET_Y + i * SCHEM_CELL
        pygame.draw.line(screen, GRID_LINE, (schem_x, y), (schem_x + SCHEM_WIDTH, y), 1)
    
    for col, row in potholes:
        px = schem_x + col * SCHEM_CELL + SCHEM_CELL // 2
        py = SCHEM_OFFSET_Y + row * SCHEM_CELL + SCHEM_CELL // 2
        pygame.draw.circle(screen, POTHOLE_COLOR, (int(px), int(py)), SCHEM_CELL // 4)
    
    for vehicle in [av_vehicle] + obstacle_vehicles:
        if vehicle.target and vehicle.anim_frame < STEP_FRAMES:
            t = ease_in_out(vehicle.anim_frame / STEP_FRAMES)
            start_col, start_row = vehicle.col, vehicle.row
            target_col, target_row = vehicle.target
            curr_col = start_col + (target_col - start_col) * t
            curr_row = start_row + (target_row - start_row) * t
        else:
            curr_col = vehicle.col
            curr_row = vehicle.row
        px = schem_x + curr_col * SCHEM_CELL + SCHEM_CELL // 2
        py = SCHEM_OFFSET_Y + curr_row * SCHEM_CELL + SCHEM_CELL // 2
        size = int(SCHEM_CELL * 0.6)
        rect = pygame.Rect(px - size // 2, py - size // 2, size, size)
        color = AV_COLOR if vehicle.kind == "av" else OBSTACLE_COLOR
        pygame.draw.rect(screen, color, rect, 2)

def draw_matrix_visualiser(screen, av_vehicle, obstacle_vehicles, potholes, matrix_x, matrix_font, title_font):
    title_text = title_font.render("Occupancy Matrix", True, WHITE)
    title_x = matrix_x + (MATRIX_WIDTH - title_text.get_width()) // 2
    title_y = MATRIX_OFFSET_Y - title_text.get_height() - 8
    screen.blit(title_text, (title_x, title_y))
    
    pygame.draw.rect(screen, BLACK, (matrix_x, MATRIX_OFFSET_Y, MATRIX_WIDTH, MATRIX_HEIGHT))
    
    border_rect = pygame.Rect(matrix_x + MATRIX_BORDER_THICK // 2, MATRIX_OFFSET_Y + MATRIX_BORDER_THICK // 2, MATRIX_WIDTH - MATRIX_BORDER_THICK, MATRIX_HEIGHT - MATRIX_BORDER_THICK)
    pygame.draw.rect(screen, OBSTACLE_COLOR, border_rect, MATRIX_BORDER_THICK)
    
    for i in range(1, GRID_COLS):
        x = matrix_x + i * MATRIX_CELL
        pygame.draw.line(screen, GRID_LINE, (x, MATRIX_OFFSET_Y), (x, MATRIX_OFFSET_Y + MATRIX_HEIGHT), 1)
    for i in range(1, TOTAL_ROAD_ROWS):
        y = MATRIX_OFFSET_Y + i * MATRIX_CELL
        pygame.draw.line(screen, GRID_LINE, (matrix_x, y), (matrix_x + MATRIX_WIDTH, y), 1)
    
    grid = {}
    for vehicle in [av_vehicle] + obstacle_vehicles:
        if vehicle.target and vehicle.anim_frame < STEP_FRAMES:
            t = ease_in_out(vehicle.anim_frame / STEP_FRAMES)
            start_col, start_row = vehicle.col, vehicle.row
            target_col, target_row = vehicle.target
            curr_col = start_col + (target_col - start_col) * t
            curr_row = start_row + (target_row - start_row) * t
        else:
            curr_col = vehicle.col
            curr_row = vehicle.row
        cell_col = round(curr_col)
        cell_row = round(curr_row)
        color = AV_COLOR if vehicle.kind == "av" else OBSTACLE_COLOR
        grid[(cell_col, cell_row)] = ('1', color)
    for col, row in potholes:
        grid[(col, row)] = ('1', POTHOLE_COLOR)
    
    for row in range(TOTAL_ROAD_ROWS):
        for col in range(GRID_COLS):
            symbol, color = grid.get((col, row), ('0', MATRIX_TEXT))
            text = matrix_font.render(symbol, True, color)
            tx = matrix_x + col * MATRIX_CELL + (MATRIX_CELL - text.get_width()) // 2
            ty = MATRIX_OFFSET_Y + row * MATRIX_CELL + (MATRIX_CELL - text.get_height()) // 2
            screen.blit(text, (tx, ty))

def draw_planning_view(screen, av_vehicle, planned_move, obstacle_vehicles, potholes, plan_x, title_font):
    title_text = title_font.render("AV Path Planning", True, WHITE)
    title_x = plan_x + (PLAN_WIDTH - title_text.get_width()) // 2
    title_y = PLAN_OFFSET_Y - title_text.get_height() - 8
    screen.blit(title_text, (title_x, title_y))
    
    pygame.draw.rect(screen, BLACK, (plan_x, PLAN_OFFSET_Y, PLAN_WIDTH, PLAN_HEIGHT))
    
    border_rect = pygame.Rect(plan_x + PLAN_BORDER_THICK // 2, PLAN_OFFSET_Y + PLAN_BORDER_THICK // 2, PLAN_WIDTH - PLAN_BORDER_THICK, PLAN_HEIGHT - PLAN_BORDER_THICK)
    pygame.draw.rect(screen, AV_COLOR, border_rect, PLAN_BORDER_THICK)
    
    for i in range(1, PLAN_SIZE):
        x = plan_x + i * PLAN_CELL
        pygame.draw.line(screen, GRID_LINE, (x, PLAN_OFFSET_Y), (x, PLAN_OFFSET_Y + PLAN_HEIGHT), 1)
        y = PLAN_OFFSET_Y + i * PLAN_CELL
        pygame.draw.line(screen, GRID_LINE, (plan_x, y), (plan_x + PLAN_WIDTH, y), 1)
    
    av_col, av_row = av_vehicle.pos()
    local_av_col = PLAN_SIZE // 2
    local_av_row = PLAN_SIZE // 2
    
    px = plan_x + local_av_col * PLAN_CELL + PLAN_CELL // 2
    py = PLAN_OFFSET_Y + local_av_row * PLAN_CELL + PLAN_CELL // 2
    size = int(PLAN_CELL * 0.5)
    rect = pygame.Rect(px - size // 2, py - size // 2, size, size)
    pygame.draw.rect(screen, AV_COLOR, rect, 0, border_radius=4)
    
    for dc in range(-PLAN_SIZE//2, PLAN_SIZE//2 + 1):
        for dr in range(-PLAN_SIZE//2, PLAN_SIZE//2 + 1):
            g_col = av_col + dc
            g_row = av_row + dr
            if not inside(g_col, g_row):
                continue
            local_col = local_av_col + dc
            local_row = local_av_row + dr
            if local_col < 0 or local_col >= PLAN_SIZE or local_row < 0 or local_row >= PLAN_SIZE:
                continue
            px = plan_x + local_col * PLAN_CELL + PLAN_CELL // 2
            py = PLAN_OFFSET_Y + local_row * PLAN_CELL + PLAN_CELL // 2
            if (g_col, g_row) in potholes:
                pygame.draw.circle(screen, POTHOLE_COLOR, (int(px), int(py)), PLAN_CELL // 5)
            for ov in obstacle_vehicles:
                if ov.pos() == (g_col, g_row):
                    size = int(PLAN_CELL * 0.5)
                    rect = pygame.Rect(px - size // 2, py - size // 2, size, size)
                    pygame.draw.rect(screen, OBSTACLE_COLOR, rect, 0, border_radius=4)
                    break
    
    if planned_move and planned_move != av_vehicle.pos():
        target_col, target_row = planned_move
        dx = target_col - av_col
        dy = target_row - av_row
        local_target_col = local_av_col + dx
        local_target_row = local_av_row + dy
        if 0 <= local_target_col < PLAN_SIZE and 0 <= local_target_row < PLAN_SIZE:
            start_x = plan_x + local_av_col * PLAN_CELL + PLAN_CELL // 2
            start_y = PLAN_OFFSET_Y + local_av_row * PLAN_CELL + PLAN_CELL // 2
            end_x = plan_x + local_target_col * PLAN_CELL + PLAN_CELL // 2
            end_y = PLAN_OFFSET_Y + local_target_row * PLAN_CELL + PLAN_CELL // 2
            pygame.draw.line(screen, ARROW_COLOR, (start_x, start_y), (end_x, end_y), 3)
            arrow_size = 8
            angle = math.atan2(end_y - start_y, end_x - start_x)
            head_x1 = end_x - arrow_size * math.cos(angle - math.pi / 6)
            head_y1 = end_y - arrow_size * math.sin(angle - math.pi / 6)
            head_x2 = end_x - arrow_size * math.cos(angle + math.pi / 6)
            head_y2 = end_y - arrow_size * math.sin(angle + math.pi / 6)
            pygame.draw.line(screen, ARROW_COLOR, (end_x, end_y), (head_x1, head_y1), 3)
            pygame.draw.line(screen, ARROW_COLOR, (end_x, end_y), (head_x2, head_y2), 3)

def draw_log_panel(screen, logs, log_font):
    pygame.draw.rect(screen, LOG_PANEL_BG, (LOG_PANEL_X, 0, LOG_PANEL_WIDTH, LOG_PANEL_HEIGHT))
    y = 10
    for log in logs[-20:]:  # Show last 20 logs to fit the panel
        text = log_font.render(log, True, LOG_TEXT_COLOR)
        screen.blit(text, (LOG_PANEL_X + 10, y))
        y += 18
    instructions = [
        "Controls:",
        "P: Pause/Resume",
        "M: Toggle Manual Mode",
        "Arrows: Move AV (manual mode)",
        "R: Reset Simulation",
        "ESC: Quit"
    ]
    y = LOG_PANEL_HEIGHT - len(instructions) * 18 - 10
    for inst in instructions:
        text = log_font.render(inst, True, LOG_TEXT_COLOR)
        screen.blit(text, (LOG_PANEL_X + 10, y))
        y += 18

def draw_scene(screen, av_vehicle, obstacle_vehicles, potholes, font, label_font, matrix_font, title_font, hud_font, log_font, av_img, obstacle_img, tick, overlay_state, overlay_alpha, road_offset, fps, planned_move, paused, manual_mode, completion_time, collision_count, success_rate, logs):
    road_parallax(screen, road_offset)
    for c in range(1, GRID_COLS):
        x = c * CELL
        for y in range(15, HEIGHT, 22):
            pygame.draw.line(screen, LANE, (x, y), (x, y + 10), 2)
    for r in range(1, GRID_ROWS_ONSCREEN):
        y = r * CELL
        pygame.draw.line(screen, (55, 58, 58), (0, y), (WIDTH, y), 1)
    for col, row in potholes:
        if road_offset - 1 <= row < road_offset + GRID_ROWS_ONSCREEN + 1:
            draw_pothole(screen, col, row, road_offset)
    for ov in obstacle_vehicles:
        if road_offset - 1 <= ov.row < road_offset + GRID_ROWS_ONSCREEN + 1:
            draw_vehicle_sprite_or_shape(screen, ov, None, obstacle_img, road_offset, label_font)
    if road_offset - 1 <= av_vehicle.row < road_offset + GRID_ROWS_ONSCREEN + 1:
        draw_vehicle_sprite_or_shape(screen, av_vehicle, av_img, None, road_offset, label_font)
    hud = pygame.Surface((WIDTH, 25), pygame.SRCALPHA)
    hud.fill((20, 20, 20, 180))
    screen.blit(hud, (0, HEIGHT - 25))
    progress = TOTAL_ROAD_ROWS - 1 - int(av_vehicle.row)
    info = f"Step: {tick}  AV Pos: {av_vehicle.pos()}  Progress: {progress}/{TOTAL_ROAD_ROWS-1}  Obstacles: {len(obstacle_vehicles)}  Potholes: {len(potholes)}  FPS: {fps:.1f}"
    txt = font.render(info, True, (220, 220, 220))
    screen.blit(txt, (6, HEIGHT - 22))
    decision_hud = pygame.Surface((WIDTH, 20), pygame.SRCALPHA)
    decision_hud.fill((20, 20, 20, 180))
    screen.blit(decision_hud, (0, HEIGHT - 45))
    decision_text = f"AV Planned Move: {planned_move if planned_move else 'Stationary at ' + str(av_vehicle.pos())}"
    decision_txt = hud_font.render(decision_text, True, (220, 220, 220))
    screen.blit(decision_txt, (6, HEIGHT - 42))
    metrics_hud = pygame.Surface((WIDTH, 20), pygame.SRCALPHA)
    metrics_hud.fill((20, 20, 20, 180))
    screen.blit(metrics_hud, (0, HEIGHT - 65))
    metrics_text = f"Completion Time: {completion_time} steps  Collisions: {collision_count}  Success Rate: {success_rate:.2%}"
    metrics_txt = hud_font.render(metrics_text, True, (220, 220, 220))
    screen.blit(metrics_txt, (6, HEIGHT - 62))
    if paused:
        pause_text = title_font.render("PAUSED", True, PAUSE_COLOR)
        screen.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2 - pause_text.get_height() // 2))
    if manual_mode:
        manual_text = title_font.render("MANUAL MODE", True, PAUSE_COLOR)
        screen.blit(manual_text, (WIDTH // 2 - manual_text.get_width() // 2, HEIGHT // 2 + 20))
    if overlay_state:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(overlay_alpha * 0.6 * 255)))
        screen.blit(overlay, (0, 0))
        if overlay_state == "SUCCESS":
            msg = "Success: AV Reached Destination"
            c = (140, 255, 140)
        else:
            msg = "Failure: Collision Detected"
            c = (255, 120, 120)
        big = pygame.font.SysFont("Arial", 28, bold=True)
        surf = big.render(msg, True, c)
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 - 28))
    
    draw_schematic(screen, av_vehicle, obstacle_vehicles, potholes, WIDTH, title_font)
    draw_matrix_visualiser(screen, av_vehicle, obstacle_vehicles, potholes, WIDTH + SCHEM_WIDTH, matrix_font, title_font)
    draw_planning_view(screen, av_vehicle, planned_move, obstacle_vehicles, potholes, WIDTH + SCHEM_WIDTH + MATRIX_WIDTH, title_font)
    draw_log_panel(screen, logs, log_font)
    
    pygame.display.flip()

def main():
    num_potholes = int(input("Enter the number of potholes to spawn (default 5): ") or 5)
    random.seed(42)
    logs = []
    screen = init_pygame_or_exit()
    av_img, obstacle_img = try_load_images(logs)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 16)
    label_font = pygame.font.SysFont("Arial", FONT_LABEL_SIZE, bold=True)
    matrix_font = pygame.font.SysFont("Arial", 14)
    title_font = pygame.font.SysFont("Arial", TITLE_FONT_SIZE, bold=True)
    hud_font = pygame.font.SysFont("Arial", HUD_FONT_SIZE)
    log_font = pygame.font.SysFont("Arial", LOG_FONT_SIZE)

    def reset():
        occupied = set()
        av = Vehicle(col=float(GRID_COLS // 2), row=float(TOTAL_ROAD_ROWS - 1), kind="av")
        occupied.add(av.pos())
        potholes = spawn_potholes(occupied, num_potholes, logs)
        obstacles = spawn_obstacle_vehicles(av, occupied, logs)
        for ov in obstacles:
            ov.target = None
            ov.anim_frame = STEP_FRAMES
        av.target = None
        av.anim_frame = STEP_FRAMES
        return av, obstacles, potholes

    av_vehicle, obstacle_vehicles, potholes = reset()
    tick = 0
    overlay_state = None
    overlay_start = 0.0
    overlay_alpha = 0.0
    road_offset = 0.0
    planned_move = None
    paused = False
    manual_mode = False
    completion_time = 0
    collision_count = 0
    success_rate = 0.0
    run_count = 0
    success_count = 0

    running = True
    while running:
        delta_time = clock.tick(FPS) / 1000.0
        fps = clock.get_fps()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                if ev.key == pygame.K_r:
                    av_vehicle, obstacle_vehicles, potholes = reset()
                    tick = 0
                    overlay_state = None
                    road_offset = 0.0
                    planned_move = None
                if ev.key == pygame.K_p:
                    paused = not paused
                if ev.key == pygame.K_m:
                    manual_mode = not manual_mode
                if manual_mode:
                    if ev.key == pygame.K_UP:
                        planned_move = (int(av_vehicle.col), int(av_vehicle.row) - 1)
                    elif ev.key == pygame.K_DOWN:
                        planned_move = (int(av_vehicle.col), int(av_vehicle.row) + 1)
                    elif ev.key == pygame.K_LEFT:
                        planned_move = (int(av_vehicle.col) - 1, int(av_vehicle.row))
                    elif ev.key == pygame.K_RIGHT:
                        planned_move = (int(av_vehicle.col) + 1, int(av_vehicle.row))
                    if planned_move:
                        commit_av_move(av_vehicle, planned_move)

        if paused:
            draw_scene(screen, av_vehicle, obstacle_vehicles, potholes, font, label_font, matrix_font, title_font, hud_font, log_font,
                       av_img, obstacle_img, tick, overlay_state, overlay_alpha, road_offset, fps, planned_move, paused, manual_mode, completion_time, collision_count, success_rate, logs)
            continue

        target_road_offset = max(0, av_vehicle.row - GRID_ROWS_ONSCREEN // 2)
        road_offset += (target_road_offset - road_offset) * 0.2

        if overlay_state:
            if time.time() - overlay_start >= RESET_DELAY:
                run_count += 1
                if overlay_state == "SUCCESS":
                    success_count += 1
                    completion_time = tick
                else:
                    collision_count += 1
                    logs.append(f"Collision at step {tick}, position {av_vehicle.pos()}")
                success_rate = success_count / run_count if run_count > 0 else 0.0
                av_vehicle, obstacle_vehicles, potholes = reset()
                overlay_state = None
                overlay_alpha = 0.0
                tick = 0
                road_offset = 0.0
                planned_move = None
            else:
                draw_scene(screen, av_vehicle, obstacle_vehicles, potholes, font, label_font, matrix_font, title_font, hud_font, log_font,
                           av_img, obstacle_img, tick, overlay_state, overlay_alpha, road_offset, fps, planned_move, paused, manual_mode, completion_time, collision_count, success_rate, logs)
                continue

        animating = any(ov.is_animating() for ov in obstacle_vehicles) or av_vehicle.is_animating()
        if not animating and not manual_mode:
            planned_map, planned_targets, initial_map = plan_obstacle_moves(obstacle_vehicles, av_vehicle.pos(), potholes)
            planned_move = av_decide_and_move(av_vehicle, planned_map, planned_targets, initial_map, potholes)
            commit_obstacle_moves(planned_map, obstacle_vehicles)
            commit_av_move(av_vehicle, planned_move)
        else:
            for ov in obstacle_vehicles:
                if ov.target and ov.anim_frame < STEP_FRAMES:
                    ov.anim_frame += delta_time * FPS
                    if ov.anim_frame >= STEP_FRAMES:
                        ov.col = float(ov.target[0])
                        ov.row = float(ov.target[1])
                        ov.target = None
            if av_vehicle.target and av_vehicle.anim_frame < STEP_FRAMES:
                av_vehicle.anim_frame += delta_time * FPS
                if av_vehicle.anim_frame >= STEP_FRAMES:
                    av_vehicle.col = float(av_vehicle.target[0])
                    av_vehicle.row = float(av_vehicle.target[1])
                    av_vehicle.target = None
                    planned_move = None

            if not any(ov.is_animating() for ov in obstacle_vehicles) and not av_vehicle.is_animating():
                tick += 1
                if any(ov.pos() == av_vehicle.pos() for ov in obstacle_vehicles) or av_vehicle.pos() in potholes or any(ov.pos() in potholes for ov in obstacle_vehicles):
                    overlay_state = "CRASH"
                    overlay_start = time.time()
                    overlay_alpha = 1.0
                    print(f"Collision at step {tick}, position {av_vehicle.pos()}")
                elif int(av_vehicle.row) == 0:
                    overlay_state = "SUCCESS"
                    overlay_start = time.time()
                    overlay_alpha = 1.0
                    print(f"AV reached destination at step {tick}, column {av_vehicle.col}")

        draw_scene(screen, av_vehicle, obstacle_vehicles, potholes, font, label_font, matrix_font, title_font, hud_font, log_font,
                   av_img, obstacle_img, tick, overlay_state, overlay_alpha, road_offset, fps, planned_move, paused, manual_mode, completion_time, collision_count, success_rate, logs)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
