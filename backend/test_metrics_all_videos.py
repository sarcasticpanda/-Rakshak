"""
Comprehensive Crowd Metrics Analysis
Tests all check_vids and MOT17 videos to understand metric ranges
"""
import sys
sys.path.insert(0, str(__file__).replace('test_metrics_all_videos.py', ''))

import cv2
import numpy as np
from pathlib import Path
from app.core.robust_pipeline import RobustDetectionPipeline
from app.core.tracker import ByteTracker
from app.core.crowd_metrics import CrowdMetrics
import time


def analyze_video(video_path: Path, name: str, max_frames: int = 200):
    """Analyze one video and return metrics summary"""
    
    print(f"\n{'='*70}")
    print(f"📹 Analyzing: {name}")
    print(f"{'='*70}")
    
    if not video_path.exists():
        print(f"❌ Not found: {video_path}")
        return None
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ Could not open: {video_path}")
        return None
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"   Resolution: {width}x{height}, FPS: {fps}, Total: {total} frames")
    print(f"   Processing first {max_frames} frames...")
    
    # Initialize
    pipeline = RobustDetectionPipeline(enable_heatmap=True)
    tracker = ByteTracker()
    crowd_metrics = CrowdMetrics()
    
    metrics_log = []
    frame_count = 0
    start_time = time.time()
    
    while frame_count < max_frames and frame_count < total:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Detection + Tracking
        detections, metadata = pipeline.detect(frame)
        tracks = tracker.update(detections, frame_size=(width, height))
        
        # Metrics
        metrics = crowd_metrics.calculate(
            tracks=tracker.tracks,
            frame_shape=(height, width),
            heatmap=pipeline.heatmap
        )
        
        metrics_log.append(metrics)
        
        if frame_count % 50 == 0:
            print(f"   Frame {frame_count}/{max_frames}...")
    
    cap.release()
    elapsed = time.time() - start_time
    
    if not metrics_log:
        print(f"❌ No metrics collected")
        return None
    
    # Calculate statistics
    result = {
        'name': name,
        'frames': frame_count,
        'fps_processed': frame_count / elapsed,
        
        # Count
        'count_avg': np.mean([m['count'] for m in metrics_log]),
        'count_max': np.max([m['count'] for m in metrics_log]),
        'count_min': np.min([m['count'] for m in metrics_log]),
        'count_std': np.std([m['count'] for m in metrics_log]),
        
        # Density
        'density_avg': np.mean([m['density'] for m in metrics_log]),
        'density_norm_avg': np.mean([m['density_normalized'] for m in metrics_log]),
        'density_max': np.max([m['density'] for m in metrics_log]),
        
        # Compression
        'compression_avg': np.mean([m['compression'] for m in metrics_log]),
        'compression_norm_avg': np.mean([m['compression_normalized'] for m in metrics_log]),
        'compression_min': np.min([m['compression'] for m in metrics_log]),
        
        # Velocity Variance
        'variance_avg': np.mean([m['velocity_variance'] for m in metrics_log]),
        'variance_norm_avg': np.mean([m['velocity_variance_normalized'] for m in metrics_log]),
        'variance_max': np.max([m['velocity_variance'] for m in metrics_log]),
        
        # Direction Entropy
        'entropy_avg': np.mean([m['direction_entropy'] for m in metrics_log]),
        'entropy_norm_avg': np.mean([m['direction_entropy_normalized'] for m in metrics_log]),
        
        # Heatmap
        'heatmap_comp_avg': np.mean([m['heatmap_compression'] for m in metrics_log]),
        'heatmap_comp_norm_avg': np.mean([m['heatmap_compression_normalized'] for m in metrics_log]),
        
        # Speed
        'speed_avg': np.mean([m['avg_speed'] for m in metrics_log]),
        'speed_max': np.mean([m['max_speed'] for m in metrics_log]),
        'accel_avg': np.mean([m['avg_acceleration'] for m in metrics_log]),
        'accel_max': np.mean([m['max_acceleration'] for m in metrics_log]),
        
        # Panic indicators
        'high_speed_ratio_avg': np.mean([m['high_speed_ratio'] for m in metrics_log]),
    }
    
    # Calculate preview risk
    result['preview_risk'] = (
        result['density_norm_avg'] * 0.20 +
        result['compression_norm_avg'] * 0.25 +
        result['variance_norm_avg'] * 0.20 +
        result['entropy_norm_avg'] * 0.15 +
        result['heatmap_comp_norm_avg'] * 0.20
    ) * 100
    
    # Print summary
    print(f"\n   📊 Summary:")
    print(f"      People: {result['count_avg']:.1f} (±{result['count_std']:.1f}), Max: {result['count_max']}")
    print(f"      Density: {result['density_avg']:.2f} people/100k px")
    print(f"      Compression: {result['compression_avg']:.1f} px avg distance")
    print(f"      Speed: {result['speed_avg']:.2f} px/frame (max: {result['speed_max']:.2f})")
    print(f"      High Speed Ratio: {result['high_speed_ratio_avg']*100:.1f}%")
    print(f"      Preview Risk: {result['preview_risk']:.1f}/100")
    print(f"      Processing: {result['fps_processed']:.1f} fps")
    
    return result


def main():
    """Analyze all videos"""
    
    print("=" * 80)
    print("COMPREHENSIVE CROWD METRICS ANALYSIS")
    print("=" * 80)
    print("\nObjective: Understand metric ranges across different scenarios")
    print("This will help tune the risk engine thresholds in Phase 2")
    print("=" * 80)
    
    results = []
    
    # ========================================
    # CHECK_VIDS VIDEOS
    # ========================================
    
    print("\n" + "=" * 80)
    print("PART 1: CHECK_VIDS VIDEOS")
    print("=" * 80)
    
    check_vids_dir = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids")
    
    check_vids_videos = [
        ("test2.mp4", "Sparse - Normal crowd"),
        ("test3.mp4", "Medium - Moderate density"),
        ("stampede.mp4", "Dense - High density/stampede"),
        ("test_d1.mp4", "Unknown - To be classified"),
    ]
    
    for video_name, description in check_vids_videos:
        video_path = check_vids_dir / video_name
        result = analyze_video(video_path, f"{video_name} ({description})", max_frames=100)
        if result:
            results.append(result)
    
    # ========================================
    # MOT17 VIDEOS
    # ========================================
    
    print("\n" + "=" * 80)
    print("PART 2: MOT17 DATASET")
    print("=" * 80)
    
    mot17_dir = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\MOT17\MOT17\train")
    
    mot17_videos = [
        ("MOT17-02-FRCNN", "Shopping mall - sparse"),
        ("MOT17-04-FRCNN", "Train station - dense"),
    ]
    
    for seq_name, description in mot17_videos:
        img_dir = mot17_dir / seq_name / "img1"
        
        if not img_dir.exists():
            print(f"\n⚠️  Skipping {seq_name} (not found)")
            continue
        
        # Create temporary video from image sequence
        images = sorted(list(img_dir.glob("*.jpg")))
        
        if not images:
            print(f"\n⚠️  No images in {seq_name}")
            continue
        
        print(f"\n{'='*70}")
        print(f"📹 Analyzing: {seq_name} ({description})")
        print(f"{'='*70}")
        print(f"   Found {len(images)} images, processing first 150...")
        
        # Read first image for dimensions
        sample = cv2.imread(str(images[0]))
        if sample is None:
            print(f"❌ Could not read images")
            continue
        
        height, width = sample.shape[:2]
        
        # Initialize
        pipeline = RobustDetectionPipeline(enable_heatmap=True)
        tracker = ByteTracker()
        crowd_metrics = CrowdMetrics()
        
        metrics_log = []
        frame_count = 0
        start_time = time.time()
        max_frames = min(100, len(images))
        
        for img_path in images[:max_frames]:
            frame = cv2.imread(str(img_path))
            if frame is None:
                continue
            
            frame_count += 1
            
            # Detection + Tracking
            detections, metadata = pipeline.detect(frame)
            tracks = tracker.update(detections, frame_size=(width, height))
            
            # Metrics
            metrics = crowd_metrics.calculate(
                tracks=tracker.tracks,
                frame_shape=(height, width),
                heatmap=pipeline.heatmap
            )
            
            metrics_log.append(metrics)
            
            if frame_count % 50 == 0:
                print(f"   Frame {frame_count}/{max_frames}...")
        
        elapsed = time.time() - start_time
        
        if metrics_log:
            # Calculate statistics
            result = {
                'name': f"{seq_name} ({description})",
                'frames': frame_count,
                'fps_processed': frame_count / elapsed,
                'count_avg': np.mean([m['count'] for m in metrics_log]),
                'count_max': np.max([m['count'] for m in metrics_log]),
                'count_std': np.std([m['count'] for m in metrics_log]),
                'density_avg': np.mean([m['density'] for m in metrics_log]),
                'density_norm_avg': np.mean([m['density_normalized'] for m in metrics_log]),
                'compression_avg': np.mean([m['compression'] for m in metrics_log]),
                'compression_norm_avg': np.mean([m['compression_normalized'] for m in metrics_log]),
                'variance_avg': np.mean([m['velocity_variance'] for m in metrics_log]),
                'variance_norm_avg': np.mean([m['velocity_variance_normalized'] for m in metrics_log]),
                'entropy_avg': np.mean([m['direction_entropy'] for m in metrics_log]),
                'entropy_norm_avg': np.mean([m['direction_entropy_normalized'] for m in metrics_log]),
                'heatmap_comp_avg': np.mean([m['heatmap_compression'] for m in metrics_log]),
                'heatmap_comp_norm_avg': np.mean([m['heatmap_compression_normalized'] for m in metrics_log]),
                'speed_avg': np.mean([m['avg_speed'] for m in metrics_log]),
                'speed_max': np.mean([m['max_speed'] for m in metrics_log]),
                'high_speed_ratio_avg': np.mean([m['high_speed_ratio'] for m in metrics_log]),
            }
            
            result['preview_risk'] = (
                result['density_norm_avg'] * 0.20 +
                result['compression_norm_avg'] * 0.25 +
                result['variance_norm_avg'] * 0.20 +
                result['entropy_norm_avg'] * 0.15 +
                result['heatmap_comp_norm_avg'] * 0.20
            ) * 100
            
            print(f"\n   📊 Summary:")
            print(f"      People: {result['count_avg']:.1f} (±{result['count_std']:.1f}), Max: {result['count_max']}")
            print(f"      Density: {result['density_avg']:.2f} people/100k px")
            print(f"      Compression: {result['compression_avg']:.1f} px")
            print(f"      Speed: {result['speed_avg']:.2f} px/frame")
            print(f"      Preview Risk: {result['preview_risk']:.1f}/100")
            
            results.append(result)
    
    # ========================================
    # FINAL COMPARISON
    # ========================================
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE COMPARISON - ALL VIDEOS")
    print("=" * 80)
    
    if not results:
        print("❌ No results to compare")
        return
    
    # Sort by risk score
    results_sorted = sorted(results, key=lambda x: x['preview_risk'])
    
    print("\n📊 SORTED BY RISK SCORE:")
    print("-" * 80)
    print(f"{'Video':<40} {'People':<12} {'Risk':<10} {'Density':<10}")
    print("-" * 80)
    
    for r in results_sorted:
        print(f"{r['name']:<40} {r['count_avg']:>6.1f} ±{r['count_std']:>4.1f} "
              f"{r['preview_risk']:>6.1f}/100  {r['density_avg']:>6.2f}")
    
    # Detailed metrics table
    print("\n" + "=" * 80)
    print("DETAILED METRICS (Normalized 0-1 scale)")
    print("=" * 80)
    print(f"{'Video':<40} {'Dens':<7} {'Comp':<7} {'Var':<7} {'Entr':<7} {'Heat':<7}")
    print("-" * 80)
    
    for r in results_sorted:
        print(f"{r['name']:<40} "
              f"{r['density_norm_avg']:>6.3f}  "
              f"{r['compression_norm_avg']:>6.3f}  "
              f"{r['variance_norm_avg']:>6.3f}  "
              f"{r['entropy_norm_avg']:>6.3f}  "
              f"{r['heatmap_comp_norm_avg']:>6.3f}")
    
    # Risk categories
    print("\n" + "=" * 80)
    print("RISK CLASSIFICATION")
    print("=" * 80)
    
    low_risk = [r for r in results if r['preview_risk'] < 40]
    medium_risk = [r for r in results if 40 <= r['preview_risk'] < 70]
    high_risk = [r for r in results if r['preview_risk'] >= 70]
    
    print(f"\n🟢 LOW RISK (< 40): {len(low_risk)} videos")
    for r in low_risk:
        print(f"   • {r['name']}: {r['preview_risk']:.1f}/100")
    
    print(f"\n🟡 MEDIUM RISK (40-70): {len(medium_risk)} videos")
    for r in medium_risk:
        print(f"   • {r['name']}: {r['preview_risk']:.1f}/100")
    
    print(f"\n🔴 HIGH RISK (≥ 70): {len(high_risk)} videos")
    for r in high_risk:
        print(f"   • {r['name']}: {r['preview_risk']:.1f}/100")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS FOR PHASE 2")
    print("=" * 80)
    
    if results:
        min_risk = min(r['preview_risk'] for r in results)
        max_risk = max(r['preview_risk'] for r in results)
        
        print(f"\n📊 Observed Risk Range: {min_risk:.1f} - {max_risk:.1f}")
        print(f"\n💡 Suggested Thresholds:")
        print(f"   • NORMAL:   0 - 40   (Green)")
        print(f"   • WARNING: 40 - 70   (Yellow)")
        print(f"   • CRITICAL: 70 - 100 (Red)")
        
        print(f"\n🎯 Metric Contributions:")
        avg_contributions = {
            'Density': np.mean([r['density_norm_avg'] for r in results]) * 0.20 * 100,
            'Compression': np.mean([r['compression_norm_avg'] for r in results]) * 0.25 * 100,
            'Variance': np.mean([r['variance_norm_avg'] for r in results]) * 0.20 * 100,
            'Entropy': np.mean([r['entropy_norm_avg'] for r in results]) * 0.15 * 100,
            'Heatmap': np.mean([r['heatmap_comp_norm_avg'] for r in results]) * 0.20 * 100,
        }
        
        for metric, contribution in sorted(avg_contributions.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {metric:<15} contributes {contribution:>5.1f} points on average")
    
    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nReady to build Risk Engine with proper thresholds!")


if __name__ == "__main__":
    main()
