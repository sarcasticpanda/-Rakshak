"""
Debug: Check what's wrong with stampede detection
"""
import sys
sys.path.insert(0, str(__file__).replace('debug_stampede.py', ''))

import cv2
from pathlib import Path
from ultralytics import YOLO

# Test different confidence thresholds on first frame
video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\stampede.mp4")

if not video_path.exists():
    print("Video not found!")
    exit()

cap = cv2.VideoCapture(str(video_path))
ret, frame = cap.read()
cap.release()

if not ret:
    print("Can't read frame!")
    exit()

print(f"Frame shape: {frame.shape}")

model = YOLO("yolov8m.pt")
model.to("cuda")

thresholds = [0.01, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40]

print("\n" + "="*60)
print("TESTING DIFFERENT CONFIDENCE THRESHOLDS ON STAMPEDE")
print("="*60)

for conf in thresholds:
    results = model.predict(
        source=frame,
        conf=conf,
        iou=0.35,
        classes=[0],
        max_det=2000,
        imgsz=1280,
        half=True,
        device="cuda",
        verbose=False
    )
    
    count = len(results[0].boxes) if results else 0
    density = (count / (frame.shape[0] * frame.shape[1])) * 100000
    
    print(f"Conf={conf:.2f} → {count:3d} people, Density={density:.1f}")

print("="*60)
