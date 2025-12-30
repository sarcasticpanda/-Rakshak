"""
Test Phase 4: Motion Features
Visualize speed, direction, and panic detection
"""
import sys
sys.path.insert(0, str(__file__).replace('test_motion.py', ''))

import cv2
import numpy as np
from pathlib import Path
from app.core.detector import PersonDetector
from app.core.tracker import ByteTracker
from app.core.motion import MotionAnalyzer


def draw_motion_info(frame, tracks, motion_data, analyzer):
    """Draw motion visualization on frame"""
    
    # Draw each track with motion info
    for track in tracks:
        tid = track['track_id']
        bbox = track['bbox']
        x1, y1, x2, y2 = map(int, bbox)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        
        # Get individual motion
        motion = analyzer.get_track_motion(tid)
        
        if motion:
            speed = motion['current_speed']
            direction = motion['current_direction']
            
            # Color based on speed (green=slow, yellow=medium, red=fast)
            if speed < 5:
                color = (0, 255, 0)  # Green - slow
            elif speed < 15:
                color = (0, 255, 255)  # Yellow - medium
            else:
                color = (0, 0, 255)  # Red - fast
            
            # Draw box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw direction arrow
            if speed > 2:  # Only show direction if moving
                arrow_len = min(30, int(speed * 3))
                end_x = int(cx + arrow_len * np.cos(direction))
                end_y = int(cy + arrow_len * np.sin(direction))
                cv2.arrowedLine(frame, (cx, cy), (end_x, end_y), color, 2, tipLength=0.3)
            
            # Speed label
            cv2.putText(frame, f"{speed:.1f}", (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        else:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (128, 128, 128), 1)
    
    # Draw motion dashboard
    draw_dashboard(frame, motion_data, analyzer)
    
    return frame


def draw_dashboard(frame, motion_data, analyzer):
    """Draw motion metrics dashboard"""
    h, w = frame.shape[:2]
    
    # Dashboard background
    cv2.rectangle(frame, (10, 10), (350, 200), (0, 0, 0), -1)
    cv2.rectangle(frame, (10, 10), (350, 200), (255, 255, 255), 2)
    
    # Title
    cv2.putText(frame, "MOTION ANALYSIS", (20, 35),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    # Metrics
    y = 60
    metrics = [
        (f"Avg Speed: {motion_data['avg_speed']:.1f} px/f", (255, 255, 255)),
        (f"Max Speed: {motion_data['max_speed']:.1f} px/f", (255, 255, 255)),
        (f"Fast Movers: {motion_data['fast_movers']} ({motion_data['fast_mover_ratio']*100:.0f}%)", 
         (0, 255, 255) if motion_data['fast_mover_ratio'] > 0.3 else (255, 255, 255)),
        (f"Sudden Accels: {motion_data['sudden_accel_count']}", 
         (0, 165, 255) if motion_data['sudden_accel_count'] > 3 else (255, 255, 255)),
    ]
    
    for text, color in metrics:
        cv2.putText(frame, text, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        y += 22
    
    # Direction indicator
    if motion_data['dominant_direction'] is not None:
        arrow = analyzer.direction_to_arrow(motion_data['dominant_direction'])
        agreement = motion_data['direction_agreement'] * 100
        cv2.putText(frame, f"Dominant Dir: {arrow} ({agreement:.0f}% agree)", (20, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y += 22
    
    # Panic score bar
    y += 5
    panic = motion_data['panic_score']
    cv2.putText(frame, f"PANIC SCORE:", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Score bar
    bar_x = 140
    bar_width = 180
    bar_height = 15
    cv2.rectangle(frame, (bar_x, y-12), (bar_x + bar_width, y+3), (50, 50, 50), -1)
    
    # Fill based on score
    fill_width = int(bar_width * panic / 100)
    if panic < 30:
        bar_color = (0, 255, 0)
    elif panic < 50:
        bar_color = (0, 255, 255)
    elif panic < 70:
        bar_color = (0, 165, 255)
    else:
        bar_color = (0, 0, 255)
    
    cv2.rectangle(frame, (bar_x, y-12), (bar_x + fill_width, y+3), bar_color, -1)
    cv2.putText(frame, f"{panic:.0f}", (bar_x + bar_width + 5, y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, bar_color, 2)
    
    # Alerts at bottom
    if motion_data['alerts']:
        for i, alert in enumerate(motion_data['alerts'][:3]):
            cv2.putText(frame, alert, (10, h - 30 - i*25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)


def main():
    print("=" * 70)
    print("PHASE 4: MOTION FEATURE ANALYSIS")
    print("Detecting speed, direction, acceleration, panic")
    print("=" * 70)
    
    # Test on REAL STAMPEDE video
    video_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\stampede.mp4")
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    output_dir = Path(__file__).parent / "output" / "motion_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Output: {output_dir}")
    
    # Initialize components
    print("\n🔧 Loading components...")
    detector = PersonDetector()
    tracker = ByteTracker(track_thresh=0.3, track_buffer=15, match_thresh=0.4, min_hits=3, max_age=10)
    motion_analyzer = MotionAnalyzer(
        speed_threshold=15.0,      # 15 px/frame = fast
        accel_threshold=5.0,       # Sudden acceleration
        direction_change_threshold=np.pi/4  # 45 degrees
    )
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"\n📹 Video: {video_path.name}")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps}, Frames: {total_frames}")
    
    # Output video
    output_path = output_dir / "stampede_real_motion.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # Process
    frame_count = 0
    max_panic = 0
    alert_frames = 0
    
    print(f"\n🎬 Processing...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Detect -> Track -> Analyze Motion
        detections = detector.detect(frame)
        tracks = tracker.update(detections, frame_size=(width, height))
        motion_data = motion_analyzer.update(tracks)
        
        # Track stats
        if motion_data['panic_score'] > max_panic:
            max_panic = motion_data['panic_score']
        if motion_data['alerts']:
            alert_frames += 1
        
        # Visualize
        annotated = draw_motion_info(frame.copy(), tracks, motion_data, motion_analyzer)
        
        # Frame counter
        cv2.putText(annotated, f"Frame {frame_count}/{total_frames}", (width-180, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        out.write(annotated)
        
        if frame_count % 50 == 0:
            print(f"   Frame {frame_count}: {len(tracks)} tracks, "
                  f"Panic: {motion_data['panic_score']:.0f}, "
                  f"Speed: {motion_data['avg_speed']:.1f}")
    
    cap.release()
    out.release()
    
    print(f"\n{'='*60}")
    print(f"📊 MOTION ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"   Frames processed: {frame_count}")
    print(f"   Max panic score: {max_panic:.1f}")
    print(f"   Frames with alerts: {alert_frames}")
    print(f"\n   📁 Output: {output_path}")
    print(f"{'='*60}")
    
    # Open video
    print("\n🎬 Opening output video...")


if __name__ == "__main__":
    main()
