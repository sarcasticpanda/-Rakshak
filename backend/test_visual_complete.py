"""
Complete Visual Test with Crowd Metrics + Risk Scoring
Shows: Detection boxes, Track IDs, Trajectories, Speed indicators, Comprehensive dashboard, Risk score
"""
import sys
sys.path.insert(0, str(__file__).replace('test_visual_complete.py', ''))

import cv2
import numpy as np
from pathlib import Path
from collections import deque
from app.core.robust_pipeline import RobustDetectionPipeline
from app.core.tracker import ByteTracker
from app.core.crowd_metrics import CrowdMetrics


def get_speed_color(speed, max_speed=30.0):
    """Get color based on speed (green->yellow->red)"""
    ratio = min(speed / max_speed, 1.0)
    if ratio < 0.3:
        return (0, 255, 0)  # Green - slow
    elif ratio < 0.6:
        return (0, 255, 255)  # Yellow - medium
    else:
        return (0, 0, 255)  # Red - fast


def visualize_complete(frame, detections, tracks, metrics, metadata, pipeline, frame_num):
    """
    Complete visualization with all data layers
    
    Layers:
    1. Heatmap overlay (base spatial awareness)
    2. Detection boxes (YOLOv8 results)
    3. Track IDs + trajectories (ByteTrack)
    4. Speed indicators (color-coded per person)
    5. Comprehensive dashboard (left side)
    6. Risk score display (top right, large)
    7. Stampede warning banner (if critical)
    """
    annotated = frame.copy()
    h, w = frame.shape[:2]
    
    # ========================================
    # LAYER 1: Heatmap overlay
    # ========================================
    if pipeline and pipeline.heatmap and pipeline.heatmap.is_bootstrapped():
        annotated = pipeline.heatmap.get_visualization(annotated, alpha=0.25)
    
    # ========================================
    # LAYER 2: Detection boxes (faint)
    # ========================================
    for det in detections:
        x1, y1, x2, y2 = map(int, det['bbox'])
        conf = det['confidence']
        is_synthetic = det.get('synthetic', False)
        
        if is_synthetic:
            color = (255, 0, 255)  # Magenta
            thickness = 2
        else:
            color = (100, 100, 100)  # Gray - faint
            thickness = 1
        
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
    
    # ========================================
    # LAYER 3 & 4: Tracks + Speed indicators
    # ========================================
    if tracks and metrics and 'per_person' in metrics:
        per_person_map = {p['track_id']: p for p in metrics['per_person']}
        
        for track_dict in tracks:
            # Track bounding box
            x1, y1, x2, y2 = map(int, track_dict['bbox'])
            track_id = track_dict['track_id']
            
            # Get speed info
            person_data = per_person_map.get(track_id, None)
            if person_data:
                speed = person_data['speed']
                direction = person_data['direction']
            else:
                speed = 0.0
                direction = 0.0
            
            # Color by speed
            color = get_speed_color(speed)
            
            # Draw track box (thicker than detection)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
            
            # Track ID
            cv2.putText(annotated, f"ID:{track_id}", (x1, y1-25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Speed
            cv2.putText(annotated, f"{speed:.1f}px/f", (x1, y1-8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Trajectory trail (last 30 frames)
            if 'trajectory' in track_dict and len(track_dict['trajectory']) > 1:
                points = np.array(track_dict['trajectory'][-30:], dtype=np.int32)
                for i in range(1, len(points)):
                    cv2.line(annotated, tuple(points[i-1]), tuple(points[i]), color, 2)
            
            # Direction arrow (if moving)
            if speed > 1.0:
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                arrow_len = 40
                dx = int(arrow_len * np.cos(direction))
                dy = int(arrow_len * np.sin(direction))
                cv2.arrowedLine(annotated, (int(cx), int(cy)), 
                               (int(cx+dx), int(cy+dy)), color, 2, tipLength=0.3)
    
    # ========================================
    # LAYER 5: Comprehensive Dashboard (left)
    # ========================================
    dashboard_w = 480
    dashboard_h = 380
    overlay = annotated.copy()
    cv2.rectangle(overlay, (10, 10), (10+dashboard_w, 10+dashboard_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, annotated)
    cv2.rectangle(annotated, (10, 10), (10+dashboard_w, 10+dashboard_h), (255, 255, 255), 2)
    
    y = 40
    
    # Title
    cv2.putText(annotated, "STAMPEDE DETECTION SYSTEM", (20, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    y += 35
    
    # Mode
    mode = metadata['mode']
    mode_colors = {'sparse': (0, 255, 0), 'medium': (0, 255, 255), 'dense': (0, 0, 255)}
    mode_color = mode_colors.get(mode, (255, 255, 255))
    cv2.putText(annotated, f"Mode: {mode.upper()}", (20, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2)
    y += 30
    
    # Counts
    cv2.putText(annotated, f"People Count: {metrics['count']}", (20, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    y += 30
    
    # Detection pipeline breakdown
    cv2.putText(annotated, f"  Raw Detections: {metadata['raw_count']}", (20, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
    y += 22
    cv2.putText(annotated, f"  Heatmap Validated: {metadata.get('heatmap_validated_count', 0)}", (20, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
    y += 22
    cv2.putText(annotated, f"  Temporal Validated: {metadata['temporal_validated_count']}", (20, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
    y += 30
    
    # Crowd metrics
    cv2.putText(annotated, "CROWD METRICS:", (20, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 0), 2)
    y += 28
    
    cv2.putText(annotated, f"Density: {metrics['density']:.2f} per 100k px", (30, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    cv2.putText(annotated, f"({metrics['density_normalized']:.2f})", (350, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    y += 22
    
    cv2.putText(annotated, f"Compression: {metrics['compression']:.1f} px", (30, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    cv2.putText(annotated, f"({metrics['compression_normalized']:.2f})", (350, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    y += 22
    
    cv2.putText(annotated, f"Velocity Variance: {metrics['velocity_variance']:.1f}", (30, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    cv2.putText(annotated, f"({metrics['velocity_variance_normalized']:.2f})", (350, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    y += 22
    
    # NEW: Flow Collision
    flow_col = metrics.get('flow_collision_normalized', 0.0)
    flow_color = (0, 0, 255) if flow_col > 0.5 else (200, 200, 200)
    cv2.putText(annotated, f"Flow Collision: {metrics.get('flow_collision', 0):.2f}", (30, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, flow_color, 1)
    cv2.putText(annotated, f"({flow_col:.2f})", (350, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    y += 22
    
    # NEW: Panic Wave
    panic = metrics.get('panic_wave_normalized', 0.0)
    panic_color = (0, 0, 255) if panic > 0.5 else (200, 200, 200)
    cv2.putText(annotated, f"Panic Wave: {metrics.get('panic_wave', 0):.2f}", (30, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, panic_color, 1)
    cv2.putText(annotated, f"({panic:.2f})", (350, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    y += 25
    
    # Speed stats
    cv2.putText(annotated, f"Avg Speed: {metrics['avg_speed']:.1f} | Max: {metrics['max_speed']:.1f} px/f", (30, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
    y += 20
    cv2.putText(annotated, f"High Speed: {metrics['high_speed_count']} ({metrics['high_speed_ratio']*100:.0f}%)", (30, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
    
    # Frame number
    cv2.putText(annotated, f"Frame {frame_num}", (20, dashboard_h-10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    
    # ========================================
    # LAYER 6: Risk Score (top right, LARGE)
    # ========================================
    risk_score = metrics.get('risk_score', 0.0)
    
    # Risk level
    if risk_score < 40:
        risk_level = "NORMAL"
        risk_color = (0, 255, 0)  # Green
    elif risk_score < 70:
        risk_level = "WARNING"
        risk_color = (0, 200, 255)  # Orange
    else:
        risk_level = "CRITICAL"
        risk_color = (0, 0, 255)  # Red
    
    # Risk box - made taller for prediction
    risk_box_x = w - 280
    risk_box_w = 270
    risk_box_h = 190
    overlay = annotated.copy()
    cv2.rectangle(overlay, (risk_box_x, 10), (risk_box_x+risk_box_w, 10+risk_box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.8, annotated, 0.2, 0, annotated)
    cv2.rectangle(annotated, (risk_box_x, 10), (risk_box_x+risk_box_w, 10+risk_box_h), risk_color, 3)
    
    # Risk score - LARGE
    cv2.putText(annotated, f"{risk_score:.1f}", (risk_box_x+40, 80),
               cv2.FONT_HERSHEY_SIMPLEX, 2.0, risk_color, 4)
    cv2.putText(annotated, "/100", (risk_box_x+180, 80),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    
    # Risk level
    cv2.putText(annotated, risk_level, (risk_box_x+50, 120),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, risk_color, 2)
    
    # ========================================
    # LAYER 6B: Risk Trend Prediction
    # ========================================
    prediction = metrics.get('prediction', {})
    pred_text = prediction.get('prediction', 'ANALYZING...')
    trend = prediction.get('trend', 0)
    
    # Prediction color based on severity
    if pred_text == "STAMPEDE_IMMINENT":
        pred_color = (0, 0, 255)  # Red - DANGER
    elif pred_text == "RISK_INCREASING":
        pred_color = (0, 165, 255)  # Orange - Warning
    elif pred_text == "STABLE_HIGH":
        pred_color = (0, 200, 255)  # Yellow-Orange
    elif pred_text == "RISK_DECREASING":
        pred_color = (0, 255, 0)  # Green
    else:
        pred_color = (200, 200, 200)  # Gray
    
    # Trend arrow
    if trend > 0.5:
        arrow = "↑↑"
    elif trend > 0:
        arrow = "↑"
    elif trend < -0.5:
        arrow = "↓↓"
    elif trend < 0:
        arrow = "↓"
    else:
        arrow = "→"
    
    cv2.putText(annotated, f"TREND: {arrow}", (risk_box_x+20, 155),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, pred_color, 2)
    cv2.putText(annotated, pred_text.replace("_", " "), (risk_box_x+20, 185),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, pred_color, 1)
    
    # ========================================
    # LAYER 7: Stampede Warning Banner
    # ========================================
    if risk_score >= 70 or pred_text == "STAMPEDE_IMMINENT":
        # Flashing effect (based on frame number)
        if frame_num % 20 < 10:
            banner_h = 80
            overlay = annotated.copy()
            cv2.rectangle(overlay, (0, h//2 - banner_h//2), (w, h//2 + banner_h//2), (0, 0, 255), -1)
            cv2.addWeighted(overlay, 0.6, annotated, 0.4, 0, annotated)
            
            cv2.putText(annotated, "⚠ STAMPEDE RISK DETECTED ⚠", (w//2-400, h//2+10),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 4)
    
    return annotated


def test_video(video_path, name):
    """Test video with complete visualization"""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"{'='*70}")
    
    cap = cv2.VideoCapture(str(video_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"   Resolution: {width}x{height}, FPS: {fps}, Total Frames: {total}")
    
    # Output directory
    output_dir = Path(__file__).parent / "output" / "visual_complete"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{name}_annotated.mp4"
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Initialize components
    pipeline = RobustDetectionPipeline(enable_heatmap=True)
    tracker = ByteTracker()
    crowd_metrics = CrowdMetrics()
    
    frame_count = 0
    risk_scores = []
    
    max_frames = min(total, 150)  # Process first 150 frames
    
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Detection pipeline
        detections, metadata = pipeline.detect(frame)
        
        # Tracking (PHASE 1: Pass heatmap for confidence boosting)
        tracks = tracker.update(detections, (height, width), pipeline.heatmap)
        
        # Crowd metrics
        metrics = crowd_metrics.calculate(tracker.tracks, (height, width), pipeline.heatmap)
        
        # Risk score
        risk_score = crowd_metrics.calculate_risk_score(metrics)
        metrics['risk_score'] = risk_score
        risk_scores.append(risk_score)
        
        # Risk trend prediction (NEW!)
        prediction = crowd_metrics.predict_risk_trend()
        metrics['prediction'] = prediction
        
        # Complete visualization
        annotated = visualize_complete(frame, detections, tracks, metrics, metadata, pipeline, frame_count)
        
        out.write(annotated)
        
        if frame_count % 25 == 0:
            print(f"   Frame {frame_count}/{max_frames}: "
                  f"People={metrics['count']}, Risk={risk_score:.1f}, "
                  f"Variance={metrics['velocity_variance']:.3f}")
    
    cap.release()
    out.release()
    
    # Statistics
    print(f"\n   📊 Statistics:")
    print(f"   ├─ Frames processed: {frame_count}")
    print(f"   ├─ Average risk score: {np.mean(risk_scores):.1f}/100")
    print(f"   ├─ Max risk score: {np.max(risk_scores):.1f}/100")
    print(f"   ├─ Min risk score: {np.min(risk_scores):.1f}/100")
    
    # Risk distribution
    normal_frames = sum(1 for r in risk_scores if r < 40)
    warning_frames = sum(1 for r in risk_scores if 40 <= r < 70)
    critical_frames = sum(1 for r in risk_scores if r >= 70)
    
    print(f"   ├─ Risk distribution:")
    print(f"   │  ├─ NORMAL (<40):   {normal_frames} frames ({normal_frames/frame_count*100:.0f}%)")
    print(f"   │  ├─ WARNING (40-70): {warning_frames} frames ({warning_frames/frame_count*100:.0f}%)")
    print(f"   │  └─ CRITICAL (>70):  {critical_frames} frames ({critical_frames/frame_count*100:.0f}%)")
    print(f"   └─ Output: {output_path.name}")
    
    return str(output_path)


def main():
    print("=" * 70)
    print("COMPLETE VISUAL TEST - DETECTION + TRACKING + METRICS + RISK")
    print("=" * 70)
    
    videos_to_test = [
        (r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4", "test2_sparse"),
        (r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test3.mp4", "test3_medium"),
        (r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\stampede.mp4", "stampede_dense"),
        (r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test_d1.mp4", "test_d1"),
        (r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\MOT17\MOT17\train\MOT17-02-FRCNN\img1", "MOT17-02"),
        (r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\MOT17\MOT17\train\MOT17-04-FRCNN\img1", "MOT17-04"),
    ]
    
    output_videos = []
    
    for video_path, name in videos_to_test:
        path = Path(video_path)
        
        # Handle MOT17 image sequences vs video files
        if path.is_dir():
            # MOT17 - skip for now (would need image sequence handler)
            print(f"\n⚠️  Skipping {name} (image sequence - not implemented yet)")
            continue
        elif not path.exists():
            print(f"\n⚠️  Skipping {name} (file not found)")
            continue
        
        output_video = test_video(path, name)
        output_videos.append(output_video)
    
    print("\n" + "=" * 70)
    print("✅ VISUALIZATION COMPLETE")
    print("=" * 70)
    print("\nGenerated annotated videos with:")
    print("  ✓ Detection boxes (gray)")
    print("  ✓ Track IDs + trajectory trails (color by speed)")
    print("  ✓ Speed indicators (green/yellow/red)")
    print("  ✓ Direction arrows")
    print("  ✓ Comprehensive dashboard (all metrics)")
    print("  ✓ Large risk score display (top right)")
    print("  ✓ Stampede warning banner (if critical)")
    print("  ✓ Heatmap overlay (background)")
    print("=" * 70)
    
    return output_videos


if __name__ == "__main__":
    videos = main()
