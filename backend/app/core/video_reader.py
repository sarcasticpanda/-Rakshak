"""
Unified frame reader for all input sources:
- Image sequences (MOT-style datasets)
- Video files (.mp4, .avi)
- Future: RTSP live streams

SOURCE-AGNOSTIC DESIGN:
All sources provide frames through the same interface
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Generator
from app.utils.config import DEFAULT_FPS, TARGET_RESOLUTION, FRAME_SKIP, VERBOSE


class FrameReader:
    """Unified interface for reading frames from different sources"""
    
    def __init__(self, source: str, source_type: str = "auto", fps: int = DEFAULT_FPS):
        """
        Initialize frame reader
        
        Args:
            source: Path to image folder, video file, or RTSP URL
            source_type: "images", "video", "rtsp", or "auto" (auto-detect)
            fps: Simulated FPS for image sequences
        """
        self.source = source
        self.fps = fps
        self.frame_count = 0
        self.current_frame_idx = 0
        
        # Auto-detect source type
        if source_type == "auto":
            self.source_type = self._detect_source_type(source)
        else:
            self.source_type = source_type
        
        # Initialize appropriate reader
        if self.source_type == "images":
            self._init_image_reader()
        elif self.source_type == "video":
            self._init_video_reader()
        elif self.source_type == "rtsp":
            self._init_rtsp_reader()
        else:
            raise ValueError(f"Unknown source type: {self.source_type}")
        
        if VERBOSE:
            print(f"[FrameReader] Initialized {self.source_type} reader: {source}")
            print(f"[FrameReader] Total frames: {self.frame_count}, FPS: {self.fps}")
    
    def _detect_source_type(self, source: str) -> str:
        """Auto-detect source type from path/URL"""
        source_path = Path(source)
        
        # Check if directory (image sequence)
        if source_path.is_dir():
            return "images"
        
        # Check if video file
        if source_path.is_file() and source_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
            return "video"
        
        # Check if RTSP stream
        if source.startswith(('rtsp://', 'http://', 'https://')):
            return "rtsp"
        
        raise ValueError(f"Cannot detect source type from: {source}")
    
    def _init_image_reader(self):
        """Initialize reader for image sequence (MOT-style)"""
        self.image_folder = Path(self.source)
        
        if not self.image_folder.exists():
            raise FileNotFoundError(f"Image folder not found: {self.source}")
        
        # Get all image files sorted by name
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        self.image_files = []
        for ext in image_extensions:
            self.image_files.extend(sorted(self.image_folder.glob(ext)))
        
        if not self.image_files:
            raise ValueError(f"No images found in: {self.source}")
        
        self.frame_count = len(self.image_files)
        self.cap = None  # No video capture object for images
    
    def _init_video_reader(self):
        """Initialize reader for video file"""
        self.cap = cv2.VideoCapture(self.source)
        
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video file: {self.source}")
        
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        self.image_files = None
    
    def _init_rtsp_reader(self):
        """Initialize reader for RTSP stream (future implementation)"""
        # TODO: Implement RTSP stream support
        raise NotImplementedError("RTSP support coming in future phase")
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read next frame (source-agnostic)
        
        Returns:
            (success, frame): success is True if frame read, frame is BGR numpy array
        """
        if self.source_type == "images":
            return self._read_image_frame()
        elif self.source_type == "video":
            return self._read_video_frame()
        elif self.source_type == "rtsp":
            return self._read_rtsp_frame()
    
    def _read_image_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from image sequence"""
        if self.current_frame_idx >= self.frame_count:
            return False, None
        
        # Apply frame skip
        actual_idx = self.current_frame_idx * FRAME_SKIP
        if actual_idx >= self.frame_count:
            return False, None
        
        image_path = self.image_files[actual_idx]
        frame = cv2.imread(str(image_path))
        
        if frame is None:
            print(f"[Warning] Failed to read image: {image_path}")
            self.current_frame_idx += 1
            return False, None
        
        # DO NOT RESIZE - pass original frame, YOLO will resize internally
        
        self.current_frame_idx += 1
        return True, frame
    
    def _read_video_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from video file"""
        # Apply frame skip
        for _ in range(FRAME_SKIP - 1):
            self.cap.grab()
        
        ret, frame = self.cap.read()
        
        if not ret:
            return False, None
        
        # DO NOT RESIZE - pass original frame, YOLO will resize internally
        
        self.current_frame_idx += 1
        return True, frame
    
    def _read_rtsp_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from RTSP stream"""
        # TODO: Implement
        raise NotImplementedError("RTSP support coming in future phase")
    
    def __iter__(self):
        """Make reader iterable"""
        return self
    
    def __next__(self) -> np.ndarray:
        """Get next frame for iteration"""
        success, frame = self.read_frame()
        if not success:
            raise StopIteration
        return frame
    
    def reset(self):
        """Reset to beginning"""
        self.current_frame_idx = 0
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    def get_progress(self) -> float:
        """Get processing progress (0.0 to 1.0)"""
        if self.frame_count == 0:
            return 0.0
        return self.current_frame_idx / self.frame_count
    
    def get_frame_info(self) -> dict:
        """Get current frame information"""
        return {
            "source_type": self.source_type,
            "current_frame": self.current_frame_idx,
            "total_frames": self.frame_count,
            "fps": self.fps,
            "progress": self.get_progress()
        }
    
    def release(self):
        """Release resources"""
        if self.cap is not None:
            self.cap.release()
        if VERBOSE:
            print(f"[FrameReader] Released resources")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.release()


# Convenience function for simple usage
def get_frame_reader(source: str, **kwargs) -> FrameReader:
    """
    Create frame reader with auto-detection
    
    Args:
        source: Path to images/video or RTSP URL
        **kwargs: Additional arguments for FrameReader
    
    Returns:
        FrameReader instance
    
    Example:
        reader = get_frame_reader("data/images/camera_01")
        for frame in reader:
            # Process frame
            pass
        reader.release()
    """
    return FrameReader(source, **kwargs)
