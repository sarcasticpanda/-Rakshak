"""
TEST ON MOT17 + INDIAN CROWDS
Find optimal settings that work for BOTH sparse and dense crowds
"""

import sys
sys.path.insert(0, str(__file__).replace('test_mot17_and_indian.py', ''))

import cv2
from pathlib import Path
from ultralytics import YOLO
import numpy as np

def test_video(model, video_path, video_name, conf, iou, frames=30):
    """Test a single video and return stats"""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    MIN_ASPECT, MAX_ASPECT = 0.3, 4.0
    detection_counts = []
    
    for i in range(frames):
        ret, frame = cap.read()
        if not ret:
            break
        
        results = model.predict(
            source=frame,
            conf=conf,
            iou=iou,
            classes=[0],
            max_det=1500,
            imgsz=1920,
            half=True,
            verbose=False
        )
        
        count = 0
        for result in results:
            boxes = result.boxes
            for j in range(len(boxes)):
                box = boxes.xyxy[j].cpu().numpy()
                x1, y1, x2, y2 = box
                w, h = x2 - x1, y2 - y1
                if w > 0 and h > 0:
                    aspect = h / w
                    if MIN_ASPECT <= aspect <= MAX_ASPECT:
                        count += 1
        detection_counts.append(count)
    
    cap.release()
    
    if not detection_counts:
        return None
    
    return {
        'name': video_name,
        'avg': np.mean(detection_counts),
        'max': max(detection_counts),
        'min': min(detection_counts),
        'res': f"{width}x{height}"
    }


def test_image_sequence(model, img_dir, seq_name, conf, iou, frames=30):
    """Test MOT17 image sequence"""
    img_files = sorted(img_dir.glob("*.jpg"))
    if not img_files:
        return None
    
    MIN_ASPECT, MAX_ASPECT = 0.3, 4.0
    detection_counts = []
    
    for img_path in img_files[:frames]:
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue
        
        results = model.predict(
            source=frame,
            conf=conf,
            iou=iou,
            classes=[0],
            max_det=1500,
            imgsz=1920,
            half=True,
            verbose=False
        )
        
        count = 0
        for result in results:
            boxes = result.boxes
            for j in range(len(boxes)):
                box = boxes.xyxy[j].cpu().numpy()
                x1, y1, x2, y2 = box
                w, h = x2 - x1, y2 - y1
                if w > 0 and h > 0:
                    aspect = h / w
                    if MIN_ASPECT <= aspect <= MAX_ASPECT:
                        count += 1
        detection_counts.append(count)
    
    if not detection_counts:
        return None
    
    # Get resolution from first image
    first_img = cv2.imread(str(img_files[0]))
    h, w = first_img.shape[:2] if first_img is not None else (0, 0)
    
    return {
        'name': seq_name,
        'avg': np.mean(detection_counts),
        'max': max(detection_counts),
        'min': min(detection_counts),
        'res': f"{w}x{h}"
    }


def main():
    print("=" * 80)
    print("MOT17 + INDIAN CROWD TEST")
    print("Finding optimal settings for BOTH sparse and dense crowds")
    print("=" * 80)
    
    # Load model
    print("\n🔧 Loading YOLOv8m...")
    model = YOLO("yolov8m.pt")
    model.to('cuda')
    
    # Paths
    mot17_path = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\MOT17\MOT17\train")
    indian_vids = Path(r"C:\Users\Lunar Panda\3-Main\stampede\-Rakshak\check_vids")
    
    # MOT17 sequences (mix of sparse and dense)
    mot17_seqs = [
        "MOT17-02-FRCNN",  # Sparse pedestrians
        "MOT17-04-FRCNN",  # Dense crowd
        "MOT17-05-FRCNN",  # Medium
        "MOT17-09-FRCNN",  # Sparse
        "MOT17-10-FRCNN",  # Medium moving
        "MOT17-11-FRCNN",  # Sparse
        "MOT17-13-FRCNN",  # Dense crowd
    ]
    
    # Indian videos
    indian_videos = [
        ("test_d1.mp4", "Indian_Dense"),
        ("test3.mp4", "Indian_Dense2"),
        ("test2.mp4", "Indian_Sparse"),
    ]
    
    # Test configurations
    configs = [
        (0.01, 0.45, "Current (aggressive)"),
        (0.02, 0.45, "Balanced"),
        (0.03, 0.45, "Conservative"),
    ]
    
    print(f"\n📊 Testing {len(configs)} configurations...")
    
    all_config_results = {}
    
    for conf, iou, config_name in configs:
        print(f"\n{'='*70}")
        print(f"CONFIG: {config_name} (conf={conf}, iou={iou})")
        print(f"{'='*70}")
        
        results = {'mot17': [], 'indian': []}
        
        # Test MOT17
        print("\n  📁 MOT17 Sequences:")
        for seq_name in mot17_seqs:
            seq_path = mot17_path / seq_name / "img1"
            if seq_path.exists():
                r = test_image_sequence(model, seq_path, seq_name, conf, iou, frames=20)
                if r:
                    results['mot17'].append(r)
                    density = "sparse" if r['avg'] < 20 else ("medium" if r['avg'] < 50 else "dense")
                    print(f"     {seq_name}: {r['avg']:.1f} avg ({density})")
        
        # Test Indian videos
        print("\n  📁 Indian Crowd Videos:")
        for vid_name, label in indian_videos:
            vid_path = indian_vids / vid_name
            if vid_path.exists():
                r = test_video(model, vid_path, label, conf, iou, frames=20)
                if r:
                    results['indian'].append(r)
                    print(f"     {label}: {r['avg']:.1f} avg, {r['max']} max")
        
        all_config_results[config_name] = results
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("📊 CONFIGURATION COMPARISON")
    print("=" * 80)
    
    print("\n" + "-" * 80)
    print(f"{'Config':<25} {'MOT17 Avg':<12} {'Indian Dense':<15} {'Indian Sparse':<15}")
    print("-" * 80)
    
    best_config = None
    best_score = 0
    
    for config_name, results in all_config_results.items():
        mot17_avg = np.mean([r['avg'] for r in results['mot17']]) if results['mot17'] else 0
        
        indian_dense = [r for r in results['indian'] if 'Dense' in r['name']]
        indian_sparse = [r for r in results['indian'] if 'Sparse' in r['name']]
        
        dense_avg = np.mean([r['avg'] for r in indian_dense]) if indian_dense else 0
        sparse_avg = np.mean([r['avg'] for r in indian_sparse]) if indian_sparse else 0
        
        print(f"{config_name:<25} {mot17_avg:<12.1f} {dense_avg:<15.1f} {sparse_avg:<15.1f}")
        
        # Score: Dense detection is priority, but not too high on sparse
        # Want dense >= 200 and sparse reasonable
        score = dense_avg - abs(sparse_avg - 50) * 0.5  # Penalize if sparse too high
        if dense_avg >= 200:
            score += 50
        
        if score > best_score:
            best_score = score
            best_config = config_name
    
    # Detailed analysis
    print("\n" + "=" * 80)
    print("📊 DETAILED ANALYSIS BY DENSITY")
    print("=" * 80)
    
    for config_name, results in all_config_results.items():
        print(f"\n  {config_name}:")
        
        # MOT17 breakdown
        sparse = [r for r in results['mot17'] if r['avg'] < 20]
        medium = [r for r in results['mot17'] if 20 <= r['avg'] < 50]
        dense = [r for r in results['mot17'] if r['avg'] >= 50]
        
        if sparse:
            print(f"     MOT17 Sparse ({len(sparse)} seqs): {np.mean([r['avg'] for r in sparse]):.1f} avg")
        if medium:
            print(f"     MOT17 Medium ({len(medium)} seqs): {np.mean([r['avg'] for r in medium]):.1f} avg")
        if dense:
            print(f"     MOT17 Dense ({len(dense)} seqs): {np.mean([r['avg'] for r in dense]):.1f} avg")
        
        # Indian
        for r in results['indian']:
            print(f"     {r['name']}: {r['avg']:.1f} avg, {r['max']} max")
    
    print("\n" + "=" * 80)
    print(f"🏆 RECOMMENDED: {best_config}")
    print("=" * 80)
    
    # Generate output video with best config
    best_conf = 0.01 if "aggressive" in best_config.lower() else (0.02 if "Balanced" in best_config else 0.03)
    
    print(f"\n🎬 Generating comparison video with conf={best_conf}...")
    
    output_dir = Path(__file__).parent / "output" / "mot17_indian_comparison"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate one video from each category
    test_samples = [
        (mot17_path / "MOT17-02-FRCNN" / "img1", "MOT17_Sparse", "img_seq"),
        (mot17_path / "MOT17-04-FRCNN" / "img1", "MOT17_Dense", "img_seq"),
        (indian_vids / "test_d1.mp4", "Indian_Dense", "video"),
        (indian_vids / "test2.mp4", "Indian_Sparse", "video"),
    ]
    
    for path, name, ptype in test_samples:
        if not path.exists():
            continue
        
        print(f"   Processing {name}...")
        
        if ptype == "video":
            cap = cv2.VideoCapture(str(path))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            out_path = output_dir / f"{name}_conf{best_conf}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))
            
            for i in range(50):
                ret, frame = cap.read()
                if not ret:
                    break
                
                results = model.predict(source=frame, conf=best_conf, iou=0.45, classes=[0], 
                                        max_det=1500, imgsz=1920, half=True, verbose=False)
                
                annotated = frame.copy()
                count = 0
                for result in results:
                    for j in range(len(result.boxes)):
                        box = result.boxes.xyxy[j].cpu().numpy()
                        x1, y1, x2, y2 = box
                        w, h = x2 - x1, y2 - y1
                        if w > 0 and h > 0 and 0.3 <= h/w <= 4.0:
                            count += 1
                            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                
                cv2.putText(annotated, f"{name}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                cv2.putText(annotated, f"People: {count}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                out.write(annotated)
            
            cap.release()
            out.release()
        
        else:  # Image sequence
            img_files = sorted(path.glob("*.jpg"))[:50]
            if not img_files:
                continue
            
            first = cv2.imread(str(img_files[0]))
            height, width = first.shape[:2]
            
            out_path = output_dir / f"{name}_conf{best_conf}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(out_path), fourcc, 10, (width, height))
            
            for img_path in img_files:
                frame = cv2.imread(str(img_path))
                if frame is None:
                    continue
                
                results = model.predict(source=frame, conf=best_conf, iou=0.45, classes=[0],
                                        max_det=1500, imgsz=1920, half=True, verbose=False)
                
                annotated = frame.copy()
                count = 0
                for result in results:
                    for j in range(len(result.boxes)):
                        box = result.boxes.xyxy[j].cpu().numpy()
                        x1, y1, x2, y2 = box
                        w, h = x2 - x1, y2 - y1
                        if w > 0 and h > 0 and 0.3 <= h/w <= 4.0:
                            count += 1
                            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                
                cv2.putText(annotated, f"{name}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                cv2.putText(annotated, f"People: {count}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                out.write(annotated)
            
            out.release()
    
    print(f"\n📁 Output videos saved to: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
