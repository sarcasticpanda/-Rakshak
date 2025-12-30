"""
Test Multi-Camera Parallel Processing
Shows 2-3 cameras running simultaneously in separate processes
"""
import cv2
import time
from pathlib import Path
import sys

sys.path.insert(0, '.')
from app.core.camera_manager import CameraManager, CameraConfig


def main():
    print("="*60)
    print("MULTI-CAMERA PARALLEL PROCESSING TEST")
    print("="*60)
    
    manager = CameraManager()
    
    # Camera 1: Stampede video
    print("\n[Setup] Adding cameras...")
    manager.add_camera(CameraConfig(
        camera_id="cam_stampede",
        name="Stampede Video",
        source="../check_vids/stampede.mp4",
        location="Test Location 1",
        context="dense_crowd",
        target_fps=8
    ))
    
    # Camera 2: Test2 video
    manager.add_camera(CameraConfig(
        camera_id="cam_test2",
        name="Test2 Video",
        source="../check_vids/test2.mp4",
        location="Test Location 2",
        context="sparse_crowd",
        target_fps=8
    ))
    
    # Camera 3: Test3 video
    manager.add_camera(CameraConfig(
        camera_id="cam_test3",
        name="Test3 Video",
        source="../check_vids/test3.mp4",
        location="Test Location 3",
        context="medium_crowd",
        target_fps=8
    ))
    
    # Optional: Add IP Webcam if available
    # Uncomment this to test with your phone:
    """
    manager.add_camera(CameraConfig(
        camera_id="cam_phone",
        name="Phone Camera",
        source="http://100.115.33.220:8080/video",
        location="Mobile Phone",
        context="live",
        target_fps=6
    ))
    """
    
    print("\n[Setup] Starting all cameras...")
    manager.start_all()
    
    print("\n" + "="*60)
    print("CAMERAS RUNNING - Monitoring metrics")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    try:
        iteration = 0
        while True:
            time.sleep(2)
            iteration += 1
            
            # Get metrics from all cameras
            all_metrics = manager.get_metrics()
            
            # Display status
            print(f"\n--- Update {iteration} ---")
            for camera_id, metrics in all_metrics.items():
                print(f"  [{camera_id}] "
                      f"People: {metrics.get('people_count', 0):3d} | "
                      f"Risk: {metrics.get('risk_score', 0):5.1f} | "
                      f"{metrics.get('risk_level', 'UNKNOWN'):8s} | "
                      f"FPS: {metrics.get('fps', 0):4.1f}")
            
            # Global stats every 10 seconds
            if iteration % 5 == 0:
                stats = manager.get_global_stats()
                print("\n" + "="*60)
                print(f"📊 GLOBAL STATS:")
                print(f"   Total People: {stats['total_people']}")
                print(f"   Max Risk: {stats['max_risk_score']:.1f}")
                print(f"   Critical Cameras: {stats['critical_cameras']}")
                print(f"   Warning Cameras: {stats['warning_cameras']}")
                print(f"   Active Cameras: {stats['active_cameras']}/{stats['total_cameras']}")
                print("="*60)
    
    except KeyboardInterrupt:
        print("\n\n[User] Stopping...")
    
    finally:
        manager.stop_all()
        print("\n" + "="*60)
        print("✅ All cameras stopped")
        print("="*60)
        
        # Final status
        print("\n📋 Final Status:")
        for status in manager.get_all_status():
            print(f"  {status['name']}: {status['status']} | "
                  f"Last people count: {status['people_count']}")


if __name__ == "__main__":
    main()
