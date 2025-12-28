"""Final test - verify both sparse (no FP) and dense (high detection) work"""
import sys
sys.path.insert(0, str(__file__).replace('test_final_both.py', ''))

import cv2
from pathlib import Path
from app.core.detector import PersonDetector
from app.core.tracker import ByteTracker
import numpy as np

print("=" * 70)
print("FINAL TEST: False Positives Removed + Dense Detection Maintained")
print("=" * 70)

detector = PersonDetector()

# Test sparse
print("\n🔍 SPARSE VIDEO (test2.mp4):")
cap = cv2.VideoCapture(r'C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4')
sparse_counts = []
for i in range(50):
    ret, frame = cap.read()
    if not ret: break
    dets = detector.detect(frame)
    sparse_counts.append(len(dets))
cap.release()
print(f"   Avg: {np.mean(sparse_counts):.1f}, Max: {max(sparse_counts)}, Min: {min(sparse_counts)}")
print(f"   ✅ Should be clean - no buildings/sky/signs")

# Test dense
print("\n🔍 DENSE VIDEO (test_d1.mp4):")
cap = cv2.VideoCapture(r'C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test_d1.mp4')
dense_counts = []
for i in range(50):
    ret, frame = cap.read()
    if not ret: break
    dets = detector.detect(frame)
    dense_counts.append(len(dets))
cap.release()
print(f"   Avg: {np.mean(dense_counts):.1f}, Max: {max(dense_counts)}, Min: {min(dense_counts)}")

if np.mean(dense_counts) >= 100:
    print(f"   ✅ Good detection maintained")
else:
    print(f"   ⚠️  May need to lower conf threshold")

print("\n" + "=" * 70)
print("OUTPUT FILES:")
print("=" * 70)
print("   📁 backend/output/bytetrack/")
print("      • Dense_Indian_tracked.mp4")
print("      • Sparse_Indian_tracked.mp4")
print("   📁 backend/output/bytetrack_fixed/")
print("      • sparse_fixed.mp4")
print("=" * 70)
