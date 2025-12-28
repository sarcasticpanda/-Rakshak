"""
Configuration file for Stampede-Rakshak system
All global settings and hyperparameters
"""
import os
from pathlib import Path

# ============================================
# PROJECT PATHS
# ============================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# Input sources
IMAGES_DIR = DATA_DIR / "images"
VIDEOS_DIR = DATA_DIR / "videos"

# Output paths
OUTPUT_DIR.mkdir(exist_ok=True)
ANNOTATED_OUTPUT_PATH = OUTPUT_DIR / "annotated_output.mp4"
LOGS_DIR = OUTPUT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ============================================
# VIDEO/FRAME SETTINGS
# ============================================
# For image sequences (MOT17)
DEFAULT_FPS = 10  # Simulated FPS for image sequences
TARGET_RESOLUTION = None  # DO NOT RESIZE - Let YOLO handle it! (resizing destroys small people)
FRAME_SKIP = 1  # Process every Nth frame (1 = no skip)

# ============================================
# YOLO DETECTION SETTINGS (OPTIMIZED FOR 200-400 PEOPLE IN DENSE CROWDS)
# ============================================
YOLO_MODEL = "yolov8m.pt"  # YOLOv8m - Best for high-density crowd detection
YOLO_CONF_THRESHOLD = 0.02  # Balanced - reduces false positives (buildings/signs) while keeping people
YOLO_IOU_THRESHOLD = 0.35   # Aggressive NMS (0.35 = suppress 35%+ overlap, fixes sparse duplicates)
YOLO_DEVICE = "cuda"  # "cuda" or "cpu"
DETECT_PERSON_ONLY = True  # Only detect person class (class_id = 0)

# Critical settings for detecting 400-500 people
YOLO_MAX_DET = 1500  # Maximum detections per image (increased from 300)
YOLO_IMGSZ = 1920    # Large input size for small/distant people (GPU intensive!)
YOLO_HALF = True     # Use FP16 for faster inference on GPU

# Additional filtering for dense Indian crowds
ENABLE_ASPECT_RATIO_FILTER = True  # Filter out vehicles (scooters, bikes)
MIN_PERSON_ASPECT_RATIO = 0.8  # Height/Width - person is taller than wide (reject horizontal boxes)
MAX_PERSON_ASPECT_RATIO = 3.0  # Reject very tall/thin boxes (poles, signs, building edges)

# STRICT Size filtering - reject buildings, sky, large objects
ENABLE_SIZE_FILTER = True
MIN_BOX_AREA = 800        # Minimum pixels (reject tiny noise)
MAX_BOX_AREA = 100000     # Maximum absolute area in pixels (reject huge boxes)
MAX_BOX_AREA_RATIO = 0.04  # Max 4% of frame (a person is usually <4% of frame area)
MIN_BOX_HEIGHT = 40       # Minimum height in pixels
MAX_BOX_HEIGHT = 600      # Maximum height in pixels (allow closer people)
MAX_BOX_HEIGHT_RATIO = 0.5  # Max 50% of frame height (reject full-height boxes)
MAX_BOX_WIDTH = 350       # Maximum width in pixels (person width is limited)
MAX_BOX_WIDTH_RATIO = 0.25  # Max 25% of frame width

# ============================================
# PREPROCESSING (LIGHTING)
# ============================================
ENABLE_CLAHE = True  # Contrast Limited Adaptive Histogram Equalization
CLAHE_CLIP_LIMIT = 2.0
CLAHE_GRID_SIZE = (8, 8)

ENABLE_GAMMA_CORRECTION = False
GAMMA_VALUE = 1.2

ENABLE_BRIGHTNESS_NORM = False
TARGET_BRIGHTNESS = 128

# ============================================
# BYTETRACK SETTINGS
# ============================================
TRACK_BUFFER = 30  # Frames to keep lost tracks
TRACK_THRESH = 0.5  # High confidence track threshold
MATCH_THRESH = 0.8  # IOU matching threshold
MIN_BOX_AREA = 100  # Minimum bounding box area

# Motion history buffer
TRAJECTORY_BUFFER_SIZE = 30  # Store last N positions per track

# ============================================
# MOTION FEATURE SETTINGS
# ============================================
SPEED_THRESHOLD_NORMAL = 50  # pixels/frame
SPEED_THRESHOLD_RUNNING = 100  # pixels/frame
ACCELERATION_THRESHOLD = 20  # pixels/frame²

# ============================================
# CROWD METRICS SETTINGS
# ============================================
DENSITY_HIGH_THRESHOLD = 0.3  # People per pixel² (area ratio)
DENSITY_CRITICAL_THRESHOLD = 0.5
COMPRESSION_THRESHOLD = 50  # Average inter-person distance in pixels
DIRECTION_ENTROPY_THRESHOLD = 0.7  # Normalized entropy

# ============================================
# PANIC AGGREGATION SETTINGS
# ============================================
# Weights for panic score calculation
WEIGHT_SPEED_SPIKE = 0.3
WEIGHT_ACCELERATION_SPIKE = 0.2
WEIGHT_DIRECTION_CHAOS = 0.25
WEIGHT_COMPRESSION = 0.25

PANIC_SCORE_THRESHOLD_WARNING = 0.5
PANIC_SCORE_THRESHOLD_CRITICAL = 0.75

# ============================================
# TEMPORAL CONSISTENCY
# ============================================
TEMPORAL_WINDOW_SIZE = 15  # Frames to smooth panic score
PANIC_PERSISTENCE_THRESHOLD = 10  # Panic must persist for N frames

# ============================================
# RISK ENGINE
# ============================================
RISK_LEVEL_NORMAL = "NORMAL"
RISK_LEVEL_WARNING = "WARNING"
RISK_LEVEL_CRITICAL = "CRITICAL"

# ============================================
# VISUALIZATION SETTINGS
# ============================================
DRAW_BOXES = True
DRAW_TRACK_IDS = True
DRAW_TRAJECTORIES = True
DRAW_DENSITY_HEATMAP = False

BOX_COLOR_NORMAL = (0, 255, 0)  # Green
BOX_COLOR_WARNING = (0, 165, 255)  # Orange
BOX_COLOR_CRITICAL = (0, 0, 255)  # Red
BOX_THICKNESS = 2

FONT_SCALE = 0.6
FONT_THICKNESS = 2

# ============================================
# MULTI-CAMERA SETTINGS (FUTURE)
# ============================================
ENABLE_MULTI_CAMERA = False
CAMERA_CONFIGS = {
    "camera_01": {"source": "images/camera_01", "location": "Main Entrance"},
    "camera_02": {"source": "images/camera_02", "location": "Food Court"},
}

# ============================================
# API SETTINGS
# ============================================
API_HOST = "127.0.0.1"
API_PORT = 8000
API_WORKERS = 1
API_RELOAD = True  # Auto-reload on code changes (dev only)

# ============================================
# DEBUGGING
# ============================================
DEBUG_MODE = True
VERBOSE = True
SAVE_DEBUG_FRAMES = False
DEBUG_FRAMES_DIR = OUTPUT_DIR / "debug_frames"
if SAVE_DEBUG_FRAMES:
    DEBUG_FRAMES_DIR.mkdir(exist_ok=True)
