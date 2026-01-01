"""
Debug Heatmap Visualization
Shows just one camera with enhanced heatmap overlay
"""
import cv2
import sys
import time
import numpy as np

sys.path.insert(0, '.')
from app.core.camera_pipeline import CameraPipeline, CameraConfig

def main():
    print("=" * 60)
    print("HEATMAP DEBUG - SINGLE CAMERA")
    print("=" * 60)
    
    # Single camera for testing
    cam = CameraPipeline(CameraConfig(
        camera_id="debug_cam",
        name="Stampede Debug",
        source="../check_vids/stampede.mp4",
        location="Debug Location",
        target_fps=30
    ))
    
    if not cam.connect():
        print("❌ Failed to connect")
        return
    
    cam.start()
    print("✅ Camera started")
    print("\nWaiting for heatmap bootstrap (30 frames)...")
    print("CONTROLS: Q = Quit | H = Toggle heatmap visibility")
    print("=" * 60)
    
    time.sleep(2)
    
    frame_count = 0
    show_heatmap_only = False
    
    try:
        while True:
            frame = cam.get_frame()
            
            if frame is not None:
                frame_count += 1
                
                # Get heatmap status
                is_bootstrapped = cam.detector.heatmap and cam.detector.heatmap.is_bootstrapped()
                
                # Create display frame
                display = frame.copy()
                h, w = display.shape[:2]
                
                # Show heatmap visualization if available
                if is_bootstrapped:
                    heat_vis = cam.detector.heatmap.get_visualization()
                    
                    if heat_vis is not None:
                        if show_heatmap_only:
                            # Show ONLY heatmap (for debugging visibility)
                            display = heat_vis
                            cv2.putText(display, "HEATMAP ONLY MODE", (10, 30),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                        else:
                            # Normal blended mode
                            display = cv2.addWeighted(frame, 0.5, heat_vis, 0.5, 0)
                        
                        # Get heatmap stats
                        max_heat = np.max(cam.detector.heatmap.temporal_heatmap)
                        mean_heat = np.mean(cam.detector.heatmap.temporal_heatmap)
                        
                        # Status overlay
                        status_y = 30
                        cv2.putText(display, f"Frame: {frame_count}", (10, status_y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        status_y += 30
                        cv2.putText(display, f"Heatmap: ACTIVE", (10, status_y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        status_y += 30
                        cv2.putText(display, f"Max Heat: {max_heat:.3f}", (10, status_y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        status_y += 30
                        cv2.putText(display, f"Mean Heat: {mean_heat:.3f}", (10, status_y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        status_y += 30
                        cv2.putText(display, f"Updates: {cam.detector.heatmap.update_count}", (10, status_y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                else:
                    # Bootstrapping
                    cv2.putText(display, f"WARMING UP... ({frame_count}/30)", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                
                # Bottom help text
                cv2.putText(display, "Press H to toggle heatmap-only mode | Q to quit", 
                           (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                cv2.imshow("Heatmap Debug", display)
                
                # Print status every 60 frames
                if frame_count % 60 == 1:
                    if is_bootstrapped:
                        print(f"[Frame {frame_count}] Heatmap active | Max: {max_heat:.3f} | Mean: {mean_heat:.3f}")
                    else:
                        print(f"[Frame {frame_count}] Bootstrapping...")
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n⛔ Quit")
                break
            elif key == ord('h'):
                show_heatmap_only = not show_heatmap_only
                mode = "HEATMAP ONLY" if show_heatmap_only else "BLENDED"
                print(f"\n🔄 Switched to {mode} mode")
                
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
    finally:
        cam.stop()
        cam.disconnect()
        cv2.destroyAllWindows()
        print("✅ Done")

if __name__ == "__main__":
    main()
