"""
FIXED ByteTrack Test - No extra boxes, properly synced
"""
import sys
sys.path.insert(0, str(__file__).replace('test_bytetrack_fixed.py', ''))

import cv2
from pathlib import Path
from app.core.detector import PersonDetector
from app.core.tracker import ByteTracker
import numpy as np
import time


def draw_tracks(frame, tracks):
    """Draw tracked people - simple clean boxes"""
    colors = [
        (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), 
        (255, 0, 255), (0, 255, 255), (128, 255, 0), (255, 128, 0)
    ]
    
    for track in tracks:
        tid = track['track_id']
        x1, y1, x2, y2 = map(int, track['bbox'])
        color = colors[tid % len(colors)]
        
        # Draw box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw ID (small, at top)
        cv2.putText(frame, str(tid), (x1+2, y1+15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return frame


def main():
    print("=" * 70)
    print("FIXED BYTETRACK TEST")
    print("No ghost boxes, no oversized boxes, proper tracking")
    print("=" * 70)
    
    test_videos = [
        (Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test_d1.mp4"), "Dense"),
        (Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4"), "Sparse"),
    ]
    
    available = [(p, n) for p, n in test_videos if p.exists()]
    
    output_dir = Path(__file__).parent / "output" / "bytetrack_final"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Output: {output_dir}")
    print("\n🔧 Loading detector...")
    detector = PersonDetector()
    
    for video_path, video_name in available:
        print(f"\n{'='*60}")
        print(f"Processing: {video_name}")
        print(f"{'='*60}")
        
        # Fresh tracker with strict settings
        tracker = ByteTracker(
            track_thresh=0.3,
            track_buffer=15,
            match_thresh=0.4,
            min_hits=3,
            max_age=10
        )
        
        cap = cv2.VideoCapture(str(video_path))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"   Resolution: {width}x{height}")
        
        output_path = output_dir / f"{video_name}_tracked.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        frames_to_process = min(150, total)
        det_counts = []
        track_counts = []
        
        for i in range(frames_to_process):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect
            detections = detector.detect(frame)
            
            # Track - pass frame size for validation
            tracks = tracker.update(detections, frame_size=(width, height))
            
            det_counts.append(len(detections))
            track_counts.append(len(tracks))
            
            # Draw
            annotated = draw_tracks(frame.copy(), tracks)
            
            # Info overlay
            cv2.putText(annotated, f"{video_name}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(annotated, f"Det: {len(detections)} Track: {len(tracks)}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            out.write(annotated)
            
            if (i+1) % 30 == 0:
                print(f"   Frame {i+1}: {len(detections)} det, {len(tracks)} tracked")
        
        cap.release()
        out.release()
        
        print(f"\n   Results:")
        print(f"   ├─ Avg Detections: {np.mean(det_counts):.1f}")
        print(f"   ├─ Avg Tracked: {np.mean(track_counts):.1f}")
        print(f"   ├─ Total IDs: {tracker.get_total_ids()}")
        print(f"   └─ Saved: {output_path.name}")
        
        # VALIDATION: Tracked should be <= Detections (no ghost boxes)
        if np.mean(track_counts) > np.mean(det_counts) * 1.2:
            print(f"   ⚠️  Warning: More tracks than detections - possible ghosts")
        else:
            print(f"   ✅ Clean: Tracked ≈ Detected (no ghost boxes)")
    
    print("\n" + "=" * 70)
    print("✅ COMPLETE")
    print("=" * 70)
    print(f"\n📁 Check videos in: {output_dir}")
    print("   • No oversized boxes covering buildings/sky")
    print("   • Tracked count ≈ Detection count (no ghosts)")
    print("   • Clean person-sized boxes only")


if __name__ == "__main__":
    main()
