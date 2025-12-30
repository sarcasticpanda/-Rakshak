"""
Test Robust Detection Pipeline
Validates temporal filtering, duplicate removal, and adaptive modes
"""
import sys
sys.path.insert(0, str(__file__).replace('test_robust_pipeline.py', ''))

import cv2
import numpy as np
from pathlib import Path
from app.core.robust_pipeline import RobustDetectionPipeline
from app.core.tracker import ByteTracker


def visualize_detections(frame, detections, metadata, pipeline=None):
    """Draw detections with metadata and heatmap overlay"""
    annotated = frame.copy()
    
    # Add heatmap overlay if available
    if pipeline and pipeline.heatmap and pipeline.heatmap.is_bootstrapped():
        annotated = pipeline.heatmap.get_visualization(annotated, alpha=0.3)
    
    # Draw each detection
    for det in detections:
        x1, y1, x2, y2 = map(int, det['bbox'])
        conf = det['confidence']
        is_synthetic = det.get('synthetic', False)
        
        # Color by type
        if is_synthetic:
            color = (255, 0, 255)  # Magenta - synthetic
        elif conf > 0.5:
            color = (0, 255, 0)  # Green - high conf
        elif conf > 0.25:
            color = (0, 255, 255)  # Yellow - medium
        else:
            color = (0, 165, 255)  # Orange - low conf
        
        thickness = 3 if is_synthetic else 2
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
        
        label = f"{'SYN' if is_synthetic else ''}{conf:.2f}"
        cv2.putText(annotated, label, (x1, y1-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Dashboard
    mode = metadata['mode']
    mode_colors = {
        'sparse': (0, 255, 0),
        'medium': (0, 255, 255),
        'dense': (0, 0, 255)
    }
    mode_color = mode_colors.get(mode, (255, 255, 255))
    
    cv2.rectangle(annotated, (10, 10), (450, 180), (0, 0, 0), -1)
    cv2.rectangle(annotated, (10, 10), (450, 180), (255, 255, 255), 2)
    
    cv2.putText(annotated, f"MODE: {mode.upper()}", (20, 40),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, mode_color, 2)
    cv2.putText(annotated, f"Final Count: {metadata['final_count']}", (20, 75),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Pipeline steps
    y = 105
    cv2.putText(annotated, f"Raw: {metadata['raw_count']}", (20, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    y += 20
    if 'heatmap_validated_count' in metadata:
        cv2.putText(annotated, f"Heatmap: {metadata['heatmap_validated_count']}", (20, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        y += 20
    cv2.putText(annotated, f"Temporal: {metadata['temporal_validated_count']}", (20, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Heatmap status
    if metadata.get('heatmap_bootstrapped', False):
        cv2.putText(annotated, "Heatmap: ACTIVE", (250, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    else:
        cv2.putText(annotated, "Heatmap: Warming...", (250, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
    
    return annotated


def test_video(video_path, name):
    """Test video with robust pipeline"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    cap = cv2.VideoCapture(str(video_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"   Resolution: {width}x{height}, FPS: {fps}")
    
    # Output
    output_dir = Path(__file__).parent / "output" / "robust_pipeline"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{name}_robust.mp4"
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Pipeline
    pipeline = RobustDetectionPipeline(enable_heatmap=True)
    
    frame_count = 0
    final_counts = []
    raw_counts = []
    synthetic_counts = []
    modes = []
    
    while frame_count < min(total, 200):  # Process first 200 frames
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Run robust pipeline
        detections, metadata = pipeline.detect(frame)
        
        final_counts.append(metadata['final_count'])
        raw_counts.append(metadata['raw_count'])
        synthetic_count = sum(1 for d in detections if d.get('synthetic', False))
        synthetic_counts.append(synthetic_count)
        modes.append(metadata['mode'])
        
        # Visualize
        annotated = visualize_detections(frame, detections, metadata, pipeline)
        
        # Frame counter
        cv2.putText(annotated, f"Frame {frame_count}/{min(total, 200)}", 
                   (width-200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        out.write(annotated)
        
        if frame_count % 25 == 0:
            print(f"   Frame {frame_count}: Mode={metadata['mode']}, "
                  f"Raw={metadata['raw_count']}, Final={metadata['final_count']}, Synthetic={synthetic_count}")
    
    cap.release()
    out.release()
    
    # Statistics
    print(f"\n   📊 Statistics:")
    print(f"   ├─ Frames processed: {frame_count}")
    print(f"   ├─ Avg raw detections: {np.mean(raw_counts):.1f}")
    print(f"   ├─ Avg final count: {np.mean(final_counts):.1f}")
    print(f"   ├─ Avg synthetic: {np.mean(synthetic_counts):.1f}")
    print(f"   ├─ Filtering: {(1 - np.mean(final_counts)/np.mean(raw_counts))*100:.1f}% removed")
    print(f"   ├─ Gap filling: +{np.sum(synthetic_counts)} synthetic boxes")
    
    # Mode distribution
    sparse_frames = modes.count('sparse')
    medium_frames = modes.count('medium')
    dense_frames = modes.count('dense')
    
    print(f"   ├─ Mode distribution:")
    print(f"   │  ├─ Sparse: {sparse_frames} frames ({sparse_frames/frame_count*100:.0f}%)")
    print(f"   │  ├─ Medium: {medium_frames} frames ({medium_frames/frame_count*100:.0f}%)")
    print(f"   │  └─ Dense:  {dense_frames} frames ({dense_frames/frame_count*100:.0f}%)")
    print(f"   └─ Output: {output_path.name}")
    
    return str(output_path)


def main():
    print("=" * 70)
    print("ROBUST DETECTION PIPELINE TEST")
    print("Features: Temporal Validation + Motion Consistency + Adaptive Mode")
    print("=" * 70)
    
    videos = []
    
    # Test sparse
    sparse_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4")
    if sparse_path.exists():
        video = test_video(sparse_path, "Sparse")
        videos.append(video)
    
    # Test dense stampede
    dense_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\stampede.mp4")
    if dense_path.exists():
        video = test_video(dense_path, "Stampede")
        videos.append(video)
    
    # Test medium (test3)
    medium_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4")
    if medium_path.exists():
        video = test_video(medium_path, "Medium")
        videos.append(video)
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 70)
    print("\nCheck for:")
    print("  ✓ Sparse: No double boxes, mode stays sparse, heatmap overlay")
    print("  ✓ Dense: High detection count, mode switches to dense, gap filling (magenta boxes)")
    print("  ✓ Smooth counts: No flickering (temporal + heatmap working)")
    print("  ✓ Heatmap: Red/yellow zones show crowd locations")
    print("=" * 70)
    
    if videos:
        return videos[0]


if __name__ == "__main__":
    video = main()
