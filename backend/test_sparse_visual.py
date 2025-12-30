"""
Test adaptive detection on sparse videos with visual output
Check for double boxes in sparse scenarios
"""
import sys
sys.path.insert(0, str(__file__).replace('test_sparse_visual.py', ''))

import cv2
import numpy as np
from pathlib import Path
from app.core.detector import PersonDetector
from app.core.tracker import ByteTracker

def test_video(video_path, name, is_image_sequence=False):
    """Test video and generate output with detection boxes"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    detector = PersonDetector()
    tracker = ByteTracker(track_thresh=0.3, track_buffer=15, match_thresh=0.4, min_hits=3, max_age=10)
    
    output_dir = Path(__file__).parent / "output" / "sparse_check"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if is_image_sequence:
        # MOT17 image sequence
        img_files = sorted(video_path.glob("*.jpg"))
        if not img_files:
            print(f"   ❌ No images found in {video_path}")
            return
        first_img = cv2.imread(str(img_files[0]))
        height, width = first_img.shape[:2]
        fps = 10
        total = min(100, len(img_files))
    else:
        # Video file
        cap = cv2.VideoCapture(str(video_path))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total = min(100, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    
    print(f"   Resolution: {width}x{height}")
    print(f"   Processing {total} frames...")
    
    # Output video
    output_path = output_dir / f"{name}_sparse_check.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    det_counts = []
    track_counts = []
    
    for i in range(total):
        if is_image_sequence:
            if i >= len(img_files):
                break
            frame = cv2.imread(str(img_files[i]))
            if frame is None:
                continue
        else:
            ret, frame = cap.read()
            if not ret:
                break
        
        # Detect with adaptive mode
        detections = detector.detect(frame, adaptive=True)
        tracks = tracker.update(detections, frame_size=(width, height))
        
        det_counts.append(len(detections))
        track_counts.append(len(tracks))
        
        # Draw detections in GREEN
        annotated = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Info
        cv2.putText(annotated, f"{name}", (10, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(annotated, f"DETECTED: {len(detections)}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.putText(annotated, f"Frame {i+1}/{total}", (10, 130),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Warning if too many overlaps (double boxes)
        if len(detections) > 0:
            # Simple overlap check: if avg box area is very small relative to frame
            avg_area = np.mean([
                (det['bbox'][2] - det['bbox'][0]) * (det['bbox'][3] - det['bbox'][1])
                for det in detections
            ])
            frame_area = width * height
            if len(detections) > 30 and avg_area < frame_area * 0.005:
                cv2.putText(annotated, "WARNING: Possible double boxes", (10, height-20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        out.write(annotated)
        
        if (i+1) % 20 == 0:
            print(f"   Frame {i+1}: {len(detections)} detected, {len(tracks)} tracked")
    
    if not is_image_sequence:
        cap.release()
    out.release()
    
    avg_det = np.mean(det_counts)
    avg_track = np.mean(track_counts)
    
    print(f"\n   📊 Results:")
    print(f"   ├─ Avg Detections: {avg_det:.1f}")
    print(f"   ├─ Avg Tracks: {avg_track:.1f}")
    print(f"   └─ Saved: {output_path.name}")
    
    # Assessment
    if avg_track > avg_det * 1.2:
        print(f"   ⚠️  WARNING: Tracks > Detections (ghost boxes?)")
    elif avg_det / avg_track > 2.0:
        print(f"   ⚠️  WARNING: Too many detections vs tracks (double boxes?)")
    else:
        print(f"   ✅ GOOD: Detection/tracking ratio looks clean")
    
    return str(output_path)


def main():
    print("=" * 70)
    print("SPARSE VIDEO CHECK - Adaptive Detection")
    print("Checking for double boxes in sparse scenarios")
    print("=" * 70)
    
    videos = []
    
    # Test sparse video from check_vids
    sparse_vid = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4")
    if sparse_vid.exists():
        path = test_video(sparse_vid, "Sparse_test2", is_image_sequence=False)
        videos.append(path)
    
    # Test MOT17
    mot_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\MOT17\MOT17\train\MOT17-02-FRCNN\img1")
    if mot_path.exists():
        path = test_video(mot_path, "MOT17-02_Sparse", is_image_sequence=True)
        videos.append(path)
    
    print("\n" + "=" * 70)
    print("✅ VIDEOS GENERATED")
    print("=" * 70)
    print("\nWatch these videos to check for:")
    print("  1. Are there double/overlapping boxes on the same person?")
    print("  2. Is detection count reasonable for sparse crowd?")
    print("  3. Are boxes clean and tight around people?")
    print("=" * 70)
    
    # Open first video
    if videos:
        print(f"\n🎬 Opening: {videos[0]}")
        return videos[0]

if __name__ == "__main__":
    video = main()
