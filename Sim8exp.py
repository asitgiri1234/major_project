#!/usr/bin/env python3
import sys
import random
import math
import time
import datetime # Import datetime for timestamps
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Set
import pygame
import pygame.freetype  # Import freetype
import pygame_menu
from io import BytesIO
import matplotlib.pyplot as plt

# ---- CONFIG ----
GRID_COLS = 8
GRID_ROWS_ONSCREEN = 8
TOTAL_ROAD_ROWS = 30

FPS = 60
# --- Speed Control ---
INITIAL_SIM_SPEED = 1.0
MIN_SIM_SPEED = 0.2
MAX_SIM_SPEED = 3.0
SPEED_INCREMENT = 0.2
STEP_SECONDS = 0.3 # Base seconds per step
# ---

SPAWN_PROB = 0.68
POTHOLE_PROB = 0.15
RESET_DELAY = 1.5

FONT_LABEL_SIZE = 12
TITLE_FONT_SIZE = 16
HUD_FONT_SIZE = 12

# --- UPDATED Layout Weights & Padding ---
SIM_LAYOUT_WEIGHT = 0.35
PANEL_PADDING = 5
DASH_LAYOUT_WEIGHT = 0.22
SCHEM_LAYOUT_WEIGHT = 0.10
MATRIX_LAYOUT_WEIGHT = 0.10
PLAN_TELEMETRY_LAYOUT_WEIGHT = 0.11
LOG_LAYOUT_WEIGHT = 0.12
# ---

THEMES = { # (Themes dictionary remains the same)
    'dark': {'AV_COLOR': (24,120,210),'OBSTACLE_COLOR': (200,40,40),'WHITE': (240,240,240),'BLACK': (16,16,20),'ROAD': (30,33,38),'LANE': (110,110,110),'HUD_BG': (18,18,18,180),'SHADOW': (10,10,15,100),'BOUNDING': (244,208,63),'POTHOLE_COLOR': (255,215,0),'POTHOLE_DARK': (20,20,20),'CRACK_GRAY': (70,70,70),'MATRIX_TEXT': (0,255,0),'GRID_LINE': (100,100,100),'ARROW_COLOR': (50,205,50),'PAUSE_COLOR': (255,255,255),'LOG_PANEL_BG': (18,18,18),'LOG_TEXT_COLOR': (220,220,220),'LOG_FONT_SIZE': 12,'BACKGROUND': (16,16,20),'PANEL_BG': (25,25,30),},
    'light': {'AV_COLOR': (33,150,243),'OBSTACLE_COLOR': (244,67,54),'WHITE': (66,66,66),'BLACK': (245,245,245),'ROAD': (224,224,224),'LANE': (189,189,189),'HUD_BG': (250,250,250,180),'SHADOW': (224,224,224,80),'BOUNDING': (255,152,0),'POTHOLE_COLOR': (255,152,0),'POTHOLE_DARK': (130,130,130),'CRACK_GRAY': (189,189,189),'MATRIX_TEXT': (76,175,80),'GRID_LINE': (224,224,224),'ARROW_COLOR': (76,175,80),'PAUSE_COLOR': (66,66,66),'LOG_PANEL_BG': (245,245,245),'LOG_TEXT_COLOR': (66,66,66),'LOG_FONT_SIZE': 12,'BACKGROUND': (245,245,245),'PANEL_BG': (255,255,255),},
    'tron': {'AV_COLOR': (0,255,255),'OBSTACLE_COLOR': (255,0,0),'WHITE': (0,255,255),'BLACK': (0,0,0),'ROAD': (0,0,0),'LANE': (0,128,255),'HUD_BG': (0,0,0,180),'SHADOW': (0,128,255,50),'BOUNDING': (255,255,0),'POTHOLE_COLOR': (255,165,0),'POTHOLE_DARK': (50,50,50),'CRACK_GRAY': (0,128,255),'MATRIX_TEXT': (0,255,0),'GRID_LINE': (0,128,255),'ARROW_COLOR': (0,255,0),'PAUSE_COLOR': (0,255,255),'LOG_PANEL_BG': (0,0,0),'LOG_TEXT_COLOR': (0,255,255),'LOG_FONT_SIZE': 12,'BACKGROUND': (0,0,0),'PANEL_BG': (0,0,0),},
    'wireframe': {'AV_COLOR': (0,255,0),'OBSTACLE_COLOR': (0,255,0),'WHITE': (0,255,0),'BLACK': (0,0,0),'ROAD': (0,0,0),'LANE': (0,255,0),'HUD_BG': (0,0,0,180),'SHADOW': (0,100,0,50),'BOUNDING': (0,255,0),'POTHOLE_COLOR': (0,255,0),'POTHOLE_DARK': (0,100,0),'CRACK_GRAY': (0,255,0),'MATRIX_TEXT': (0,255,0),'GRID_LINE': (0,255,0),'ARROW_COLOR': (0,255,0),'PAUSE_COLOR': (0,255,0),'LOG_PANEL_BG': (0,0,0),'LOG_TEXT_COLOR': (0,255,0),'LOG_FONT_SIZE': 12,'BACKGROUND': (0,0,0),'PANEL_BG': (0,0,0),}
}

# --- Global simulation speed ---
simulation_speed_multiplier = INITIAL_SIM_SPEED
# ---

def get_color(theme, key): # (remains the same)
    color = THEMES[theme][key]
    if len(color) == 4: return color
    if max(color) > 1: return tuple(c / 255 for c in color)
    return color

def cell_to_pixel(col: float, row: float, road_offset: float, cell_size: float) -> Tuple[float, float]: # (remains the same)
    x = col * cell_size + cell_size / 2
    y = (row - road_offset) * cell_size + cell_size / 2
    return x, y

def inside(col: float, row: float) -> bool: # (remains the same)
    return 0 <= int(col) < GRID_COLS and 0 <= int(row) < TOTAL_ROAD_ROWS

def ease_in_out(t: float) -> float: return t * t * (3 - 2 * t) # (remains the same)

@dataclass
class Vehicle: # (remains the same)
    col: float; row: float; kind: str; dir: int = 0
    target: Optional[Tuple[int, int]] = None; anim_frame: float = 0.0
    def pos(self) -> Tuple[int, int]: return (int(self.col), int(self.row))
    def is_animating(self, current_step_frames) -> bool:
        return self.target is not None and self.anim_frame < current_step_frames

class Panel: # (remains the same)
    def __init__(self, x, y, width, height, draw_func, screen_width, screen_height, layout_weight):
        self.x, self.y, self.width, self.height = x, y, width, height
        self.draw_func = draw_func
        self.screen_width, self.screen_height = screen_width, screen_height
        self.layout_weight = layout_weight
        self.visible = True; self.header_height = 25
        self.dragging, self.resizing = False, False
        self.drag_offset, self.resize_corner = (0, 0), None
        self.min_width, self.min_height = 100, 100
    def contains(self, pos):
        if not self.visible: return False
        x, y = pos; return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height
    def contains_header(self, pos):
        if not self.visible: return False
        x, y = pos; return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.header_height
    def contains_bottom_right(self, pos):
        if not self.visible: return False
        x, y = pos; return self.x + self.width - 10 <= x <= self.x + self.width and self.y + self.height - 10 <= y <= self.y + self.height
    def get_close_button_rect(self) -> pygame.Rect: return pygame.Rect(self.x + self.width - 22, 7, 15, 15)
    def handle_click(self, pos) -> bool:
        if not self.visible or not self.get_close_button_rect().collidepoint(pos): return False
        self.visible = False; return True
    def start_drag(self, pos):
        if self.contains_header(pos): self.dragging, self.drag_offset = True, (pos[0] - self.x, pos[1] - self.y); return True
        return False
    def start_resize(self, pos):
        if self.contains_bottom_right(pos): self.resizing, self.resize_corner = True, pos; return True
        return False
    def update_drag(self, pos):
        if self.dragging: self.x, self.y = max(0, min(pos[0]-self.drag_offset[0], self.screen_width-self.width)), max(0, min(pos[1]-self.drag_offset[1], self.screen_height-self.height))
    def update_resize(self, pos):
        if self.resizing: self.width, self.height = max(self.min_width, pos[0]-self.x), max(self.min_height, pos[1]-self.y)
    def stop_interaction(self): self.dragging, self.resizing = False, False
    def draw(self, screen, *args):
        if not self.visible or self.width <= 0 or self.height <= 0: return
        theme = args[-1]
        pygame.draw.rect(screen, THEMES[theme]['PANEL_BG'], (self.x, self.y, self.width, self.height))
        self.draw_func(screen, self.x, self.y, self.width, self.height, *args)
        pygame.draw.rect(screen, THEMES[theme]['BOUNDING'], (self.x+self.width-10, self.y+self.height-10, 10, 10))
        close_rect = self.get_close_button_rect()
        pygame.draw.rect(screen, THEMES[theme]['OBSTACLE_COLOR'], close_rect)
        pygame.draw.line(screen, THEMES[theme]['WHITE'], close_rect.topleft, close_rect.bottomright, 2)
        pygame.draw.line(screen, THEMES[theme]['WHITE'], close_rect.topright, close_rect.bottomleft, 2)

def init_pygame_or_exit(total_width, total_height) -> pygame.Surface: # (remains the same)
    pygame.init(); pygame.freetype.init(); pygame.font.init()
    try: screen = pygame.display.set_mode((total_width, total_height), pygame.RESIZABLE)
    except pygame.error as e: print("Failed window:", e); sys.exit(1)
    pygame.display.set_caption("AV Obstacle Avoidance Simulation"); return screen

def try_load_images(logs, cell_size, theme): # (remains the same)
    if theme in ['wireframe', 'tron']: return None, None
    try:
        av_img=pygame.image.load("av_vehicle.png").convert_alpha(); obstacle_img=pygame.image.load("obstacle_vehicle.png").convert_alpha()
        size=int(cell_size*0.78)
        if size > 0: av_img=pygame.transform.smoothscale(av_img,(size,size)); obstacle_img=pygame.transform.smoothscale(obstacle_img,(size,size)); # logs.append("Loaded images.")
        else: logs.append("WARN: Cell size zero."); return None, None
        return av_img, obstacle_img
    except Exception as e: logs.append(f"WARN: Img load fail: {e}. Using shapes."); return None, None

def spawn_potholes(occupied: Set[Tuple[int, int]], num_potholes: int, logs) -> Set[Tuple[int, int]]: # (remains the same)
    potholes=set(); available=[]
    for r in range(TOTAL_ROAD_ROWS-1):
        for c in range(GRID_COLS):
            if(c,r) not in occupied: available.append((c,r))
    random.shuffle(available); [potholes.add(pos) or occupied.add(pos) for pos in available[:num_potholes]]
    return potholes

def spawn_obstacle_vehicles(av_vehicle: Vehicle, occupied: Set[Tuple[int, int]], logs, spawn_prob) -> list: # (remains the same)
    obstacles=[]
    for r in range(TOTAL_ROAD_ROWS-1):
        if random.random()<spawn_prob:
            free_cols=[c for c in range(GRID_COLS) if(c,r) not in occupied]
            if not free_cols: continue
            c=random.choice(free_cols); occupied.add((c,r)); direction=random.choice([-1,1])
            obstacles.append(Vehicle(float(c),float(r),"obstacle",direction))
    return obstacles

def plan_obstacle_moves(obstacle_vehicles: list, av_pos: Tuple[int, int], potholes: Set[Tuple[int, int]], current_step_frames: int) -> Tuple[Dict[int, Tuple[int, int]], Set[Tuple[int, int]], Dict[Tuple[int, int], int]]: # (remains the same)
    initial_map={ov.pos():i for i,ov in enumerate(obstacle_vehicles)}; planned_map,planned_targets={},set()
    indices=list(range(len(obstacle_vehicles))); random.shuffle(indices)
    for i in indices:
        ov=obstacle_vehicles[i]; curr=ov.pos(); target_col=int(ov.col)+ov.dir; target=(target_col,int(ov.row))
        if not (0<=target_col<GRID_COLS): ov.dir*=-1; planned_map[i]=curr; planned_targets.add(curr); continue
        if(target in initial_map and initial_map[target]!=i) or(target in planned_targets) or(target==av_pos) or(target in potholes): ov.dir*=-1; planned_map[i]=curr; planned_targets.add(curr); continue
        planned_map[i]=target; planned_targets.add(target)
    return planned_map,planned_targets,initial_map

def commit_obstacle_moves(planned_map: Dict[int, Tuple[int, int]], obstacle_vehicles: list, current_step_frames: int): # (remains the same)
    for i,target in planned_map.items():
        ov=obstacle_vehicles[i]
        if target!=ov.pos(): ov.target,ov.anim_frame = target, 0.0
        else: ov.target,ov.anim_frame = None, current_step_frames

def av_decide_and_move(av_vehicle: Vehicle, planned_map: Dict[int, Tuple[int, int]], planned_targets: Set[Tuple[int, int]], initial_map: Dict[Tuple[int, int], int], potholes: Set[Tuple[int, int]]) -> Tuple[int, int]:
    curr_row, av_col = int(av_vehicle.row), int(av_vehicle.col)
    if curr_row == 0: return av_vehicle.pos()
    forward = (av_col, curr_row - 1)
    
    def will_be_free(cell: Tuple[int, int]) -> bool:
        if not inside(cell[0],cell[1]) or cell in potholes or cell in planned_targets: return False
        if cell in initial_map: idx=initial_map[cell]; planned=planned_map.get(idx,cell); return planned!=cell
        return True

    if will_be_free(forward): return forward # Check forward first

    # Check sides on current row
    for dx in [-1, 1]:
        nc, nr = av_col + dx, curr_row
        if will_be_free((nc, nr)): # Indentation fixed
            return (nc, nr)

    # Check diagonals forward
    for dx in [-1, 1]:
        nc, nr = av_col + dx, curr_row - 1
        if will_be_free((nc, nr)): # Indentation fixed
            return (nc, nr)

    return av_vehicle.pos() # Stay put if all blockedss

def commit_av_move(av_vehicle: Vehicle, target: Tuple[int, int], current_step_frames: int): # (remains the same)
    if target!=av_vehicle.pos() and inside(target[0],target[1]): av_vehicle.target,av_vehicle.anim_frame=target,0.0
    else: av_vehicle.target,av_vehicle.anim_frame=None,current_step_frames

def draw_bounding_box(screen, px, py, kind, label_font, cell_size, theme='dark'): # (remains the same)
    size=cell_size*0.76; w,h=int(size),int(size*0.5); l,t=int(px-size/2),int(py-size/2)
    rect=pygame.Rect(l,t,w,h); pygame.draw.rect(screen,THEMES[theme]['BOUNDING'],rect,2,border_radius=6)
    lbl="AV" if kind=="av" else "OV"; label_font.render_to(screen,(l+4,t-14),lbl,THEMES[theme]['BOUNDING'])

def vertical_gradient(surface, top_color, bottom_color): # (remains the same)
    h=surface.get_height()
    for y in range(h): t=y/h; r=int(top_color[0]*(1-t)+bottom_color[0]*t); g=int(top_color[1]*(1-t)+bottom_color[1]*t); b=int(top_color[2]*(1-t)+bottom_color[2]*t); pygame.draw.line(surface,(r,g,b),(0,y),(surface.get_width(),y))

def road_parallax(surface, offset, theme, sim_width, sim_height): # (remains the same)
    if theme=='tron': surface.fill(THEMES[theme]['ROAD']); [pygame.draw.rect(surface,(0,50,100),(0,-20+int(offset*(0.5+i*0.2))+i*(sim_height//4),sim_width,sim_height//4+10)) for i in range(4)]
    elif theme=='wireframe': surface.fill(THEMES[theme]['ROAD']); cw,ch=sim_width/GRID_COLS,sim_height/GRID_ROWS_ONSCREEN; [pygame.draw.line(surface,THEMES[theme]['GRID_LINE'],(i*cw,0),(i*cw,sim_height)) for i in range(1,GRID_COLS)]; [pygame.draw.line(surface,THEMES[theme]['GRID_LINE'],(0,i*ch),(sim_width,i*ch)) for i in range(1,GRID_ROWS_ONSCREEN)]
    else: top,bot=(15,16,26) if theme=='dark' else (240,240,245),(36,40,50) if theme=='dark' else (200,200,210); vertical_gradient(surface,top,bot); [pygame.draw.rect(surface,(38+i*6,39+i*5,45+i*7) if theme=='dark' else (220-i*5,220-i*5,225-i*5),(0,-20+int(offset*(0.5+i*0.2))+i*(sim_height//4),sim_width,sim_height//4+10),border_radius=20) for i in range(4)]; overlay=pygame.Surface((sim_width,sim_height),pygame.SRCALPHA); o_color=(34,38,42,30) if theme=='dark' else (255,255,255,20); overlay.fill(o_color); surface.blit(overlay,(0,0))

def draw_shadow(screen, px: float, py: float, cell_size: float, theme='dark'): # (remains the same)
    if theme == 'wireframe': return
    shadow_rect = pygame.Rect(px-cell_size//3, py+cell_size//4, cell_size//1.5, cell_size//6); pygame.draw.ellipse(screen, THEMES[theme]['SHADOW'], shadow_rect)

def draw_vehicle_sprite_or_shape(screen, vehicle: Vehicle, av_img, obstacle_img, road_offset, label_font, cell_size, sim_width, sim_height, theme='dark'): # (remains the same, includes wireframe)
    global simulation_speed_multiplier
    current_step_frames = max(1, int(FPS * STEP_SECONDS / simulation_speed_multiplier))
    if vehicle.target and vehicle.anim_frame < current_step_frames: t=ease_in_out(vehicle.anim_frame/current_step_frames); sc,sr=vehicle.col,vehicle.row; tc,tr=vehicle.target; cc=sc+(tc-sc)*t; cr=sr+(tr-sr)*t; px,py=cell_to_pixel(cc,cr,road_offset,cell_size)
    else: px, py = cell_to_pixel(vehicle.col, vehicle.row, road_offset, cell_size)
    if 0<=px<sim_width and 0<=py<sim_height:
        draw_shadow(screen, px, py, cell_size, theme)
        if theme != 'wireframe': draw_bounding_box(screen, px, py, vehicle.kind, label_font, cell_size, theme=theme)
        if theme == 'wireframe':
            half_w=cell_size*0.3; half_h=cell_size*0.15; roof_h=cell_size*0.1; roof_w_off=cell_size*0.1
            p1=(int(px-half_w), int(py-half_h)); p2=(int(px+half_w), int(py-half_h)); p3=(int(px+half_w), int(py+half_h)); p4=(int(px-half_w), int(py+half_h))
            p5=(int(px-half_w+roof_w_off), int(py-half_h-roof_h)); p6=(int(px+half_w-roof_w_off), int(py-half_h-roof_h))
            color=THEMES[theme]['AV_COLOR'] if vehicle.kind=="av" else THEMES[theme]['OBSTACLE_COLOR']
            pygame.draw.line(screen,color,p1,p2,1); pygame.draw.line(screen,color,p2,p3,1); pygame.draw.line(screen,color,p3,p4,1); pygame.draw.line(screen,color,p4,p1,1) # Body
            pygame.draw.line(screen,color,p5,p6,1); pygame.draw.line(screen,color,p1,p5,1); pygame.draw.line(screen,color,p2,p6,1) # Roof
            wheel_r=int(cell_size*0.05)
            if wheel_r>0: pygame.draw.circle(screen,color,(int(px-half_w*0.6),int(py+half_h)),wheel_r,1); pygame.draw.circle(screen,color,(int(px+half_w*0.6),int(py+half_h)),wheel_r,1) # Wheels
            return
        if vehicle.kind=="av":
            if av_img: screen.blit(av_img,(int(px-av_img.get_width()/2),int(py-av_img.get_height()/2)))
            else: body_rect=pygame.Rect(int(px-cell_size*0.36),int(py-cell_size*0.2),int(cell_size*0.72),int(cell_size*0.4)); pygame.draw.rect(screen,THEMES[theme]['AV_COLOR'],body_rect,border_radius=8 if theme!='tron' else 0); win_rect=pygame.Rect(int(px-cell_size*0.32),int(py-cell_size*0.18),int(cell_size*0.64),int(cell_size*0.18)); w_color=(200,240,255) if theme=='dark' else (100,200,255) if theme=='light' else (0,128,255); pygame.draw.rect(screen,w_color,win_rect,border_radius=6 if theme!='tron' else 0); wr=int(cell_size*0.1); pygame.draw.circle(screen,THEMES[theme]['BLACK'],(int(px-cell_size*0.25),int(py+cell_size*0.15)),wr); pygame.draw.circle(screen,THEMES[theme]['BLACK'],(int(px+cell_size*0.25),int(py+cell_size*0.15)),wr)
        else:
            if obstacle_img: screen.blit(obstacle_img,(int(px-obstacle_img.get_width()/2),int(py-obstacle_img.get_height()/2)))
            else: body_rect=pygame.Rect(int(px-cell_size*0.3),int(py-cell_size*0.15),int(cell_size*0.6),int(cell_size*0.3)); pygame.draw.rect(screen,THEMES[theme]['OBSTACLE_COLOR'],body_rect,border_radius=6 if theme!='tron' else 0); win_rect=pygame.Rect(int(px-cell_size*0.25),int(py-cell_size*0.13),int(cell_size*0.5),int(cell_size*0.13)); pygame.draw.rect(screen,THEMES[theme]['WHITE'],win_rect,border_radius=4 if theme!='tron' else 0); wr=int(cell_size*0.08); pygame.draw.circle(screen,THEMES[theme]['BLACK'],(int(px-cell_size*0.2),int(py+cell_size*0.1)),wr); pygame.draw.circle(screen,THEMES[theme]['BLACK'],(int(px+cell_size*0.2),int(py+cell_size*0.1)),wr)

def draw_pothole(screen, col: int, row: int, road_offset: float, cell_size, sim_width, sim_height, theme='dark'): # (remains the same)
    px,py=cell_to_pixel(float(col),float(row),road_offset,cell_size)
    if 0<=px<sim_width and 0<=py<sim_height:
        random.seed(col+row*GRID_COLS); hole_rect=pygame.Rect(int(px-cell_size*0.3),int(py-cell_size*0.15),int(cell_size*0.6),int(cell_size*0.3))
        if theme=='wireframe': pygame.draw.ellipse(screen,THEMES[theme]['POTHOLE_COLOR'],hole_rect,1)
        elif theme=='tron': pygame.draw.ellipse(screen,THEMES[theme]['POTHOLE_COLOR'],hole_rect,2)
        else: pygame.draw.ellipse(screen,THEMES[theme]['POTHOLE_DARK'],hole_rect); border_color=(60,60,60) if theme=='dark' else (200,200,200); pygame.draw.ellipse(screen,border_color,hole_rect,2); [pygame.draw.line(screen,(g:=70+random.randint(-10,10) if theme=='dark' else 180+random.randint(-10,10),g,g),(int(px+(ox:=random.uniform(-cell_size*0.3,cell_size*0.3))),int(py+(oy:=random.uniform(-cell_size*0.15,cell_size*0.15)))),(int(px+ox+math.cos(a:=random.uniform(0,2*math.pi))*(l:=random.uniform(10,25))),int(py+oy+math.sin(a)*l)),1) for _ in range(3)]

def draw_kpi(screen, x, y, label, value, label_font, value_font, theme, panel_width): # (remains the same)
    lbl_color,val_color = THEMES[theme]['LANE'],THEMES[theme]['WHITE']
    lbl_rect = label_font.render_to(screen,(x+15,y),label,lbl_color)
    val_surf,val_rect = value_font.render(value,val_color) # Use render for size
    val_x = x+panel_width-val_rect.width-15
    if val_x < lbl_rect.right+10: val_x=x+15+100
    value_font.render_to(screen,(val_x,y),value,val_color) # Use render_to for drawing
    return y + label_font.get_sized_height() + 8

def draw_schematic(screen, x, y, panel_width, panel_height, av_vehicle, obstacle_vehicles, potholes, title_font, theme='dark'): # (remains the same)
    global simulation_speed_multiplier
    current_step_frames = max(1, int(FPS * STEP_SECONDS / simulation_speed_multiplier))
    title_rect=title_font.get_rect("Schematic"); title_x,title_y=x+(panel_width-title_rect.width)/2,y+7
    title_font.render_to(screen,(title_x,title_y),"Schematic",THEMES[theme]['WHITE'])
    content_y,content_h=y+title_font.get_sized_height()+20,panel_height-(title_font.get_sized_height()+30); border=2
    if content_h<=0 or panel_width<=0: return
    pygame.draw.rect(screen,THEMES[theme]['BLACK'],(x,content_y,panel_width,content_h)); border_rect=pygame.Rect(x+border/2,content_y+border/2,panel_width-border,content_h-border); pygame.draw.rect(screen,THEMES[theme]['AV_COLOR'],border_rect,border)
    cw,ch=panel_width/GRID_COLS,content_h/TOTAL_ROAD_ROWS
    for i in range(1,GRID_COLS): lx=x+i*cw; pygame.draw.line(screen,THEMES[theme]['GRID_LINE'],(lx,content_y),(lx,content_y+content_h),1)
    for i in range(1,TOTAL_ROAD_ROWS): ly=content_y+i*ch; pygame.draw.line(screen,THEMES[theme]['GRID_LINE'],(x,ly),(x+panel_width,ly),1)
    for col,row in potholes: px,py=x+col*cw+cw/2,content_y+row*ch+ch/2; pygame.draw.circle(screen,THEMES[theme]['POTHOLE_COLOR'],(int(px),int(py)),int(cw)/4,2 if theme=='wireframe' else 0)
    for v in [av_vehicle]+obstacle_vehicles:
        if v.target and v.anim_frame < current_step_frames: t=ease_in_out(v.anim_frame/current_step_frames); sc,sr=v.col,v.row; tc,tr=v.target; cc=sc+(tc-sc)*t; cr=sr+(tr-sr)*t
        else: cc,cr=v.col,v.row
        px,py=x+cc*cw+cw/2,content_y+cr*ch+ch/2; size=int(cw*0.6)
        if size>0: rect=pygame.Rect(px-size/2,py-size/2,size,size); color=THEMES[theme]['AV_COLOR'] if v.kind=="av" else THEMES[theme]['OBSTACLE_COLOR']; pygame.draw.rect(screen,color,rect,2 if theme=='wireframe' else 0)

def draw_matrix_visualiser(screen, x, y, panel_width, panel_height, av_vehicle, obstacle_vehicles, potholes, matrix_font, title_font, theme='dark'): # (remains the same)
    global simulation_speed_multiplier
    current_step_frames = max(1, int(FPS * STEP_SECONDS / simulation_speed_multiplier))
    title_rect=title_font.get_rect("Occupancy"); title_x,title_y=x+(panel_width-title_rect.width)/2,y+7
    title_font.render_to(screen,(title_x,title_y),"Occupancy",THEMES[theme]['WHITE'])
    content_y,content_h=y+title_font.get_sized_height()+20,panel_height-(title_font.get_sized_height()+30); border=2
    if content_h<=0 or panel_width<=0: return
    pygame.draw.rect(screen,THEMES[theme]['BLACK'],(x,content_y,panel_width,content_h)); border_rect=pygame.Rect(x+border/2,content_y+border/2,panel_width-border,content_h-border); pygame.draw.rect(screen,THEMES[theme]['OBSTACLE_COLOR'],border_rect,border)
    cw,ch=panel_width/GRID_COLS,content_h/TOTAL_ROAD_ROWS; draw_text=cw>8 and ch>8
    for i in range(1,GRID_COLS): lx=x+i*cw; pygame.draw.line(screen,THEMES[theme]['GRID_LINE'],(lx,content_y),(lx,content_y+content_h),1)
    for i in range(1,TOTAL_ROAD_ROWS): ly=content_y+i*ch; pygame.draw.line(screen,THEMES[theme]['GRID_LINE'],(x,ly),(x+panel_width,ly),1)
    grid={}
    for v in [av_vehicle]+obstacle_vehicles:
        if v.target and v.anim_frame < current_step_frames: t=ease_in_out(v.anim_frame/current_step_frames); sc,sr=v.col,v.row; tc,tr=v.target; cc=sc+(tc-sc)*t; cr=sr+(tr-sr)*t
        else: cc,cr=v.col,v.row
        ccol,crow=round(cc),round(cr); color=THEMES[theme]['AV_COLOR'] if v.kind=="av" else THEMES[theme]['OBSTACLE_COLOR']; grid[(ccol,crow)]=('1',color)
    for col,row in potholes: grid[(col,row)]=('1',THEMES[theme]['POTHOLE_COLOR'])
    if draw_text:
        for row in range(TOTAL_ROAD_ROWS):
            for col in range(GRID_COLS):
                sym,clr=grid.get((col,row),('0',THEMES[theme]['MATRIX_TEXT'])); txt_rect=matrix_font.get_rect(sym)
                tx,ty=x+col*cw+(cw-txt_rect.width)/2,content_y+row*ch+(ch-txt_rect.height)/2
                if content_y<ty<content_y+content_h: matrix_font.render_to(screen,(tx,ty),sym,clr)

# --- UPDATED draw_planning_telemetry_panel (Removed vehicle_stress) ---
def draw_planning_telemetry_panel(screen, x, y, panel_width, panel_height, av_vehicle, planned_move, obstacle_vehicles, potholes, tick, kpi_font, title_font, theme='dark'):
    if panel_width<=0 or panel_height<=0: return
    plan_h=min(panel_width+20,panel_height*0.45)
    draw_planning_view_content(screen,x,y,panel_width,plan_h,av_vehicle,planned_move,obstacle_vehicles,potholes,title_font,theme)
    telemetry_y=y+plan_h+10; telemetry_h=panel_height-plan_h-10
    draw_telemetry_content(screen,x,telemetry_y,panel_width,telemetry_h,tick,av_vehicle,planned_move, kpi_font,title_font,theme) # Removed stress

def draw_planning_view_content(screen, x, y, panel_width, panel_height, av_vehicle, planned_move, obstacle_vehicles, potholes, title_font, theme='dark'): # (remains the same)
    title_rect=title_font.get_rect("Planning"); title_x,title_y=x+(panel_width-title_rect.width)/2,y+7
    title_font.render_to(screen,(title_x,title_y),"Planning",THEMES[theme]['WHITE'])
    content_y=y+title_font.get_sized_height()+20; content_size=min(panel_width-20,panel_height-(title_font.get_sized_height()+30))
    content_x=x+(panel_width-content_size)/2; border=2; plan_size=5
    if content_size<=10: return
    pygame.draw.rect(screen,THEMES[theme]['BLACK'],(content_x,content_y,content_size,content_size)); border_rect=pygame.Rect(content_x+border/2,content_y+border/2,content_size-border,content_size-border); pygame.draw.rect(screen,THEMES[theme]['AV_COLOR'],border_rect,border)
    pc=content_size/plan_size
    for i in range(1,plan_size): lx=content_x+i*pc; pygame.draw.line(screen,THEMES[theme]['GRID_LINE'],(lx,content_y),(lx,content_y+content_size),1); ly=content_y+i*pc; pygame.draw.line(screen,THEMES[theme]['GRID_LINE'],(content_x,ly),(content_x+content_size,ly),1)
    avc,avr=av_vehicle.pos(); lac,lar=plan_size//2,plan_size//2
    px,py=content_x+lac*pc+pc/2,content_y+lar*pc+pc/2; size=int(pc*0.5)
    if size>0: rect=pygame.Rect(px-size/2,py-size/2,size,size); pygame.draw.rect(screen,THEMES[theme]['AV_COLOR'],rect,2 if theme=='wireframe' else 0,border_radius=4 if theme!='tron' else 0)
    for dc in range(-plan_size//2,plan_size//2+1):
        for dr in range(-plan_size//2,plan_size//2+1):
            gc,gr=avc+dc,avr+dr; lc,lr=lac+dc,lar+dr
            if not inside(gc,gr) or not(0<=lc<plan_size and 0<=lr<plan_size): continue
            px,py=content_x+lc*pc+pc/2,content_y+lr*pc+pc/2
            if(gc,gr) in potholes: pygame.draw.circle(screen,THEMES[theme]['POTHOLE_COLOR'],(int(px),int(py)),int(pc)/5,2 if theme=='wireframe' else 0)
            for ov in obstacle_vehicles:
                if ov.pos()==(gc,gr) and size>0: rect=pygame.Rect(px-size/2,py-size/2,size,size); pygame.draw.rect(screen,THEMES[theme]['OBSTACLE_COLOR'],rect,2 if theme=='wireframe' else 0,border_radius=4 if theme!='tron' else 0); break
    if planned_move and planned_move!=av_vehicle.pos():
        tc,tr=planned_move; dx,dy=tc-avc,tr-avr; ltc,ltr=lac+dx,lar+dy
        if 0<=ltc<plan_size and 0<=ltr<plan_size:
            sx,sy=content_x+lac*pc+pc/2,content_y+lar*pc+pc/2; ex,ey=content_x+ltc*pc+pc/2,content_y+ltr*pc+pc/2
            pygame.draw.line(screen,THEMES[theme]['ARROW_COLOR'],(sx,sy),(ex,ey),3); arrow_size=8; angle=math.atan2(ey-sy,ex-sx)
            hx1,hy1=ex-arrow_size*math.cos(angle-math.pi/6),ey-arrow_size*math.sin(angle-math.pi/6); hx2,hy2=ex-arrow_size*math.cos(angle+math.pi/6),ey-arrow_size*math.sin(angle+math.pi/6)
            pygame.draw.line(screen,THEMES[theme]['ARROW_COLOR'],(ex,ey),(hx1,hy1),3); pygame.draw.line(screen,THEMES[theme]['ARROW_COLOR'],(ex,ey),(hx2,hy2),3)

# --- UPDATED draw_telemetry_content (Removed vehicle_stress) ---
def draw_telemetry_content(screen, x, y, panel_width, panel_height, tick, av_vehicle, planned_move, kpi_font, title_font, theme='dark'):
    if panel_width <= 0 or panel_height <= 0: return
    pygame.draw.line(screen, THEMES[theme]['GRID_LINE'], (x+5, y-5), (x+panel_width-5, y-5), 1)
    title_rect=title_font.get_rect("Telemetry"); title_x,title_y=x+(panel_width-title_rect.width)/2,y+7
    title_font.render_to(screen,(title_x,title_y),"Telemetry",THEMES[theme]['WHITE'])
    kpi_y = y + title_font.get_sized_height() + 25
    kpi_y=draw_kpi(screen,x,kpi_y,"Run Time:",f"{(tick*STEP_SECONDS):.1f} s",kpi_font,kpi_font,theme,panel_width)
    kpi_y=draw_kpi(screen,x,kpi_y,"Distance:",f"{(TOTAL_ROAD_ROWS-1-av_vehicle.row):.0f} m",kpi_font,kpi_font,theme,panel_width)
    status="PLANNING"; pos=f"({av_vehicle.pos()[0]},{av_vehicle.pos()[1]})"
    if planned_move and planned_move!=av_vehicle.pos(): status="EXECUTING"
    elif planned_move: status="WAITING"
    kpi_y=draw_kpi(screen,x,kpi_y,"Status:",status,kpi_font,kpi_font,theme,panel_width)
    # Stress KPI Removed
    kpi_y=draw_kpi(screen,x,kpi_y,"Position:",pos,kpi_font,kpi_font,theme,panel_width)

def draw_log_panel(screen, x, y, panel_width, panel_height, logs, log_font, theme='dark'): # (remains the same)
    if panel_width <= 0 or panel_height <= 0: return
    pygame.draw.rect(screen, THEMES[theme]['LOG_PANEL_BG'], (x, y, panel_width, panel_height))
    title_ft_font = pygame.freetype.SysFont("arial", TITLE_FONT_SIZE, bold=True)
    title_rect = title_ft_font.get_rect("Log & Controls"); title_x, title_y = x+(panel_width-title_rect.width)/2, y+7
    title_ft_font.render_to(screen,(title_x, title_y), "Log & Controls", THEMES[theme]['WHITE'])
    log_area_y = y + title_ft_font.get_sized_height() + 20; log_area_h = panel_height * 0.6
    log_y = log_area_y
    mono_log_ft_font = pygame.freetype.SysFont("monospace", THEMES[theme]['LOG_FONT_SIZE'])
    line_h = mono_log_ft_font.get_sized_height() + 2
    logs_to_show = int(log_area_h // line_h) - 1
    if logs_to_show > 0:
        start_idx = max(0, len(logs) - logs_to_show)
        for i in range(start_idx, len(logs)):
            log = logs[i]; max_w = panel_width - 30
            try:
                log_rect = mono_log_ft_font.get_rect(log)
                if log_rect.width > max_w: avg_char_w=log_rect.width/len(log) if len(log)>0 else 10; chars_fit=int(max_w/avg_char_w); log=log[:max(0,chars_fit-3)]+"..."
                mono_log_ft_font.render_to(screen,(x+15,log_y),log,THEMES[theme]['LOG_TEXT_COLOR']); log_y += line_h
            except Exception as e: print(f"Log render error: {e}"); break
    sep_y = log_area_y + log_area_h + 5
    pygame.draw.line(screen, THEMES[theme]['GRID_LINE'], (x+10, sep_y), (x+panel_width-10, sep_y), 1)
    instructions = [("P","Pause/Resume"),("M","Manual Mode"),("A","Show All Panels"),("+/-","Adj. Speed"),("R","Reset Simulation"),("ESC","Quit")]
    inst_y = sep_y + 15
    ctrl_h_needed = 25 + len(instructions)*(log_font.get_sized_height()+8) + 10
    if inst_y + ctrl_h_needed < y + panel_height:
        log_font.render_to(screen,(x+15, inst_y), "Controls:", THEMES[theme]['WHITE']); inst_y += 25
        for key, desc in instructions: inst_y = draw_kpi(screen, x, inst_y, f"[{key}]", desc, log_font, log_font, theme, panel_width)

def update_graphs(completion_times, collision_counts, success_rates, theme, graph_size_inches=(2.8, 1.8)): # (remains the same)
    graph_surfaces = []
    if graph_size_inches[0] <= 0.1 or graph_size_inches[1] <= 0.1: return []
    plt.style.use('dark_background' if theme in ['dark','tron','wireframe'] else 'default')
    face_color,text_color,grid_color=get_color(theme,'LOG_PANEL_BG'),get_color(theme,'WHITE'),get_color(theme,'GRID_LINE')
    fig1,ax1=plt.subplots(figsize=graph_size_inches); vt=[t for t in completion_times if t>0]; vi=[i for i,t in enumerate(completion_times) if t>0]
    ax1.plot(vi,vt,color=get_color(theme,'AV_COLOR'),lw=2,marker='o',ms=4,label='Time'); ax1.set_title('Completion Times',c=text_color,fontsize=9,pad=8); ax1.set_xlabel('Run',c=text_color,fontsize=7); ax1.set_ylabel('Steps',c=text_color,fontsize=7); ax1.grid(True,ls='--',alpha=0.3,c=grid_color); ax1.legend(fontsize=6); ax1.tick_params(colors=text_color,labelsize=6); [s.set_color(text_color) for s in ax1.spines.values()]; fig1.patch.set_facecolor(face_color); ax1.set_facecolor(face_color); buf1=BytesIO(); fig1.savefig(buf1,format='png',bbox_inches='tight',dpi=100); buf1.seek(0); img1=pygame.image.load(buf1); plt.close(fig1); graph_surfaces.append(img1)
    fig2,ax2=plt.subplots(figsize=graph_size_inches); ax2.plot(range(len(collision_counts)),collision_counts,color=get_color(theme,'OBSTACLE_COLOR'),lw=2,marker='o',ms=4,label='Collisions'); ax2.set_title('Collisions',c=text_color,fontsize=9,pad=8); ax2.set_xlabel('Run',c=text_color,fontsize=7); ax2.set_ylabel('Count',c=text_color,fontsize=7); ax2.grid(True,ls='--',alpha=0.3,c=grid_color); ax2.legend(fontsize=6); ax2.tick_params(colors=text_color,labelsize=6); [s.set_color(text_color) for s in ax2.spines.values()]; fig2.patch.set_facecolor(face_color); ax2.set_facecolor(face_color); buf2=BytesIO(); fig2.savefig(buf2,format='png',bbox_inches='tight',dpi=100); buf2.seek(0); img2=pygame.image.load(buf2); plt.close(fig2); graph_surfaces.append(img2)
    fig3,ax3=plt.subplots(figsize=graph_size_inches); ax3.plot(range(len(success_rates)),success_rates,color=get_color(theme,'ARROW_COLOR'),lw=2,marker='o',ms=4,label='Success'); ax3.set_title('Success Rate',c=text_color,fontsize=9,pad=8); ax3.set_xlabel('Run',c=text_color,fontsize=7); ax3.set_ylabel('Rate',c=text_color,fontsize=7); ax3.set_ylim(-0.05,1.05); ax3.grid(True,ls='--',alpha=0.3,c=grid_color); ax3.legend(fontsize=6); ax3.tick_params(colors=text_color,labelsize=6); [s.set_color(text_color) for s in ax3.spines.values()]; fig3.patch.set_facecolor(face_color); ax3.set_facecolor(face_color); buf3=BytesIO(); fig3.savefig(buf3,format='png',bbox_inches='tight',dpi=100); buf3.seek(0); img3=pygame.image.load(buf3); plt.close(fig3); graph_surfaces.append(img3)
    return graph_surfaces

def draw_dashboard(screen, x, y, panel_width, panel_height, graph_surfaces, theme='dark'): # (remains the same)
    if panel_width <= 0 or panel_height <= 0: return
    pygame.draw.rect(screen, THEMES[theme]['LOG_PANEL_BG'], (x, y, panel_width, panel_height))
    title_ft_font = pygame.freetype.SysFont("arial", TITLE_FONT_SIZE, bold=True)
    title_rect=title_ft_font.get_rect("Dashboard"); title_x,title_y=x+(panel_width-title_rect.width)/2,y+7
    title_ft_font.render_to(screen,(title_x, title_y), "Dashboard", THEMES[theme]['WHITE'])
    if graph_surfaces:
        y_offset = y + title_ft_font.get_sized_height() + 20
        available_h = panel_height - (y_offset - y) - 20; spacing = available_h / 3
        graph_h = max(1, int(spacing - 15)); graph_w = max(1, int(panel_width - 30))
        for i, graph in enumerate(graph_surfaces):
            try: scaled=pygame.transform.smoothscale(graph,(graph_w,graph_h)); screen.blit(scaled,(x+15, y_offset+i*spacing))
            except Exception as e: print(f"Graph draw error: {e}")

# --- UPDATED draw_scene signature (removed vehicle_stress) ---
def draw_scene(screen, av_vehicle, obstacle_vehicles, potholes, fonts, av_img, obstacle_img, tick, overlay_state, overlay_alpha, road_offset, fps, planned_move, paused, manual_mode, completion_time, collision_count, success_rate, logs, theme, graph_surfaces, enlarged_graph, panels, layout, sim_speed):
    sim_w,sim_h,cell_s = layout['sim_width'],layout['sim_height'],layout['cell_size']
    screen.fill(THEMES[theme]['BACKGROUND'])
    if sim_w>0 and sim_h>0:
        sim_surf=screen.subsurface(pygame.Rect(0,0,sim_w,sim_h))
        road_parallax(sim_surf,road_offset,theme,sim_w,sim_h)
        for c in range(1,GRID_COLS): xl=c*cell_s; [pygame.draw.line(sim_surf,THEMES[theme]['LANE'],(xl,yl),(xl,yl+10),2) for yl in range(15,sim_h,22)]
        for col,row in potholes:
            if road_offset-1<=row<road_offset+GRID_ROWS_ONSCREEN+1: draw_pothole(sim_surf,col,row,road_offset,cell_s,sim_w,sim_h,theme)
        for ov in obstacle_vehicles:
            if road_offset-1<=ov.row<road_offset+GRID_ROWS_ONSCREEN+1: draw_vehicle_sprite_or_shape(sim_surf,ov,None,obstacle_img,road_offset,fonts['label'],cell_s,sim_w,sim_h,theme)
        if road_offset-1<=av_vehicle.row<road_offset+GRID_ROWS_ONSCREEN+1: draw_vehicle_sprite_or_shape(sim_surf,av_vehicle,av_img,None,road_offset,fonts['label'],cell_s,sim_w,sim_h,theme)

    dashboard_panel, schematic_panel, matrix_panel, plan_telemetry_panel, log_panel = panels
    dashboard_panel.draw(screen, graph_surfaces, theme)
    schematic_panel.draw(screen, av_vehicle, obstacle_vehicles, potholes, fonts['title'], theme)
    matrix_panel.draw(screen, av_vehicle, obstacle_vehicles, potholes, fonts['matrix'], fonts['title'], theme)
    # Removed vehicle_stress from this call
    plan_telemetry_panel.draw(screen, av_vehicle, planned_move, obstacle_vehicles, potholes, tick, fonts['kpi'], fonts['title'], theme)
    log_panel.draw(screen, logs, fonts['log'], theme)

    if sim_w>0 and sim_h>0:
        hud_h,hud_s=25,5; prog=TOTAL_ROAD_ROWS-1-int(av_vehicle.row)
        hud_surf=pygame.Surface((sim_w,hud_h),pygame.SRCALPHA); hud_surf.fill(THEMES[theme]['HUD_BG']); screen.blit(hud_surf,(0,sim_h-hud_h))
        info=f"Step:{tick} Pos:{av_vehicle.pos()} Prg:{prog}/{TOTAL_ROAD_ROWS-1} Obs:{len(obstacle_vehicles)} Speed:{sim_speed:.1f}x FPS:{fps:.1f}"
        try: fonts['hud'].render_to(screen,(5,sim_h-hud_h+5), info, THEMES[theme]['LOG_TEXT_COLOR'])
        except Exception: pass
        dec_hud=pygame.Surface((sim_w,hud_h),pygame.SRCALPHA); dec_hud.fill(THEMES[theme]['HUD_BG']); screen.blit(dec_hud,(0,sim_h-hud_h*2-hud_s))
        dec_txt=f"Plan: {planned_move if planned_move else 'Hold '+str(av_vehicle.pos())}"
        try: fonts['hud'].render_to(screen,(5,sim_h-hud_h*2-hud_s+5), dec_txt, THEMES[theme]['LOG_TEXT_COLOR'])
        except Exception: pass
        met_hud=pygame.Surface((sim_w,hud_h),pygame.SRCALPHA); met_hud.fill(THEMES[theme]['HUD_BG']); screen.blit(met_hud,(0,sim_h-hud_h*3-hud_s*2))
        met_txt=f"Complete:{completion_time} Collide:{collision_count} Success:{success_rate:.1%}"
        try: fonts['hud'].render_to(screen,(5,sim_h-hud_h*3-hud_s*2+5), met_txt, THEMES[theme]['LOG_TEXT_COLOR'])
        except Exception: pass
        if paused: fonts['title'].render_to(screen,(sim_w/2-fonts['title'].get_rect('PAUSED').width/2,sim_h/2-fonts['title'].get_sized_height()/2),"PAUSED",THEMES[theme]['PAUSE_COLOR'])
        if manual_mode: fonts['title'].render_to(screen,(sim_w/2-fonts['title'].get_rect('MANUAL').width/2,sim_h/2+20),"MANUAL",THEMES[theme]['PAUSE_COLOR'])
        if overlay_state:
            overlay=pygame.Surface((sim_w,sim_h),pygame.SRCALPHA); o_color=(0,0,0,int(overlay_alpha*0.6*255)) if theme in ['dark','tron','wireframe'] else (255,255,255,int(overlay_alpha*0.6*255)); overlay.fill(o_color); screen.blit(overlay,(0,0))
            if overlay_state=="SUCCESS": msg="Success"; c=(140,255,140) if theme in ['dark','tron','wireframe'] else (0,100,0)
            else: msg=f"Failure: {overlay_state}"; c=(255,120,120) if theme in ['dark','tron','wireframe'] else (100,0,0)
            big_font=pygame.freetype.SysFont("arial",28,bold=True); big_rect=big_font.get_rect(msg); big_font.render_to(screen,(sim_w/2-big_rect.width/2,sim_h/2-28),msg,c)
    if enlarged_graph: overlay=pygame.Surface(screen.get_size(),pygame.SRCALPHA); overlay.fill((0,0,0,180)); screen.blit(overlay,(0,0)); screen.blit(enlarged_graph,(screen.get_width()/2-enlarged_graph.get_width()/2,screen.get_height()/2-enlarged_graph.get_height()/2))
    pygame.display.flip()

def run_simulation(screen, num_potholes, spawn_prob, theme, initial_width, initial_height):
    global simulation_speed_multiplier
    random.seed(42); logs=[]
    clock = pygame.time.Clock()
    try:
        fonts={'label':pygame.freetype.SysFont("arial",FONT_LABEL_SIZE,bold=True),'matrix':pygame.freetype.SysFont("monospace",14),
               'title':pygame.freetype.SysFont("arial",TITLE_FONT_SIZE,bold=True),'hud':pygame.freetype.SysFont("arial",HUD_FONT_SIZE),
               'log':pygame.freetype.SysFont("monospace",THEMES[theme]['LOG_FONT_SIZE']),'kpi':pygame.freetype.SysFont("arial",HUD_FONT_SIZE)}
    except Exception as e: print(f"FATAL Font fail: {e}"); sys.exit(1)
    completion_times,collision_counts,success_rates=[],[],[]; graph_surfaces,enlarged_graph,enlarged_idx=[],None,-1
    av_img,obstacle_img=None,None; screen_dims={'width':initial_width,'height':initial_height}; layout={}

    dashboard_panel = Panel(0,0,0,0, draw_dashboard, initial_width, initial_height, DASH_LAYOUT_WEIGHT)
    schematic_panel = Panel(0,0,0,0, draw_schematic, initial_width, initial_height, SCHEM_LAYOUT_WEIGHT)
    matrix_panel = Panel(0,0,0,0, draw_matrix_visualiser, initial_width, initial_height, MATRIX_LAYOUT_WEIGHT)
    plan_telemetry_panel = Panel(0,0,0,0, draw_planning_telemetry_panel, initial_width, initial_height, PLAN_TELEMETRY_LAYOUT_WEIGHT)
    log_panel = Panel(0,0,0,0, draw_log_panel, initial_width, initial_height, LOG_LAYOUT_WEIGHT)
    panels = [dashboard_panel, schematic_panel, matrix_panel, plan_telemetry_panel, log_panel]

    def recalculate_layout(width, height):
        nonlocal av_img, obstacle_img
        screen_dims['width'],screen_dims['height'] = width,height
        visible_panels=[p for p in panels if p.visible]; num_visible=len(visible_panels)
        vis_weights=[p.layout_weight for p in visible_panels]; total_vis_weight=sum(vis_weights)
        total_weight=SIM_LAYOUT_WEIGHT+total_vis_weight; total_weight=max(total_weight,1e-6)
        total_padding=max(0,num_visible)*PANEL_PADDING; available_width=width-total_padding
        layout['sim_width']=int((SIM_LAYOUT_WEIGHT/total_weight)*available_width); layout['sim_height']=height
        layout['cell_size']=min(layout['sim_width']/GRID_COLS,layout['sim_height']/GRID_ROWS_ONSCREEN) if GRID_COLS>0 and GRID_ROWS_ONSCREEN>0 else 0
        panel_x = layout['sim_width'] + PANEL_PADDING
        for panel in panels: # Order matters now
            if panel.visible:
                panel_w = int((panel.layout_weight / total_weight) * available_width)
                panel_w = max(panel.min_width, panel_w) if panel_w < panel.min_width else panel_w
                panel.x,panel.y,panel.width,panel.height=panel_x,0,panel_w,height
                panel.screen_width,panel.screen_height=width,height; panel_x+=panel_w+PANEL_PADDING
            else: panel.x,panel.width=-1,0
        dpi=100; dash_w=dashboard_panel.width if dashboard_panel.visible else 200
        graph_w_px,graph_h_px_calc=max(20,dash_w-40),max(20,int((height-70)/3-15)); graph_h_px=max(graph_h_px_calc,graph_w_px/3)
        layout['graph_size_inches']=(graph_w_px/dpi,graph_h_px/dpi)
        enlarged_w_px,enlarged_h_px=max(20,int(width*0.4)),max(20,int(height*0.4))
        layout['enlarged_graph_size_inches']=(enlarged_w_px/dpi,enlarged_h_px/dpi)
        av_img,obstacle_img=try_load_images(logs,layout['cell_size'],theme)

    def update_graphs_and_cache():
        nonlocal graph_surfaces
        try: graph_surfaces=update_graphs(completion_times,collision_counts,success_rates,theme,layout['graph_size_inches'])
        except Exception as e: ts=datetime.datetime.now().strftime('%H:%M:%S'); logs.append(f"[{ts}] ERR Graph update: {e}")

    def reset():
        nonlocal tick, overlay_state, road_offset, planned_move, current_collision_in_run # Removed stress
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        if run_count > 0: logs.append(f"[{timestamp}] Resetting simulation...")
        occupied=set(); av=Vehicle(GRID_COLS/2,TOTAL_ROAD_ROWS-1,"av"); occupied.add(av.pos())
        potholes=spawn_potholes(occupied,num_potholes,logs); obstacles=spawn_obstacle_vehicles(av,occupied,logs,spawn_prob)
        initial_step_frames = max(1, int(FPS * STEP_SECONDS / INITIAL_SIM_SPEED))
        for ov in obstacles: ov.target, ov.anim_frame = None, initial_step_frames
        av.target, av.anim_frame = None, initial_step_frames

        # --- Initialize road_offset correctly ---
        target_road_offset = max(0, av.row - GRID_ROWS_ONSCREEN // 2)
        road_offset = target_road_offset # Start centered
        # ---

        tick, overlay_state, planned_move = 0, None, None
        current_collision_in_run = 0 # Removed current_vehicle_stress
        return av, obstacles, potholes

    recalculate_layout(initial_width, initial_height)
    run_count, success_count = 0, 0
    av_vehicle, obstacle_vehicles, potholes = reset()
    completion_times = [0]; collision_counts = [0]; success_rates = [0.0]
    update_graphs_and_cache()
    overlay_start, overlay_alpha = 0.0, 0.0
    paused, manual_mode = False, False
    completion_time, collision_count, success_rate = 0, 0, 0.0
    current_collision_in_run = 0 # Removed current_vehicle_stress
    simulation_speed_multiplier = INITIAL_SIM_SPEED
    time_accumulator = 0.0
    MAX_STEPS_PER_FRAME = 5

    running = True
    while running:
        delta_time = clock.tick(FPS)/1000.0; fps = clock.get_fps()
        delta_time = min(delta_time, 0.1) # Clamp delta_time

        step_delay = STEP_SECONDS / simulation_speed_multiplier
        current_step_frames = max(1, int(FPS * step_delay))

        redraw_needed_after_event = False # Flag for manual mode toggle redraw

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: running = False
            if ev.type == pygame.VIDEORESIZE: nw,nh=ev.w,ev.h; nw,nh=max(640,nw),max(480,nh); screen=pygame.display.set_mode((nw,nh),pygame.RESIZABLE); recalculate_layout(nw,nh); update_graphs_and_cache() if run_count>0 or len(completion_times)>1 else None
            if ev.type == pygame.KEYDOWN:
                ts = datetime.datetime.now().strftime('%H:%M:%S')
                if ev.key == pygame.K_ESCAPE: running = False
                if ev.key == pygame.K_r: av_vehicle, obstacle_vehicles, potholes = reset()
                if ev.key == pygame.K_p: paused = not paused; logs.append(f"[{ts}] {'Paused' if paused else 'Resumed'}"); redraw_needed_after_event = True
                if ev.key == pygame.K_m: manual_mode = not manual_mode; logs.append(f"[{ts}] Manual mode {'ON' if manual_mode else 'OFF'}"); redraw_needed_after_event = True
                if ev.key == pygame.K_a: changed=False; [setattr(p,'visible',True) or (changed:=True) for p in panels if not p.visible]; logs.append(f"[{ts}] Showing all panels."); recalculate_layout(screen_dims['width'],screen_dims['height']); update_graphs_and_cache() if changed and (run_count>0 or len(completion_times)>1) else None
                if ev.key == pygame.K_PLUS or ev.key == pygame.K_EQUALS: simulation_speed_multiplier=min(MAX_SIM_SPEED,simulation_speed_multiplier+SPEED_INCREMENT); logs.append(f"[{ts}] Speed -> {simulation_speed_multiplier:.1f}x")
                if ev.key == pygame.K_MINUS: simulation_speed_multiplier=max(MIN_SIM_SPEED,simulation_speed_multiplier-SPEED_INCREMENT); logs.append(f"[{ts}] Speed -> {simulation_speed_multiplier:.1f}x")
                if manual_mode and not overlay_state and not av_vehicle.is_animating(current_step_frames):
                    nt=None; avc,avr=int(av_vehicle.col),int(av_vehicle.row)
                    if ev.key==pygame.K_UP: nt=(avc,avr-1)
                    elif ev.key==pygame.K_DOWN: nt=(avc,avr+1)
                    elif ev.key==pygame.K_LEFT: nt=(avc-1,avr)
                    elif ev.key==pygame.K_RIGHT: nt=(avc+1,avr)
                    if nt and inside(nt[0],nt[1]): planned_move=nt; commit_av_move(av_vehicle,planned_move, current_step_frames); tick+=1
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                pos=pygame.mouse.get_pos()
                if enlarged_graph: enlarged_graph, enlarged_graph_index = None,-1; continue
                panel_ui_clicked=False
                for panel in panels:
                    if panel.handle_click(pos): panel_ui_clicked=True; recalculate_layout(screen_dims['width'],screen_dims['height']); update_graphs_and_cache() if run_count>0 or len(completion_times)>1 else None; break
                if panel_ui_clicked: continue
                panel_interaction=False
                for panel in panels:
                    if panel.start_drag(pos) or panel.start_resize(pos): panel_interaction=True; break
                if not panel_interaction:
                    dash_x,dash_y,dash_w,dash_h=dashboard_panel.x,dashboard_panel.y,dashboard_panel.width,dashboard_panel.height
                    if dashboard_panel.visible and dash_x<pos[0]<dash_x+dash_w:
                        try:
                            title_h = fonts['title'].get_sized_height()
                            graph_h=(dash_h - (title_h + 40))/3
                            graph_region_y=dash_y + title_h + 20
                            if graph_h > 0:
                                clicked_idx=-1; y_click = pos[1]
                                if graph_region_y <= y_click < graph_region_y+graph_h: clicked_idx=0
                                elif graph_region_y+graph_h <= y_click < graph_region_y+2*graph_h: clicked_idx=1
                                elif graph_region_y+2*graph_h <= y_click < graph_region_y+3*graph_h: clicked_idx=2
                                if clicked_idx != -1 and graph_surfaces:
                                    ts=datetime.datetime.now().strftime('%H:%M:%S'); logs.append(f"[{ts}] Enlarging graph {clicked_idx}")
                                    try: enlarged_graph=update_graphs(completion_times,collision_counts,success_rates,theme,layout['enlarged_graph_size_inches'])[clicked_idx]; enlarged_graph_index=clicked_idx
                                    except IndexError: logs.append(f"[{ts}] ERR: Graph index {clicked_idx} invalid.")
                                    except Exception as e: logs.append(f"[{ts}] ERR Enlarging graph: {e}"); enlarged_graph_index=-1
                        except AttributeError: logs.append("WARN: Font metrics not ready for graph click.")
            if ev.type == pygame.MOUSEMOTION: pos=pygame.mouse.get_pos(); [p.update_drag(pos) or p.update_resize(pos) for p in panels]
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1: [p.stop_interaction() for p in panels]

        # --- Force redraw after certain key events ---
        if redraw_needed_after_event:
            draw_scene(screen,av_vehicle,obstacle_vehicles,potholes,fonts,av_img,obstacle_img,tick,overlay_state,overlay_alpha,road_offset,fps,planned_move,paused,manual_mode,completion_time,collision_count,success_rate,logs,theme,graph_surfaces,enlarged_graph,panels,layout, simulation_speed_multiplier) # Removed stress
            # pygame.display.flip() # This might cause flickering if called too often
            redraw_needed_after_event = False # Reset flag

        if paused:
            # Draw scene is needed here to show pause/manual text and keep screen updated
            draw_scene(screen,av_vehicle,obstacle_vehicles,potholes,fonts,av_img,obstacle_img,tick,overlay_state,overlay_alpha,road_offset,fps,planned_move,paused,manual_mode,completion_time,collision_count,success_rate,logs,theme,graph_surfaces,enlarged_graph,panels,layout, simulation_speed_multiplier); continue # Removed stress

        target_road_offset=max(0,av_vehicle.row-GRID_ROWS_ONSCREEN//2); road_offset+=(target_road_offset-road_offset)*0.2

        if overlay_state:
            overlay_alpha = max(0.0, overlay_alpha - delta_time / RESET_DELAY)
            if time.time() - overlay_start >= RESET_DELAY:
                run_count += 1; ts = datetime.datetime.now().strftime('%H:%M:%S')
                if overlay_state == "SUCCESS": success_count+=1; completion_time=tick; completion_times.append(tick); collision_counts.append(current_collision_in_run); logs.append(f"[{ts}] Run {run_count} SUCCESS ({tick} steps).")
                else: collision_count+=1; completion_times.append(0); collision_counts.append(current_collision_in_run); logs.append(f"[{ts}] Run {run_count} FAILED ({overlay_state}).")
                success_rate = success_count/run_count if run_count>0 else 0.0; success_rates.append(success_rate)
                update_graphs_and_cache()
                av_vehicle, obstacle_vehicles, potholes = reset()
            draw_scene(screen,av_vehicle,obstacle_vehicles,potholes,fonts,av_img,obstacle_img,tick,overlay_state,overlay_alpha,road_offset,fps,planned_move,paused,manual_mode,completion_time,collision_count,success_rate,logs,theme,graph_surfaces,enlarged_graph,panels,layout, simulation_speed_multiplier); continue # Removed stress

        # --- Simulation Step Logic ---
        time_accumulator += delta_time
        steps_this_frame = 0

        while time_accumulator >= step_delay and steps_this_frame < MAX_STEPS_PER_FRAME:
            if overlay_state: break
            simulation_step_occurred = True
            time_accumulator -= step_delay; steps_this_frame += 1

            current_animating = any(ov.is_animating(current_step_frames) for ov in obstacle_vehicles) or av_vehicle.is_animating(current_step_frames)
            if not current_animating:
                if not manual_mode:
                    planned_map,planned_targets,initial_map=plan_obstacle_moves(obstacle_vehicles,av_vehicle.pos(),potholes, current_step_frames)
                    planned_move=av_decide_and_move(av_vehicle,planned_map,planned_targets,initial_map,potholes)
                    commit_obstacle_moves(planned_map,obstacle_vehicles, current_step_frames); commit_av_move(av_vehicle,planned_move, current_step_frames)
                    tick+=1; ts=datetime.datetime.now().strftime('%H:%M:%S')
                    # --- COMBINED Collision Checks ---
                    crashed = False
                    if av_vehicle.pos() in potholes or any(ov.pos()==av_vehicle.pos() for ov in obstacle_vehicles):
                        crashed = True
                        if av_vehicle.pos() in potholes:
                            overlay_state = "CRASHED (Pothole)"
                            logs.append(f"[{ts}] CRASH on pothole @ {av_vehicle.pos()}!")
                            potholes.remove(av_vehicle.pos()) # Still remove
                        else:
                             overlay_state = "CRASHED (Vehicle)"
                             logs.append(f"[{ts}] CRASH @ step {tick}, pos {av_vehicle.pos()}")
                        overlay_start=time.time(); overlay_alpha=1.0; current_collision_in_run+=1
                        break # Break inner loop
                    elif int(av_vehicle.row)==0 and not overlay_state:
                         overlay_state="SUCCESS"; overlay_start=time.time(); overlay_alpha=1.0; logs.append(f"[{ts}] Destination @ step {tick}")
                         break # Break inner loop
                    # ---

        if overlay_state: # Check if inner loop set overlay state
             draw_scene(screen,av_vehicle,obstacle_vehicles,potholes,fonts,av_img,obstacle_img,tick,overlay_state,overlay_alpha,road_offset,fps,planned_move,paused,manual_mode,completion_time,collision_count,success_rate,logs,theme,graph_surfaces,enlarged_graph,panels,layout, simulation_speed_multiplier); # Removed stress
             continue

        # --- Update Animations Continuously ---
        anim_delta_frames = delta_time * FPS
        for ov in obstacle_vehicles:
            if ov.target and ov.anim_frame < current_step_frames:
                ov.anim_frame += anim_delta_frames
                if ov.anim_frame >= current_step_frames: ov.col,ov.row=float(ov.target[0]),float(ov.target[1]); ov.target=None; ov.anim_frame=current_step_frames # Clamp
        if av_vehicle.target and av_vehicle.anim_frame < current_step_frames:
            av_vehicle.anim_frame += anim_delta_frames
            if av_vehicle.anim_frame >= current_step_frames: av_vehicle.col,av_vehicle.row=float(av_vehicle.target[0]),float(av_vehicle.target[1]); av_vehicle.target=None; av_vehicle.anim_frame=current_step_frames; planned_move=None if not manual_mode else planned_move
        # ---

        draw_scene(screen,av_vehicle,obstacle_vehicles,potholes,fonts,av_img,obstacle_img,tick,overlay_state,overlay_alpha,road_offset,fps,planned_move,paused,manual_mode,completion_time,collision_count,success_rate,logs,theme,graph_surfaces,enlarged_graph,panels,layout, simulation_speed_multiplier) # Removed stress

def main(): # (remains the same)
    initial_width, initial_height = 1600, 900
    screen = init_pygame_or_exit(initial_width, initial_height)
    config = {'num_potholes': 5, 'spawn_prob': SPAWN_PROB, 'theme': 'dark'}

    def start_simulation():
        menu_theme.background_color = THEMES[config['theme']]['BACKGROUND']
        run_simulation(screen, config['num_potholes'], config['spawn_prob'], config['theme'], screen.get_width(), screen.get_height())

    def set_potholes(value):
        try: p_count = int(value); config['num_potholes'] = max(0, p_count)
        except (ValueError, TypeError): config['num_potholes'] = 5

    def set_spawn_prob(value):
        try: config['spawn_prob'] = max(0.0, min(1.0, float(value or SPAWN_PROB)))
        except ValueError: config['spawn_prob'] = SPAWN_PROB

    def set_theme(value_tuple, theme_key):
        config['theme'] = theme_key
        new_bg,new_fg,new_sel = THEMES[theme_key]['BACKGROUND'],THEMES[theme_key]['WHITE'],THEMES[theme_key]['AV_COLOR']
        mt=menu.get_theme(); mt.background_color=new_bg; mt.widget_font_color=new_fg; mt.title_font_color=new_fg; mt.selection_color=new_sel

    initial_theme = config['theme']
    menu_theme = pygame_menu.themes.THEME_DARK.copy()
    menu_theme.title_font, menu_theme.widget_font = pygame_menu.font.FONT_OPEN_SANS, pygame_menu.font.FONT_OPEN_SANS
    menu_theme.title_font_size, menu_theme.widget_font_size = 30, 20; menu_theme.widget_margin = (0, 15)
    menu_theme.selection_color=THEMES[initial_theme]['AV_COLOR']; menu_theme.background_color=THEMES[initial_theme]['BACKGROUND']
    menu_theme.widget_font_color=THEMES[initial_theme]['WHITE']; menu_theme.title_font_color=THEMES[initial_theme]['WHITE']

    menu = pygame_menu.Menu('AV Simulation Config', 600, 450, theme=menu_theme)
    menu.add.label('Simulation Parameters', font_size=24)
    menu.add.text_input('Potholes: ', default='5', input_type=pygame_menu.locals.INPUT_INT, maxchar=2, onchange=set_potholes)
    menu.add.text_input('Spawn Prob: ', default=str(SPAWN_PROB), input_type=pygame_menu.locals.INPUT_FLOAT, maxchar=4, onchange=set_spawn_prob)
    theme_items = [('Dark','dark'),('Light','light'),('Tron','tron'),('Wireframe','wireframe')]
    menu.add.selector('Theme: ', theme_items, onchange=set_theme)
    menu.add.button('Start Simulation', start_simulation); menu.add.button('Quit', pygame_menu.events.EXIT)

    alpha, clock = 0, pygame.time.Clock()
    while alpha < 255:
        events=pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.VIDEORESIZE: screen=pygame.display.set_mode((e.w,e.h),pygame.RESIZABLE); menu.resize(e.w,e.h)
        menu.update(events); screen.fill(THEMES[config['theme']]['BACKGROUND']); menu.draw(screen)
        overlay=pygame.Surface(screen.get_size(),pygame.SRCALPHA); overlay.fill((0,0,0,255-alpha)); screen.blit(overlay,(0,0))
        pygame.display.flip(); alpha=min(255,alpha+15); clock.tick(60)

    menu.mainloop(screen)
    pygame.quit(); sys.exit()

if __name__ == "__main__":
    main()