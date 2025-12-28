"""
Verify YOLOv11 installation and dependencies
"""

import sys
import torch

print("=" * 60)
print("DEPENDENCY VERIFICATION FOR YOLOV11")
print("=" * 60)

# Check Python version
print(f"\n1. Python Version: {sys.version}")

# Check PyTorch and CUDA
print(f"\n2. PyTorch Version: {torch.__version__}")
print(f"   CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"   CUDA Version: {torch.version.cuda}")
    print(f"   GPU Device: {torch.cuda.get_device_name(0)}")

# Check Ultralytics
try:
    import ultralytics
    print(f"\n3. Ultralytics Version: {ultralytics.__version__}")
    from ultralytics import YOLO
    print("   ✅ YOLO import successful")
except Exception as e:
    print(f"   ❌ YOLO import failed: {e}")
    sys.exit(1)

# Check OpenCV
try:
    import cv2
    print(f"\n4. OpenCV Version: {cv2.__version__}")
except Exception as e:
    print(f"   ❌ OpenCV import failed: {e}")
    sys.exit(1)

# Check NumPy
try:
    import numpy as np
    print(f"\n5. NumPy Version: {np.__version__}")
except Exception as e:
    print(f"   ❌ NumPy import failed: {e}")
    sys.exit(1)

# Check if YOLOv11 models are available
print("\n6. Checking YOLOv11 Model Availability:")
try:
    # Try to load YOLOv11n (smallest model for quick test)
    print("   Testing YOLOv11n download...")
    model = YOLO('yolo11n.pt')
    print(f"   ✅ YOLOv11n loaded successfully")
    print(f"   Model names: {model.names}")
    
    # Check if it uses GPU
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"   Model will use: {device.upper()}")
    
except Exception as e:
    print(f"   ❌ YOLOv11 model loading failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL DEPENDENCIES VERIFIED SUCCESSFULLY!")
print("=" * 60)
print("\nAvailable YOLOv11 models:")
print("  - yolo11n.pt (Nano - fastest, least accurate)")
print("  - yolo11s.pt (Small)")
print("  - yolo11m.pt (Medium - balanced)")
print("  - yolo11l.pt (Large)")
print("  - yolo11x.pt (Extra Large - most accurate, slowest)")
print("\nRecommendation: Use yolo11m.pt or yolo11x.pt for dense crowd detection")
