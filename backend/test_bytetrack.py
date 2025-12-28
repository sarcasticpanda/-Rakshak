"""
Phase 3 Test: ByteTrack Tracking
Test person tracking with persistent IDs and trajectories
"""

import sys
sys.path.insert(0, str(__file__).replace('test_bytetrack.py', ''))

import cv2
from pathlib import Path
from app.core.detector import PersonDetector
from app.core.tracker import ByteTracker
import numpy as np
import time

def draw_tracks(frame, tracks, show_trajectory=True):
    """Draw tracked people with IDs and trajectories"""
    # Color palette for track IDs
    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
        (0, 255, 255), (128, 0, 0), (0, 128, 0), (0, 0, 128), (128, 128, 0),
        (128, 0, 128), (0, 128, 128), (255, 128, 0), (255, 0, 128), (128, 255, 0),
        (0, 255, 128), (128, 0, 255), (0, 128, 255), (255, 128, 128), (128, 255, 128)
    ]
    
    for track in tracks:
        track_id = track['track_id']
        bbox = track['bbox']
        conf = track['confidence']
        trajectory = track.get('trajectory', [])
        
        # Get color for this track
        color = colors[track_id % len(colors)]
        
        x1, y1, x2, y2 = map(int, bbox)
        
        # Draw bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw track ID
        label = f"ID:{track_id}"
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y1 - h - 10), (x1 + w, y1), color, -1)
        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw trajectory
        if show_trajectory and len(trajectory) > 1:
            for i in range(1, len(trajectory)):
                pt1 = tuple(map(int, trajectory[i-1]))
                pt2 = tuple(map(int, trajectory[i]))
                # Fade older points
                alpha = i / len(trajectory)
                thickness = max(1, int(alpha * 3))
                cv2.line(frame, pt1, pt2, color, thickness)
    
    return frame


def main():
    print("=" * 80)
    print("PHASE 3: BYTETRACK TRACKING TEST")
    print("Testing person tracking with persistent IDs")
    print("=" * 80)
    
    # Test videos
    test_videos = [
        (Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test_d1.mp4"), "Dense_Indian"),
        (Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4"), "Sparse_Indian"),
    ]
    
    available = [(p, n) for p, n in test_videos if p.exists()]
    if not available:
        print("❌ No test videos found!")
        return
    
    print(f"\n✅ Found {len(available)} test videos")
    
    # Output directory
    output_dir = Path(__file__).parent / "output" / "bytetrack"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output: {output_dir}")
    
    # Initialize detector and tracker
    print("\n🔧 Initializing detector...")
    detector = PersonDetector()
    
    print("🔧 Initializing ByteTracker...")
    
    for video_path, video_name in available:
        print(f"\n{'='*70}")
        print(f"Processing: {video_name}")
        print(f"{'='*70}")
        
        # Fresh tracker for each video
        tracker = ByteTracker(
            track_thresh=0.3,   # Lower threshold for tracking (we have low conf detections)
            track_buffer=30,    # Keep tracks for 30 frames after disappearing
            match_thresh=0.5,   # IoU threshold for matching
            min_hits=2,         # Confirm after 2 detections
            max_age=30          # Max 30 frames without detection
        )
        
        cap = cv2.VideoCapture(str(video_path))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"   Resolution: {width}x{height}, FPS: {fps}, Frames: {total}")
        
        output_path = output_dir / f"{video_name}_tracked.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        frames_to_process = min(150, total)
        detection_counts = []
        track_counts = []
        process_times = []
        
        for frame_idx in range(frames_to_process):
            ret, frame = cap.read()
            if not ret:
                break
            
            start_time = time.time()
            
            # Detect people
            detections = detector.detect(frame)
            
            # Track people
            tracks = tracker.update(detections)
            
            process_time = (time.time() - start_time) * 1000
            process_times.append(process_time)
            
            detection_counts.append(len(detections))
            track_counts.append(len(tracks))
            
            # Draw tracks
            annotated = draw_tracks(frame.copy(), tracks, show_trajectory=True)
            
            # Overlay info
            cv2.putText(annotated, f"{video_name} - ByteTrack", (10, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.putText(annotated, f"Detections: {len(detections)}", (10, 80),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(annotated, f"Tracked: {len(tracks)}", (10, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(annotated, f"Total IDs: {tracker.get_total_ids()}", (10, 140),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(annotated, f"Frame: {frame_idx+1}/{frames_to_process}", (10, 170),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
            
            out.write(annotated)
            
            if (frame_idx + 1) % 30 == 0:
                print(f"   Frame {frame_idx+1}: {len(detections)} detections, {len(tracks)} tracked, {tracker.get_total_ids()} total IDs")
        
        cap.release()
        out.release()
        
        # Statistics
        avg_det = np.mean(detection_counts)
        avg_tracks = np.mean(track_counts)
        avg_time = np.mean(process_times)
        total_ids = tracker.get_total_ids()
        
        print(f"\n   Results for {video_name}:")
        print(f"   ├─ Avg Detections: {avg_det:.1f}")
        print(f"   ├─ Avg Tracked: {avg_tracks:.1f}")
        print(f"   ├─ Total Unique IDs: {total_ids}")
        print(f"   ├─ Process Time: {avg_time:.1f}ms/frame")
        print(f"   └─ Output: {output_path.name}")
    
    print("\n" + "=" * 80)
    print("✅ BYTETRACK TRACKING COMPLETE")
    print("=" * 80)
    print(f"\n📁 Output videos saved to: {output_dir}")
    print("\n  Watch the videos to verify:")
    print("  1. Each person has a persistent ID (colored box)")
    print("  2. IDs remain consistent across frames")
    print("  3. Trajectories show movement paths")
    print("  4. Lost tracks are recovered when person reappears")
    print("=" * 80)


if __name__ == "__main__":
    main()
