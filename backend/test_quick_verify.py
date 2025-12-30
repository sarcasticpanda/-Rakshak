"""Quick verification test - MOT17 + check_vids"""
import cv2
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, '.')
from app.core.robust_pipeline import RobustDetectionPipeline
from app.core.tracker import ByteTracker
from app.core.crowd_metrics import CrowdMetrics

output_dir = Path('output/visual_complete')
output_dir.mkdir(parents=True, exist_ok=True)

def test_mot17():
    """Test MOT17-04 (dense pedestrian scene)"""
    print("="*60)
    print("Testing MOT17-04 (image sequence)")
    print("="*60)
    
    mot_path = Path('../MOT17/MOT17/train/MOT17-04-SDP/img1')
    imgs = sorted(mot_path.glob('*.jpg'))[:150]
    print(f'  Found {len(imgs)} frames')
    
    first = cv2.imread(str(imgs[0]))
    h, w = first.shape[:2]
    print(f'  Resolution: {w}x{h}')
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_dir / 'MOT17-04_verify.mp4'), fourcc, 25, (w, h))
    
    pipeline = RobustDetectionPipeline(enable_heatmap=True)
    tracker = ByteTracker()
    metrics = CrowdMetrics()
    
    for i, img_path in enumerate(imgs):
        frame = cv2.imread(str(img_path))
        dets, meta = pipeline.detect(frame)
        tracks = tracker.update(dets, (h, w), pipeline.heatmap)
        m = metrics.calculate(tracker.tracks, (h, w), pipeline.heatmap)
        risk = metrics.calculate_risk_score(m)
        
        # Draw ALL detections as gray
        for d in dets:
            x1,y1,x2,y2 = map(int, d['bbox'])
            cv2.rectangle(frame, (x1,y1), (x2,y2), (128,128,128), 1)
        
        # Draw tracks as green/yellow/red
        for t in tracks:
            x1,y1,x2,y2 = map(int, t['bbox'])
            # Color by speed
            speed = np.sqrt(t['velocity'][0]**2 + t['velocity'][1]**2)
            if speed < 5:
                color = (0, 255, 0)  # Green - slow
            elif speed < 15:
                color = (0, 255, 255)  # Yellow - medium
            else:
                color = (0, 0, 255)  # Red - fast
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            cv2.putText(frame, f"ID:{t['track_id']}", (x1,y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Risk display
        rcolor = (0,255,0) if risk < 40 else (0,165,255) if risk < 70 else (0,0,255)
        cv2.rectangle(frame, (w-200, 10), (w-10, 80), (0,0,0), -1)
        cv2.putText(frame, f'{risk:.0f}/100', (w-180, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, rcolor, 3)
        cv2.putText(frame, f'People: {m["count"]}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        cv2.putText(frame, f'Detections: {len(dets)}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
        
        out.write(frame)
        if (i+1) % 50 == 0:
            print(f'  Frame {i+1}: {m["count"]} tracked, {len(dets)} detected, Risk={risk:.1f}')
    
    out.release()
    print(f'  ✅ Output: MOT17-04_verify.mp4')
    return str(output_dir / 'MOT17-04_verify.mp4')


def test_check_vid():
    """Test test2_sparse from check_vids"""
    print("\n" + "="*60)
    print("Testing test2_sparse (check_vids)")
    print("="*60)
    
    vid_path = Path('../check_vids/test2.mp4')
    cap = cv2.VideoCapture(str(vid_path))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f'  Resolution: {w}x{h}, FPS: {fps}, Total: {total}')
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_dir / 'test2_verify.mp4'), fourcc, fps, (w, h))
    
    pipeline = RobustDetectionPipeline(enable_heatmap=True)
    tracker = ByteTracker()
    metrics = CrowdMetrics()
    
    frame_count = 0
    max_frames = 150
    
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        
        dets, meta = pipeline.detect(frame)
        tracks = tracker.update(dets, (h, w), pipeline.heatmap)
        m = metrics.calculate(tracker.tracks, (h, w), pipeline.heatmap)
        risk = metrics.calculate_risk_score(m)
        
        # Draw ALL detections as gray
        for d in dets:
            x1,y1,x2,y2 = map(int, d['bbox'])
            cv2.rectangle(frame, (x1,y1), (x2,y2), (128,128,128), 1)
        
        # Draw tracks
        for t in tracks:
            x1,y1,x2,y2 = map(int, t['bbox'])
            speed = np.sqrt(t['velocity'][0]**2 + t['velocity'][1]**2)
            if speed < 5:
                color = (0, 255, 0)
            elif speed < 15:
                color = (0, 255, 255)
            else:
                color = (0, 0, 255)
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            cv2.putText(frame, f"ID:{t['track_id']}", (x1,y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Risk display
        rcolor = (0,255,0) if risk < 40 else (0,165,255) if risk < 70 else (0,0,255)
        cv2.rectangle(frame, (w-200, 10), (w-10, 80), (0,0,0), -1)
        cv2.putText(frame, f'{risk:.0f}/100', (w-180, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, rcolor, 3)
        cv2.putText(frame, f'People: {m["count"]}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        cv2.putText(frame, f'Detections: {len(dets)}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
        
        out.write(frame)
        if frame_count % 50 == 0:
            print(f'  Frame {frame_count}: {m["count"]} tracked, {len(dets)} detected, Risk={risk:.1f}')
    
    cap.release()
    out.release()
    print(f'  ✅ Output: test2_verify.mp4')
    return str(output_dir / 'test2_verify.mp4')


if __name__ == '__main__':
    mot_vid = test_mot17()
    check_vid = test_check_vid()
    
    print("\n" + "="*60)
    print("✅ VERIFICATION COMPLETE")
    print("="*60)
    print(f"  1. {mot_vid}")
    print(f"  2. {check_vid}")
    print("\nOpening videos...")
    
    import subprocess
    subprocess.Popen(['cmd', '/c', 'start', '', mot_vid], shell=True)
    subprocess.Popen(['cmd', '/c', 'start', '', check_vid], shell=True)
