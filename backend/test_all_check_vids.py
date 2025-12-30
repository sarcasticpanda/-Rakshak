"""
Test Robust Pipeline on All Check_Vids and MOT17 Videos
Runs the latest robust detection pipeline on all available test videos
"""
import sys
sys.path.insert(0, str(__file__).replace('test_all_check_vids.py', ''))

import cv2
import numpy as np
from pathlib import Path
from app.core.robust_pipeline import RobustDetectionPipeline
from app.core.tracker import ByteTracker
import time


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


def test_video(video_path, name, output_dir):
    """Test video with robust pipeline"""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"{'='*80}")
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ Could not open video: {video_path}")
        return None
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"📹 Resolution: {width}x{height}, FPS: {fps}, Frames: {total}")
    
    # Output
    output_path = output_dir / f"{name}_robust.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Pipeline
    pipeline = RobustDetectionPipeline(enable_heatmap=True)
    tracker = ByteTracker()
    
    frame_num = 0
    counts = []
    modes = []
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_num += 1
        
        # Process
        detections, metadata = pipeline.detect(frame)
        tracks = tracker.update(frame, detections)
        
        # Visualize
        annotated = visualize_detections(frame, detections, metadata, pipeline)
        out.write(annotated)
        
        # Stats
        counts.append(metadata['final_count'])
        modes.append(metadata['mode'])
        
        if frame_num % 30 == 0:
            elapsed = time.time() - start_time
            progress = (frame_num / total) * 100
            print(f"   Frame {frame_num}/{total} ({progress:.1f}%) - "
                  f"Count: {metadata['final_count']}, Mode: {metadata['mode']}, "
                  f"Speed: {frame_num/elapsed:.1f} fps")
    
    cap.release()
    out.release()
    
    elapsed = time.time() - start_time
    
    # Summary
    stats = {
        'name': name,
        'frames': frame_num,
        'avg_count': np.mean(counts) if counts else 0,
        'max_count': max(counts) if counts else 0,
        'min_count': min(counts) if counts else 0,
        'mode_distribution': {
            'sparse': modes.count('sparse'),
            'medium': modes.count('medium'),
            'dense': modes.count('dense')
        },
        'processing_time': elapsed,
        'avg_fps': frame_num / elapsed,
        'output_path': str(output_path)
    }
    
    print(f"\n✅ RESULTS for {name}:")
    print(f"   Average Count: {stats['avg_count']:.1f}")
    print(f"   Max Count: {stats['max_count']}")
    print(f"   Mode Distribution: {stats['mode_distribution']}")
    print(f"   Processing Time: {elapsed:.1f}s ({stats['avg_fps']:.1f} fps)")
    print(f"   Output: {output_path}")
    
    return stats


def main():
    """Test all videos from check_vids and MOT17"""
    
    print("=" * 80)
    print("ROBUST PIPELINE - COMPREHENSIVE VIDEO TEST")
    print("=" * 80)
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    check_vids_dir = project_root / 'check_vids'
    mot17_dir = project_root / 'MOT17' / 'MOT17' / 'train'
    output_dir = Path(__file__).parent / 'output' / 'comprehensive_test'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_stats = []
    
    # Test check_vids videos
    print("\n" + "=" * 80)
    print("TESTING CHECK_VIDS VIDEOS")
    print("=" * 80)
    
    check_vid_files = [
        'stampede.mp4',
        'test2.mp4',
        'test3.mp4',
        'test_d1.mp4'
    ]
    
    for vid_file in check_vid_files:
        vid_path = check_vids_dir / vid_file
        if vid_path.exists():
            stats = test_video(vid_path, vid_file.replace('.mp4', ''), output_dir)
            if stats:
                all_stats.append(stats)
        else:
            print(f"⚠️  Video not found: {vid_path}")
    
    # Test select MOT17 videos (dense crowd scenes)
    print("\n" + "=" * 80)
    print("TESTING MOT17 VIDEOS (Dense Crowd Scenes)")
    print("=" * 80)
    
    mot17_videos = [
        'MOT17-02-FRCNN',  # Shopping mall
        'MOT17-04-FRCNN',  # Train station - very dense
        'MOT17-05-FRCNN',  # City street
        'MOT17-10-FRCNN',  # Shopping area
        'MOT17-13-FRCNN',  # Train station platform
    ]
    
    for mot_name in mot17_videos:
        mot_path = mot17_dir / mot_name / 'img1'
        if not mot_path.exists():
            print(f"⚠️  MOT17 sequence not found: {mot_path}")
            continue
        
        # Create video from image sequence
        print(f"\n📁 Processing MOT17 sequence: {mot_name}")
        images = sorted(list(mot_path.glob('*.jpg')))
        
        if not images:
            print(f"   ⚠️  No images found in {mot_path}")
            continue
        
        print(f"   Found {len(images)} images")
        
        # Create temporary video
        sample = cv2.imread(str(images[0]))
        if sample is None:
            print(f"   ❌ Could not read sample image")
            continue
            
        height, width = sample.shape[:2]
        temp_video = output_dir / f"{mot_name}_temp.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        temp_writer = cv2.VideoWriter(str(temp_video), fourcc, 30, (width, height))
        
        for img_path in images:
            img = cv2.imread(str(img_path))
            if img is not None:
                temp_writer.write(img)
        
        temp_writer.release()
        
        # Process the video
        stats = test_video(temp_video, mot_name, output_dir)
        if stats:
            all_stats.append(stats)
        
        # Clean up temp video
        temp_video.unlink()
    
    # Final Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY - ALL VIDEOS")
    print("=" * 80)
    
    if all_stats:
        summary_file = output_dir / 'test_summary.txt'
        with open(summary_file, 'w') as f:
            f.write("ROBUST PIPELINE - COMPREHENSIVE TEST RESULTS\n")
            f.write("=" * 80 + "\n\n")
            
            for stats in all_stats:
                f.write(f"\nVideo: {stats['name']}\n")
                f.write(f"  Frames: {stats['frames']}\n")
                f.write(f"  Average Count: {stats['avg_count']:.1f}\n")
                f.write(f"  Max Count: {stats['max_count']}\n")
                f.write(f"  Min Count: {stats['min_count']}\n")
                f.write(f"  Mode Distribution:\n")
                for mode, count in stats['mode_distribution'].items():
                    percentage = (count / stats['frames']) * 100
                    f.write(f"    {mode}: {count} frames ({percentage:.1f}%)\n")
                f.write(f"  Processing: {stats['processing_time']:.1f}s ({stats['avg_fps']:.1f} fps)\n")
                f.write(f"  Output: {stats['output_path']}\n")
                f.write("-" * 80 + "\n")
            
            # Overall stats
            total_frames = sum(s['frames'] for s in all_stats)
            total_time = sum(s['processing_time'] for s in all_stats)
            avg_fps = total_frames / total_time if total_time > 0 else 0
            
            f.write(f"\nOVERALL STATISTICS:\n")
            f.write(f"  Total Videos: {len(all_stats)}\n")
            f.write(f"  Total Frames: {total_frames}\n")
            f.write(f"  Total Time: {total_time:.1f}s\n")
            f.write(f"  Average FPS: {avg_fps:.1f}\n")
        
        print(f"\n✅ Summary saved to: {summary_file}")
        print(f"✅ All output videos in: {output_dir}")
        
        # Print summary to console
        print("\n📊 Quick Overview:")
        for stats in all_stats:
            print(f"   {stats['name']}: Avg={stats['avg_count']:.1f}, "
                  f"Max={stats['max_count']}, "
                  f"FPS={stats['avg_fps']:.1f}")
    else:
        print("\n⚠️  No videos were processed successfully")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
