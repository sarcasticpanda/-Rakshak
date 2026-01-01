"""
Video Streaming API - MJPEG Streams
Non-blocking proxy to SharedFrameStore
"""
import cv2
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
    while True:
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
            # No frame available - send blank frame
            blank = cv2.imencode('.jpg', 
                                cv2.putText(
                                    cv2.rectangle(
                                        cv2.UMat((480, 640, 3), cv2.CV_8UC3).get(), 
                                        (0,0), (640, 480), (0,0,0), -1
                                    ).get(),
                                    "NO SIGNAL", 
                                    (200, 240), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 
                                    1.0, (255, 255, 255), 2
                                ).get())[1]
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + 
                   blank.tobytes() + b'\r\n')


@router.get("/{camera_id}")
async def get_camera_stream(camera_id: str):
    """
    Get MJPEG stream for camera
    
    Args:
        camera_id: Camera identifier
        
    Returns:
        MJPEG stream
    """
    # Check if camera exists
    if camera_id not in shared_store.list_cameras():
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return StreamingResponse(
        generate_mjpeg_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
