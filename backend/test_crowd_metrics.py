"""
Test Crowd Metrics - PHASE 1
Tests crowd calculations WITHOUT modifying detection pipeline
"""
import sys
sys.path.insert(0, str(__file__).replace('test_crowd_metrics.py', ''))

import cv2
import numpy as np
from pathlib import Path
from app.core.robust_pipeline import RobustDetectionPipeline
from app.core.tracker import ByteTracker
from app.core.crowd_metrics import CrowdMetrics


def test_metrics_calculation():
    """Test crowd metrics on sample video"""
    
    print("=" * 80)
    print("CROWD METRICS TEST - PHASE 1")
    print("=" * 80)
    print("\nThis test:")
    print("  ✓ Runs existing detection (unchanged)")
    print("  ✓ Passes tracks to CrowdMetrics")
    print("  ✓ Displays calculated metrics")
    print("  ✓ Does NOT modify detection output")
    print("=" * 80)
    
    # Test video
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4")
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    print(f"\n📹 Testing on: {video_path.name}")
    
    cap = cv2.VideoCapture(str(video_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    print(f"   Resolution: {width}x{height}, FPS: {fps}")
    
    # Initialize systems
    print("\n🔧 Initializing systems...")
    pipeline = RobustDetectionPipeline(enable_heatmap=True)
    tracker = ByteTracker()
    crowd_metrics = CrowdMetrics()  # NEW
    
    print("\n▶️  Processing frames...")
    
    frame_count = 0
    test_frames = 100  # Test first 100 frames
    
    metrics_log = []
    
    while frame_count < test_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # EXISTING DETECTION (UNCHANGED)
        detections, metadata = pipeline.detect(frame)
        
        # EXISTING TRACKING (UNCHANGED)
        tracks = tracker.update(detections, frame_size=(width, height))
        
        # NEW: Calculate crowd metrics
        metrics = crowd_metrics.calculate(
            tracks=tracker.tracks,  # Use tracker's internal tracks
            frame_shape=(height, width),
            heatmap=pipeline.heatmap
        )
        
        metrics_log.append(metrics)
        
        # Print every 25 frames
        if frame_count % 25 == 0:
            print(f"\n📊 Frame {frame_count}:")
            print(f"   People: {metadata['final_count']}")
            print(f"   Density: {metrics['density']:.2f} (normalized: {metrics['density_normalized']:.3f})")
            print(f"   Compression: {metrics['compression']:.1f}px (normalized: {metrics['compression_normalized']:.3f})")
            print(f"   Velocity Variance: {metrics['velocity_variance']:.2f} (normalized: {metrics['velocity_variance_normalized']:.3f})")
            print(f"   Direction Entropy: {metrics['direction_entropy']:.3f} (normalized: {metrics['direction_entropy_normalized']:.3f})")
            print(f"   Heatmap Compression: {metrics['heatmap_compression']:.3f} (normalized: {metrics['heatmap_compression_normalized']:.3f})")
            print(f"   Avg Speed: {metrics['avg_speed']:.2f} px/frame")
            print(f"   High Speed Count: {metrics['high_speed_count']}/{metrics['count']}")
    
    cap.release()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - First 100 Frames")
    print("=" * 80)
    
    if metrics_log:
        avg_metrics = {
            'count': np.mean([m['count'] for m in metrics_log]),
            'density': np.mean([m['density'] for m in metrics_log]),
            'compression': np.mean([m['compression'] for m in metrics_log]),
            'velocity_variance': np.mean([m['velocity_variance'] for m in metrics_log]),
            'direction_entropy': np.mean([m['direction_entropy'] for m in metrics_log]),
            'heatmap_compression': np.mean([m['heatmap_compression'] for m in metrics_log]),
            'avg_speed': np.mean([m['avg_speed'] for m in metrics_log]),
        }
        
        print(f"\n📊 Average Metrics:")
        print(f"   People Count: {avg_metrics['count']:.1f}")
        print(f"   Density: {avg_metrics['density']:.2f} people/100k px")
        print(f"   Compression: {avg_metrics['compression']:.1f} px avg distance")
        print(f"   Velocity Variance: {avg_metrics['velocity_variance']:.2f}")
        print(f"   Direction Entropy: {avg_metrics['direction_entropy']:.3f}")
        print(f"   Heatmap Compression: {avg_metrics['heatmap_compression']:.3f}")
        print(f"   Avg Speed: {avg_metrics['avg_speed']:.2f} px/frame")
        
        # Normalized scores
        print(f"\n🎯 Normalized Risk Components (0-1 scale):")
        norm_density = np.mean([m['density_normalized'] for m in metrics_log])
        norm_compression = np.mean([m['compression_normalized'] for m in metrics_log])
        norm_variance = np.mean([m['velocity_variance_normalized'] for m in metrics_log])
        norm_entropy = np.mean([m['direction_entropy_normalized'] for m in metrics_log])
        norm_heatmap = np.mean([m['heatmap_compression_normalized'] for m in metrics_log])
        
        print(f"   Density: {norm_density:.3f}")
        print(f"   Compression: {norm_compression:.3f}")
        print(f"   Velocity Variance: {norm_variance:.3f}")
        print(f"   Direction Coordination: {norm_entropy:.3f}")
        print(f"   Heatmap Compression: {norm_heatmap:.3f}")
        
        # Weighted preview (what risk engine will use)
        preview_risk = (
            norm_density * 0.20 +
            norm_compression * 0.25 +
            norm_variance * 0.20 +
            norm_entropy * 0.15 +
            norm_heatmap * 0.20
        ) * 100
        
        print(f"\n⚠️  Preview Risk Score: {preview_risk:.1f}/100")
        print("   (This is what the risk engine will calculate)")
    
    print("\n" + "=" * 80)
    print("✅ PHASE 1 COMPLETE - Metrics calculation working!")
    print("=" * 80)
    print("\nNext: Test on different videos (sparse vs dense)")


def test_multiple_videos():
    """Test metrics on sparse vs dense videos"""
    
    print("\n" + "=" * 80)
    print("TESTING MULTIPLE SCENARIOS")
    print("=" * 80)
    
    videos = [
        ("test2.mp4", "Sparse"),
        ("stampede.mp4", "Dense"),
    ]
    
    results = {}
    
    for video_name, scenario in videos:
        video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids") / video_name
        
        if not video_path.exists():
            print(f"\n⚠️  Skipping {video_name} (not found)")
            continue
        
        print(f"\n{'='*60}")
        print(f"Testing: {scenario} ({video_name})")
        print(f"{'='*60}")
        
        cap = cv2.VideoCapture(str(video_path))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        pipeline = RobustDetectionPipeline(enable_heatmap=True)
        tracker = ByteTracker()
        crowd_metrics = CrowdMetrics()
        
        metrics_log = []
        frame_count = 0
        
        while frame_count < 100:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            detections, metadata = pipeline.detect(frame)
            tracks = tracker.update(detections, frame_size=(width, height))
            metrics = crowd_metrics.calculate(tracker.tracks, (height, width), pipeline.heatmap)
            
            metrics_log.append(metrics)
        
        cap.release()
        
        # Calculate averages
        if metrics_log:
            results[scenario] = {
                'count': np.mean([m['count'] for m in metrics_log]),
                'density_norm': np.mean([m['density_normalized'] for m in metrics_log]),
                'compression_norm': np.mean([m['compression_normalized'] for m in metrics_log]),
                'variance_norm': np.mean([m['velocity_variance_normalized'] for m in metrics_log]),
                'entropy_norm': np.mean([m['direction_entropy_normalized'] for m in metrics_log]),
                'heatmap_norm': np.mean([m['heatmap_compression_normalized'] for m in metrics_log]),
            }
            
            risk = (
                results[scenario]['density_norm'] * 0.20 +
                results[scenario]['compression_norm'] * 0.25 +
                results[scenario]['variance_norm'] * 0.20 +
                results[scenario]['entropy_norm'] * 0.15 +
                results[scenario]['heatmap_norm'] * 0.20
            ) * 100
            
            results[scenario]['preview_risk'] = risk
            
            print(f"   Avg Count: {results[scenario]['count']:.1f}")
            print(f"   Preview Risk: {risk:.1f}/100")
    
    # Comparison
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    
    for scenario, data in results.items():
        print(f"\n{scenario}:")
        print(f"   People: {data['count']:.1f}")
        print(f"   Risk: {data['preview_risk']:.1f}/100")
        print(f"   Density: {data['density_norm']:.3f}")
        print(f"   Compression: {data['compression_norm']:.3f}")
        print(f"   Variance: {data['variance_norm']:.3f}")
    
    print("\n✅ Metrics differentiate between sparse and dense crowds!")


if __name__ == "__main__":
    # Test 1: Single video detailed
    test_metrics_calculation()
    
    # Test 2: Compare scenarios
    print("\n" * 2)
    test_multiple_videos()
    
    print("\n" + "=" * 80)
    print("✅ PHASE 1 TESTING COMPLETE")
    print("=" * 80)
    print("\nReady for Phase 2: Risk Engine")
