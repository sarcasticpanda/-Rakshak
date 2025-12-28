"""
Preprocessing utilities for lighting normalization
Used before YOLO detection to handle various lighting conditions
"""
import cv2
import numpy as np
from app.utils.config import (
    ENABLE_CLAHE, CLAHE_CLIP_LIMIT, CLAHE_GRID_SIZE,
    ENABLE_GAMMA_CORRECTION, GAMMA_VALUE,
    ENABLE_BRIGHTNESS_NORM, TARGET_BRIGHTNESS
)


def apply_clahe(image: np.ndarray) -> np.ndarray:
    """
    Apply Contrast Limited Adaptive Histogram Equalization
    Improves local contrast in low-light scenes
    
    Args:
        image: Input BGR image
    Returns:
        Enhanced BGR image
    """
    # Convert to LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_GRID_SIZE)
    l_clahe = clahe.apply(l)
    
    # Merge and convert back
    lab_clahe = cv2.merge([l_clahe, a, b])
    enhanced = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
    
    return enhanced


def apply_gamma_correction(image: np.ndarray, gamma: float = GAMMA_VALUE) -> np.ndarray:
    """
    Apply gamma correction for brightness adjustment
    
    Args:
        image: Input BGR image
        gamma: Gamma value (>1 brightens, <1 darkens)
    Returns:
        Gamma-corrected BGR image
    """
    inv_gamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv_gamma * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(image, table)


def normalize_brightness(image: np.ndarray, target: int = TARGET_BRIGHTNESS) -> np.ndarray:
    """
    Normalize image brightness to target value
    
    Args:
        image: Input BGR image
        target: Target mean brightness (0-255)
    Returns:
        Brightness-normalized BGR image
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    current_brightness = gray.mean()
    
    if current_brightness == 0:
        return image
    
    ratio = target / current_brightness
    adjusted = cv2.convertScaleAbs(image, alpha=ratio, beta=0)
    
    return adjusted


def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    """
    Main preprocessing pipeline for lighting normalization
    Called before YOLO detection
    
    Args:
        frame: Input BGR frame
    Returns:
        Preprocessed BGR frame
    """
    if frame is None:
        return None
    
    processed = frame.copy()
    
    # Apply enabled preprocessing techniques
    if ENABLE_CLAHE:
        processed = apply_clahe(processed)
    
    if ENABLE_GAMMA_CORRECTION:
        processed = apply_gamma_correction(processed, GAMMA_VALUE)
    
    if ENABLE_BRIGHTNESS_NORM:
        processed = normalize_brightness(processed, TARGET_BRIGHTNESS)
    
    return processed


def auto_detect_lighting(frame: np.ndarray) -> str:
    """
    Automatically detect lighting condition
    Can be used for adaptive preprocessing
    
    Args:
        frame: Input BGR frame
    Returns:
        Lighting condition: "bright", "normal", "low", "dark"
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_brightness = gray.mean()
    
    if mean_brightness > 180:
        return "bright"
    elif mean_brightness > 120:
        return "normal"
    elif mean_brightness > 60:
        return "low"
    else:
        return "dark"
