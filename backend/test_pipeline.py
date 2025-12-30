"""
Test Complete Pipeline with Adaptive Detection + Heatmap
"""
import sys
sys.path.insert(0, str(__file__).replace('test_pipeline.py', ''))

import cv2
from pathlib import Path
from app.core.pipeline import StampedePipeline


def test_video(video_path: Path, name: str, output_dir: Path):
    """Test pipeline on video"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    if not video_path.exists():
        print(f"   ❌ Video not found: {video_path}")
        return
    
    # Initialize pipeline
    pipeline = StampedePipeline(use_heatmap=True, verbose=False)
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"   Resolution: {width}x{height}, FPS: {fps}")
    print(f"   Frames: {total}")
    
    # Output video
    output_path = output_dir / f"{name}_pipeline.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Process
    frame_count = 0
    max_panic = 0
    mode_counts = {'sparse': 0, 'medium': 0, 'dense': 0}
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Process through pipeline
        result = pipeline.process_frame(frame)
        
        # Track stats
        mode_counts[result['scene']['mode']] += 1
        if result['motion']['panic_score'] > max_panic:
            max_panic = result['motion']['panic_score']
        
        # Visualize
        vis_frame = pipeline.visualize(result, show_heatmap=True)
        
        # Frame counter
        cv2.putText(vis_frame, f"Frame {frame_count}/{total}", (width-180, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        out.write(vis_frame)
        
        if frame_count % 50 == 0:
            print(f"   Frame {frame_count}: Mode={result['scene']['mode']}, "
                  f"People={len(result['tracks'])}, "
                  f"Panic={result['motion']['panic_score']:.0f}")
    
    cap.release()
    out.release()
    
    print(f"\n   📊 RESULTS:")
    print(f"   ├─ Frames processed: {frame_count}")
    print(f"   ├─ Max panic: {max_panic:.1f}")
    print(f"   ├─ Mode distribution:")
    for mode, count in mode_counts.items():
        pct = (count / frame_count) * 100
        print(f"   │  └─ {mode}: {count} frames ({pct:.1f}%)")
    print(f"   └─ Output: {output_path.name}")
    
    return str(output_path)


def main():
    print("=" * 70)
    print("COMPLETE PIPELINE TEST")
    print("Adaptive Detection + Heatmap + Tracking + Motion")
    print("=" * 70)
    
    output_dir = Path(__file__).parent / "output" / "pipeline"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    videos = []
    
    # Test 1: Sparse crowd
    print("\n🟢 TEST 1: SPARSE CROWD")
    sparse_vid = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4")
    if sparse_vid.exists():
        path = test_video(sparse_vid, "Sparse", output_dir)
        videos.append(path)
    
    # Test 2: Dense stampede
    print("\n🔴 TEST 2: DENSE STAMPEDE")
    dense_vid = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\stampede.mp4")
    if dense_vid.exists():
        path = test_video(dense_vid, "Stampede", output_dir)
        videos.append(path)
    
    # Test 3: Medium crowd
    print("\n🟡 TEST 3: MEDIUM CROWD")
    medium_vid = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4")
    if medium_vid.exists():
        path = test_video(medium_vid, "Medium", output_dir)
        videos.append(path)
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 70)
    print("\nExpected behavior:")
    print("  🟢 Sparse: Should stay in 'sparse' mode, ~20-25 people, NO duplicates")
    print("  🔴 Dense:  Should switch to 'dense' mode, 150-200 people, high panic")
    print("  🟡 Medium: May switch between modes, 40-70 people")
    print("\nWatch for:")
    print("  ✅ No double boxes in sparse scenes")
    print("  ✅ Detects most people in dense scenes")
    print("  ✅ Heatmap overlay shows crowd hotspots")
    print("  ✅ Panic score high only for real stampede")
    print("=" * 70)
    
    # Open first video
    if videos:
        print(f"\n🎬 Opening first video...")
        import subprocess
        subprocess.Popen(['cmd', '/c', 'start', '', videos[0]], shell=True)


if __name__ == "__main__":
    main()
