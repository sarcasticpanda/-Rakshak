"""
Test optimized detection on MOT17 dataset sequences
Compare detection performance across different MOT17 scenarios
"""

import sys
sys.path.insert(0, str(__file__).replace('test_mot17_optimized.py', ''))

import cv2
from pathlib import Path
from app.core.detector import PersonDetector
from app.core.video_reader import FrameReader
import time
import numpy as np

def test_mot17_sequence(sequence_path, detector, max_frames=50):
    """Test detection on a MOT17 sequence"""
    sequence_name = sequence_path.name
    print(f"\n{'='*80}")
    print(f"Testing: {sequence_name}")
    print(f"{'='*80}")
    
    # Initialize frame reader for image sequence
    reader = FrameReader(str(sequence_path / "img1"), source_type="images")
    
    print(f"   Total frames: {reader.frame_count}")
    print(f"   Processing: {min(max_frames, reader.frame_count)} frames")
    
    # Output directory
    output_dir = Path(__file__).parent / "output" / "mot17_optimized" / sequence_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get first frame to determine size
    ret, first_frame = reader.read_frame()
    if not ret:
        print("   ❌ Failed to read first frame")
        return None
    
    height, width = first_frame.shape[:2]
    print(f"   Resolution: {width}x{height} (ORIGINAL - no resize)")
    
    # Reset reader
    reader = FrameReader(str(sequence_path / "img1"), source_type="images")
    
    # Prepare output video
    output_path = output_dir / f"{sequence_name}_optimized.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, 10, (width, height))
    
    # Process frames
    total_detections = 0
    frame_count = 0
    inference_times = []
    detection_counts = []
    
    for i in range(max_frames):
        ret, frame = reader.read_frame()
        if not ret:
            break
        
        # Detect (no manual resizing!)
        start = time.time()
        detections = detector.detect(frame)
        inference_time = (time.time() - start) * 1000
        inference_times.append(inference_time)
        
        num_detections = len(detections)
        total_detections += num_detections
        detection_counts.append(num_detections)
        
        # Annotate
        annotated = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            conf = det['confidence']
            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            # Draw confidence
            cv2.putText(annotated, f"{conf:.2f}", (int(x1), int(y1)-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # Overlay
        cv2.putText(annotated, sequence_name, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(annotated, f"People: {num_detections}", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.putText(annotated, f"Frame: {i+1}/{max_frames}", (10, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(annotated, f"{width}x{height} ORIGINAL", (10, 140),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        out.write(annotated)
        frame_count += 1
        
        if (i + 1) % 10 == 0:
            print(f"   Frame {i+1}: {num_detections} people")
    
    out.release()
    
    # Statistics
    avg_detections = total_detections / frame_count if frame_count > 0 else 0
    max_detections = max(detection_counts) if detection_counts else 0
    min_detections = min(detection_counts) if detection_counts else 0
    avg_inference = np.mean(inference_times) if inference_times else 0
    
    print(f"\n   Results:")
    print(f"   ├─ Avg detections: {avg_detections:.1f} people/frame")
    print(f"   ├─ Max detections: {max_detections} people")
    print(f"   ├─ Min detections: {min_detections} people")
    print(f"   ├─ Avg inference:  {avg_inference:.1f}ms")
    print(f"   └─ Output: {output_path.name}")
    
    return {
        'sequence': sequence_name,
        'avg': avg_detections,
        'max': max_detections,
        'min': min_detections,
        'inference_ms': avg_inference,
        'resolution': f"{width}x{height}"
    }


def main():
    print("=" * 80)
    print("MOT17 DATASET TEST - OPTIMIZED DETECTION (NO RESIZE)")
    print("=" * 80)
    
    # MOT17 path
    mot17_base = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\MOT17\MOT17\train")
    
    if not mot17_base.exists():
        print(f"❌ MOT17 path not found: {mot17_base}")
        return
    
    # Find all sequences
    sequences = sorted([d for d in mot17_base.iterdir() if d.is_dir() and d.name.startswith("MOT17-")])
    
    if not sequences:
        print("❌ No MOT17 sequences found")
        return
    
    print(f"\n✅ Found {len(sequences)} MOT17 sequences:")
    for seq in sequences:
        print(f"   • {seq.name}")
    
    # Initialize detector
    print("\n🔧 Initializing detector...")
    detector = PersonDetector()
    print(f"   ✅ Model: yolov8m.pt")
    print(f"   ✅ Settings: conf={detector.conf_threshold}, iou={detector.iou_threshold}")
    print(f"   ✅ Max detections: 1500")
    print(f"   ✅ NO manual resizing - YOLO handles it internally")
    
    # Test each sequence
    results = []
    
    for sequence_path in sequences:
        result = test_mot17_sequence(sequence_path, detector, max_frames=50)
        if result:
            results.append(result)
    
    # Summary table
    print("\n" + "=" * 80)
    print("📊 SUMMARY - ALL MOT17 SEQUENCES")
    print("=" * 80)
    print(f"\n{'Sequence':<20} {'Avg Det':<12} {'Max Det':<10} {'Inference':<12} {'Resolution':<15}")
    print("-" * 79)
    
    for result in results:
        print(f"{result['sequence']:<20} {result['avg']:<12.1f} {result['max']:<10} "
              f"{result['inference_ms']:<12.1f} {result['resolution']:<15}")
    
    # Overall statistics
    print("\n" + "=" * 80)
    print("📈 OVERALL STATISTICS")
    print("=" * 80)
    
    total_avg = sum(r['avg'] for r in results) / len(results) if results else 0
    overall_max = max(r['max'] for r in results) if results else 0
    avg_inference = sum(r['inference_ms'] for r in results) / len(results) if results else 0
    
    print(f"\n   Average across all sequences: {total_avg:.1f} people/frame")
    print(f"   Maximum detection (any frame): {overall_max} people")
    print(f"   Average inference time: {avg_inference:.1f}ms")
    
    print(f"\n   All outputs saved to: backend/output/mot17_optimized/")
    
    print("\n" + "=" * 80)
    print("✅ MOT17 Testing Complete!")
    print("=" * 80)
    print("\n   Key improvements:")
    print("   • NO manual frame resizing")
    print("   • Original resolutions preserved")
    print("   • YOLO handles resizing internally with imgsz=1920")
    print("   • Small people NOT destroyed by aggressive resize")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
