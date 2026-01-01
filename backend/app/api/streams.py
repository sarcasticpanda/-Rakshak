"""
Video Streaming API - MJPEG Streams
Non-blocking proxy to SharedFrameStore
"""
import time
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.core.shared_store import shared_store


router = APIRouter(prefix="/stream", tags=["streams"])


def generate_mjpeg_stream(camera_id: str):
    """
    Generate MJPEG stream for camera
    
    Args:
        camera_id: Camera identifier
        
    Yields:
        JPEG frames in MJPEG format
    """
    frame_delay = 0.033  # 30 FPS = ~33ms between frames
    
    while True:
        try:
            # Get latest frame from shared store (non-blocking)
            frame = shared_store.get_frame(camera_id)
            
            if frame is not None:
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                if ret:
                    # Yield frame in MJPEG format
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           buffer.tobytes() + b'\r\n')
            else:
                # No frame available - send blank frame with "NO SIGNAL"
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.rectangle(blank, (0, 0), (640, 480), (0, 0, 0), -1)
                cv2.putText(blank, "NO SIGNAL", (200, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                
                ret, buffer = cv2.imencode('.jpg', blank, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           buffer.tobytes() + b'\r\n')
            
            # CRITICAL: Sleep to control frame rate
            time.sleep(frame_delay)
            
        except GeneratorExit:
            # Client disconnected
            break
        except Exception as e:
            # Log error but don't crash the stream
            print(f"[Stream:{camera_id}] Error: {e}")
            time.sleep(0.1)


@router.get("/{camera_id}")
async def get_camera_stream(camera_id: str):
    """
    Get MJPEG stream for camera
    
    Args:
        camera_id: Camera identifier
        
    Returns:
        MJPEG stream
    """
    # Note: We don't check if camera exists here - generator will show "NO SIGNAL"
    # if no frames are available. This simplifies the code.
    
    return StreamingResponse(
        generate_mjpeg_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
