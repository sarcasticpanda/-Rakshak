"""
Multi-Video Display Manager
Manages multiple VideoStreamProcessor threads and displays in grid
"""
import cv2
import time
import numpy as np
from typing import List, Dict
import torch
from pathlib import Path

from app.core.video_stream_processor import VideoStreamProcessor
from app.core.robust_pipeline import RobustDetectionPipeline


class MultiVideoDisplay:
    """
    Manages multiple video processors and displays in grid.
    
    Features:
    - One shared YOLO detector (memory efficient)
    - Multiple threads processing independently
    - Non-blocking display at 30 FPS
    - GPU memory monitoring
    """
    
    def __init__(self, max_videos: int = 10):
        """
        Initialize manager.
        
        Args:
            max_videos: Maximum simultaneous videos (GPU memory limit)
        """
        self.max_videos = max_videos
        self.processors: List[VideoStreamProcessor] = []
        
        # Shared detector (loaded once, used by all threads)
        print("[MultiVideoDisplay] Loading shared YOLOv8m detector...")
        if torch.cuda.is_available():
            gpu_mem_before = torch.cuda.memory_allocated(0) / 1024**2
            print(f"[MultiVideoDisplay] GPU memory before: {gpu_mem_before:.0f} MB")
        
        self.shared_detector = RobustDetectionPipeline(enable_heatmap=True)
        
        if torch.cuda.is_available():
            gpu_mem_after = torch.cuda.memory_allocated(0) / 1024**2
            print(f"[MultiVideoDisplay] GPU memory after: {gpu_mem_after:.0f} MB (Δ {gpu_mem_after - gpu_mem_before:.0f} MB)")
        
        print("[MultiVideoDisplay] ✅ Shared detector ready")
    
    def add_video(self, video_source: str, camera_id: str, camera_name: str, 
                  target_fps: int = 8) -> bool:
        """
        Add a video to process.
        
        Args:
            video_source: Path to video file or stream URL
            camera_id: Unique identifier
            camera_name: Display name
            target_fps: Target processing FPS (8-10 recommended)
            
        Returns:
            True if added successfully
        """
        if len(self.processors) >= self.max_videos:
            print(f"[MultiVideoDisplay] ❌ Max videos reached ({self.max_videos})")
            return False
        
        # Create processor with shared detector
        processor = VideoStreamProcessor(
            video_source=video_source,
            camera_id=camera_id,
            camera_name=camera_name,
            detector=self.shared_detector,  # SHARED
            target_fps=target_fps
        )
        
        if processor.connect():
            self.processors.append(processor)
            print(f"[MultiVideoDisplay] Added: {camera_id} ({camera_name})")
            return True
        else:
            return False
    
    def start_all(self):
        """Start all video processors"""
        print(f"\n[MultiVideoDisplay] Starting {len(self.processors)} processors...")
        for processor in self.processors:
            processor.start()
        
        # Wait for threads to produce first frames
        print("[MultiVideoDisplay] Warming up (5 seconds)...")
        time.sleep(5)
        print("[MultiVideoDisplay] ✅ All processors started\n")
    
    def stop_all(self):
        """Stop all processors"""
        print("\n[MultiVideoDisplay] Stopping all processors...")
        for processor in self.processors:
            processor.stop()
            processor.disconnect()
        print("[MultiVideoDisplay] ✅ All processors stopped")
    
    def display_loop(self):
        """
        Main display loop (runs at 30 FPS).
        Non-blocking - gets latest frame from each processor.
        """
        print("="*60)
        print("MULTI-VIDEO PARALLEL PROCESSING")
        print("="*60)
        print(f"Videos: {len(self.processors)}")
        print(f"Display: 30 FPS (fixed)")
        print(f"Processing: {self.processors[0].target_fps} FPS per video (target)")
        print("="*60)
        print("Press Q to quit, S for screenshot")
        print("="*60)
        
        # Create window
        cv2.namedWindow("Multi-Video Grid", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Multi-Video Grid", 1280, 720)
        
        frame_count = 0
        start_time = time.time()
        last_stats_time = time.time()
        
        try:
            while True:
                loop_start = time.time()
                
                # Collect latest frames (non-blocking)
                frames = []
                total_people = 0
                max_risk = 0.0
                
                for processor in self.processors:
                    frame = processor.get_latest_frame()
                    metrics = processor.get_metrics()
                    
                    if frame is not None:
                        # Resize for grid
                        frame_resized = cv2.resize(frame, (640, 360))
                        frames.append((processor.camera_name, frame_resized))
                        
                        if metrics:
                            total_people += metrics['people_count']
                            max_risk = max(max_risk, metrics['risk_score'])
                
                # Create grid
                if len(frames) > 0:
                    grid = self._create_grid(frames, grid_cols=2)
                    
                    if grid is not None and grid.size > 0:
                        # Calculate display FPS
                        elapsed = time.time() - start_time
                        display_fps = frame_count / elapsed if elapsed > 0 else 0
                        loop_time = (time.time() - loop_start) * 1000
                        
                        # Add global overlay
                        h, w = grid.shape[:2]
                        cv2.rectangle(grid, (0, 0), (w, 80), (0, 0, 0), -1)
                        
                        # Title
                        cv2.putText(grid, f"MULTI-VIDEO PARALLEL MONITORING", 
                                   (w//2 - 280, 25),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                        
                        # Stats line 1
                        cv2.putText(grid, f"Display FPS: {display_fps:.1f} | Frame: {frame_count} | Process: {loop_time:.0f}ms", 
                                   (w//2 - 280, 48),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                        
                        # Stats line 2
                        cv2.putText(grid, f"Total People: {total_people} | Max Risk: {max_risk:.0f} | Videos: {len(frames)}/{len(self.processors)}", 
                                   (w//2 - 280, 68),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        
                        # Display
                        cv2.imshow("Multi-Video Grid", grid)
                        frame_count += 1
                        
                        # Print stats every 5 seconds
                        if time.time() - last_stats_time >= 5.0:
                            print(f"\n[Frame {frame_count}] Display FPS: {display_fps:.1f}")
                            for processor in self.processors:
                                metrics = processor.get_metrics()
                                if metrics:
                                    print(f"  {processor.camera_id}: {metrics['people_count']} people | "
                                          f"Risk: {metrics['risk_score']:.0f} | "
                                          f"FPS: {metrics['fps']:.1f}")
                            print(f"  TOTAL: {total_people} people | Max Risk: {max_risk:.0f}")
                            
                            # GPU memory
                            if torch.cuda.is_available():
                                gpu_mem = torch.cuda.memory_allocated(0) / 1024**2
                                print(f"  GPU Memory: {gpu_mem:.0f} MB")
                            
                            last_stats_time = time.time()
                
                # Controls (30ms = ~33 FPS display rate)
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    print("\n⛔ Quit requested")
                    break
                elif key == ord('s'):
                    if 'grid' in locals() and grid is not None:
                        output_dir = Path("output/multi_video")
                        output_dir.mkdir(parents=True, exist_ok=True)
                        filename = output_dir / f"parallel_{int(time.time())}.jpg"
                        cv2.imwrite(str(filename), grid)
                        print(f"\n📸 Screenshot saved: {filename}")
        
        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted by user")
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cv2.destroyAllWindows()
            
            # Final stats
            elapsed = time.time() - start_time
            avg_fps = frame_count / elapsed if elapsed > 0 else 0
            print("\n" + "="*60)
            print("PARALLEL PROCESSING COMPLETE")
            print("="*60)
            print(f"Total frames displayed: {frame_count}")
            print(f"Total time: {elapsed:.1f}s")
            print(f"Average display FPS: {avg_fps:.1f}")
            print("="*60)
    
    def _create_grid(self, frames: List[tuple], grid_cols: int = 2) -> np.ndarray:
        """
        Create grid from frames.
        
        Args:
            frames: List of (name, frame) tuples
            grid_cols: Number of columns
            
        Returns:
            Grid image
        """
        if not frames:
            return None
        
        n_frames = len(frames)
        grid_rows = (n_frames + grid_cols - 1) // grid_cols
        
        # Get frame dimensions
        h, w = frames[0][1].shape[:2]
        
        # Create grid
        grid_h = h * grid_rows
        grid_w = w * grid_cols
        grid = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
        
        # Place frames
        for idx, (name, frame) in enumerate(frames):
            row = idx // grid_cols
            col = idx % grid_cols
            
            y1 = row * h
            y2 = y1 + h
            x1 = col * w
            x2 = x1 + w
            
            grid[y1:y2, x1:x2] = frame
        
        return grid
