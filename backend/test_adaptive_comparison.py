"""
Test adaptive detection: Compare sparse vs dense detection counts
"""
import sys
sys.path.insert(0, str(__file__).replace('test_adaptive_comparison.py', ''))

import cv2
from pathlib import Path
from app.core.detector import PersonDetector

def test_video(video_path, name):
    """Test video and show detection counts"""
    cap = cv2.VideoCapture(str(video_path))
    
    detector = PersonDetector()
    
    # Test first 10 frames
    counts_adaptive = []
    counts_normal = []
    
    for i in range(10):
        ret, frame = cap.read()
        if not ret:
            break
        
        # Adaptive mode (auto-detects density)
        det_adaptive = detector.detect(frame, adaptive=True)
        counts_adaptive.append(len(det_adaptive))
        
        # Normal mode (fixed settings)
        det_normal = detector.detect(frame, adaptive=False)
        counts_normal.append(len(det_normal))
    
    cap.release()
    
    import numpy as np
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{'='*60}")
    print(f"Adaptive Mode:  {np.mean(counts_adaptive):.1f} people/frame (avg)")
    print(f"Normal Mode:    {np.mean(counts_normal):.1f} people/frame (avg)")
    print(f"Improvement:    {np.mean(counts_adaptive) - np.mean(counts_normal):+.1f}")
    print(f"{'='*60}")

def main():
    print("\n" + "="*60)
    print("ADAPTIVE DETECTION TEST")
    print("Comparing detection counts: Adaptive vs Normal")
    print("="*60)
    
    # Test sparse video
    test_video(
        Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4"),
        "SPARSE CROWD (test2.mp4)"
    )
    
    # Test dense stampede
    test_video(
        Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\stampede.mp4"),
        "DENSE STAMPEDE (stampede.mp4)"
    )
    
    print("\n✅ If adaptive > normal for stampede = Working!")
    print("✅ If adaptive ≈ normal for sparse = Correct (no double boxes)")

if __name__ == "__main__":
    main()
