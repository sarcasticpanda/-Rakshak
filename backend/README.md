# Stampede-Rakshak Backend

AI-powered stampede detection system using computer vision and behavioral analysis.

## 🎯 Current Status: PHASE 1 COMPLETE

### ✅ Completed
- **Phase 0**: Project setup, venv, all dependencies installed with GPU support
- **Phase 1**: Frame reader (source-agnostic) + preprocessing

### 🔄 Next Phase
- **Phase 2**: YOLO person detection

---

## 🚀 Quick Start

### 1. Activate Virtual Environment
```bash
cd backend
.\venv\Scripts\activate  # Windows
```

### 2. Verify Installation
```bash
python test_installation.py
```

### 3. Extract MOT17 Dataset
Extract MOT17.zip and copy image sequences to:
```
backend/data/images/camera_01/
  ├── 000001.jpg
  ├── 000002.jpg
  └── ...
```

### 4. Run Phase 1 Test
```bash
python test_phase1.py
```

---

## 📁 Project Structure

```
backend/
├── venv/                    # Virtual environment
├── app/
│   ├── core/
│   │   └── video_reader.py  # ✅ PHASE 1
│   ├── utils/
│   │   ├── config.py        # ✅ PHASE 0
│   │   └── preprocessing.py # ✅ PHASE 1
│   └── api/
├── data/
│   ├── images/              # Put MOT17 here
│   └── videos/              # Put MP4 files here
├── output/                   # Generated outputs
├── requirements.txt          # ✅ PHASE 0
└── test_phase1.py           # ✅ PHASE 1
```

---

## 🔧 Tech Stack

- **Python**: 3.10.11
- **PyTorch**: 2.0.1+cu118 (GPU enabled)
- **YOLOv8**: 8.0.196
- **OpenCV**: 4.8.1.78
- **FastAPI**: 0.103.1
- **GPU**: NVIDIA GeForce RTX 3050

---

## 📋 Phase Roadmap

- [x] **Phase 0**: Project setup
- [x] **Phase 1**: Video ingestion + display
- [ ] **Phase 2**: YOLO person detection
- [ ] **Phase 3**: ByteTrack tracking
- [ ] **Phase 4**: Motion features
- [ ] **Phase 5**: Crowd metrics
- [ ] **Phase 6**: Panic aggregation
- [ ] **Phase 7**: Temporal consistency
- [ ] **Phase 8**: Risk engine
- [ ] **Phase 9**: Multi-camera fusion
- [ ] **Phase 10**: API + Frontend integration

---

## 🎮 Configuration

Edit `app/utils/config.py` to modify:
- Input/output paths
- YOLO settings
- Preprocessing options
- FPS and resolution
- All thresholds

---

## 📝 Notes

- Frame reader is **source-agnostic**: works with images, videos, and future RTSP
- Preprocessing handles lighting variations automatically
- All frames are resized to 1280x720 by default
- GPU acceleration is enabled for PyTorch/YOLO

---

## 🐛 Troubleshooting

### Import errors
```bash
# Make sure venv is activated
.\venv\Scripts\activate
```

### CUDA not available
- Check GPU drivers
- Verify: `python -c "import torch; print(torch.cuda.is_available())"`

### No images found
- Extract MOT17 to `data/images/camera_01/`
- Check file extensions (.jpg, .png)

---

**Ready for Phase 2: YOLO Detection!** 🚀
