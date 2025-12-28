"""Quick test to verify false positive filtering"""
import sys
sys.path.insert(0, str(__file__).replace('test_fp_fix.py', ''))

import cv2
from pathlib import Path
from app.core.detector import PersonDetector
from app.core.tracker import ByteTracker

print('Testing sparse video with improved filters...')
detector = PersonDetector()
tracker = ByteTracker(track_thresh=0.3, track_buffer=30, match_thresh=0.5, min_hits=2, max_age=30)

cap = cv2.VideoCapture(r'C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids\test2.mp4')

output_dir = Path('output/bytetrack_fixed')
output_dir.mkdir(parents=True, exist_ok=True)

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(str(output_dir / 'sparse_fixed.mp4'), fourcc, 25, (1280, 720))

for i in range(100):
    ret, frame = cap.read()
    if not ret:
        break
    
    detections = detector.detect(frame)
    tracks = tracker.update(detections)
    
    colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255)]
    for t in tracks:
        x1, y1, x2, y2 = map(int, t['bbox'])
        color = colors[t['track_id'] % len(colors)]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{t['track_id']}", (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    cv2.putText(frame, f'Det: {len(detections)} Track: {len(tracks)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
    out.write(frame)
    
    if i % 20 == 0:
        print(f'Frame {i}: {len(detections)} det, {len(tracks)} tracked')

cap.release()
out.release()
print(f'\nSaved: output/bytetrack_fixed/sparse_fixed.mp4')
print('Check video - should have NO large building/sky boxes now')
