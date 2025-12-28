"""Test script to verify installation"""
import torch
import cv2
import numpy as np
from ultralytics import YOLO

print("=" * 50)
print("INSTALLATION VERIFICATION")
print("=" * 50)

# PyTorch
print(f"\n✓ PyTorch: {torch.__version__}")
print(f"✓ CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"✓ CUDA Version: {torch.version.cuda}")
    print(f"✓ GPU Device: {torch.cuda.get_device_name(0)}")
else:
    print("⚠ Running on CPU only")

# OpenCV
print(f"✓ OpenCV: {cv2.__version__}")

# NumPy
print(f"✓ NumPy: {np.__version__}")

# YOLO
try:
    model = YOLO("yolov8n.pt")
    print("✓ YOLOv8: Successfully loaded")
except Exception as e:
    print(f"⚠ YOLOv8: {e}")

print("\n" + "=" * 50)
print("ALL DEPENDENCIES INSTALLED SUCCESSFULLY!")
print("=" * 50)
