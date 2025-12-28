# Data Directory

## Structure

### images/
Store image sequences (MOT-style datasets) here.

Example:
```
images/
├── camera_01/
│   ├── 000001.jpg
│   ├── 000002.jpg
│   └── ...
└── camera_02/
    ├── 000001.jpg
    └── ...
```

### videos/
Store video files (.mp4, .avi) here for testing.

Example:
```
videos/
├── test_crowd_01.mp4
└── test_rush_02.mp4
```

## MOT17 Dataset Instructions

1. Extract MOT17.zip
2. Copy image sequences to `images/camera_01/`, `images/camera_02/`, etc.
3. Each sequence folder should contain numbered images (000001.jpg, 000002.jpg, ...)
4. The system will read them in sorted order as a video stream

## Notes
- Image sequences simulate video at configurable FPS (default: 10)
- Pipeline is source-agnostic: images, videos, and RTSP streams use the same processing logic
