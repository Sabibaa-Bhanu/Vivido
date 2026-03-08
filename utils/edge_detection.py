"""Edge detection utilities for cartoonization workflows.

This module provides OpenCV-based edge extraction with tunable controls for:
- Canny edge detection
- Adaptive threshold edge detection
- Median blur denoising
- Edge thickness
- Sensitivity
- Original vs. edge side-by-side comparison
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np


EdgeMethod = Literal["canny", "adaptive"]
ImageType = Literal["portrait", "landscape", "object"]

__all__ = [
    "EdgeParams",
    "EdgeMethod",
    "ImageType",
    "OPTIMAL_SETTINGS",
    "detect_cartoon_edges",
    "detect_cartoon_edges_from_path",
    "detect_edges_adaptive",
    "detect_edges_canny",
    "compare_original_and_edges",
    "recommended_params",
    "optimal_settings_documentation",
]


@dataclass(frozen=True)
class EdgeParams:
    """Parameters for edge extraction."""

    method: EdgeMethod = "canny"
    # Canny params
    canny_low: int = 70
    canny_high: int = 140
    # Adaptive threshold params
    adaptive_block_size: int = 9
    adaptive_c: int = 2
    # Shared params
    median_blur_kernel: int = 5
    sensitivity: float = 1.0
    edge_thickness: int = 1
    invert: bool = False


OPTIMAL_SETTINGS: dict[ImageType, dict[str, object]] = {
    "portrait": {
        "method": "adaptive",
        "adaptive_block_size": 11,
        "adaptive_c": 3,
        "median_blur_kernel": 7,
        "sensitivity": 1.1,
        "edge_thickness": 1,
        "invert": False,
        "notes": "Best for soft facial contours and uneven skin lighting.",
    },
    "landscape": {
        "method": "canny",
        "canny_low": 60,
        "canny_high": 150,
        "median_blur_kernel": 5,
        "sensitivity": 1.0,
        "edge_thickness": 2,
        "invert": False,
        "notes": "Balanced for foliage, skyline, and terrain boundaries.",
    },
    "object": {
        "method": "canny",
        "canny_low": 80,
        "canny_high": 180,
        "median_blur_kernel": 5,
        "sensitivity": 0.95,
        "edge_thickness": 2,
        "invert": False,
        "notes": "Sharper outlines for products and man-made shapes.",
    },
}


def _validate_odd(value: int, minimum: int, field_name: str) -> int:
    if value < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    if value % 2 == 0:
        raise ValueError(f"{field_name} must be odd")
    return value


def _validate_image(image: np.ndarray) -> np.ndarray:
    if not isinstance(image, np.ndarray):
        raise TypeError("image must be a numpy array")
    if image.ndim not in (2, 3):
        raise ValueError("image must be grayscale (H,W) or color (H,W,C)")
    return image


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert an image to grayscale."""
    image = _validate_image(image)
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def apply_median_blur(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """Reduce noise before edge extraction."""
    _validate_odd(kernel_size, 3, "kernel_size")
    gray = to_grayscale(image)
    return cv2.medianBlur(gray, kernel_size)


def _apply_sensitivity_to_canny(low: int, high: int, sensitivity: float) -> tuple[int, int]:
    if sensitivity <= 0:
        raise ValueError("sensitivity must be > 0")
    # Higher sensitivity => lower thresholds => more edges detected.
    adjusted_low = max(1, int(low / sensitivity))
    adjusted_high = max(adjusted_low + 1, int(high / sensitivity))
    return adjusted_low, adjusted_high


def adjust_edge_thickness(edge_map: np.ndarray, thickness: int = 1) -> np.ndarray:
    """Increase edge thickness via dilation."""
    if thickness < 1:
        raise ValueError("thickness must be >= 1")
    if thickness == 1:
        return edge_map
    kernel = np.ones((3, 3), np.uint8)
    return cv2.dilate(edge_map, kernel, iterations=thickness - 1)


def detect_edges_canny(
    image: np.ndarray,
    low_threshold: int = 70,
    high_threshold: int = 140,
    median_blur_kernel: int = 5,
    sensitivity: float = 1.0,
    edge_thickness: int = 1,
    invert: bool = False,
) -> np.ndarray:
    """Detect edges using Canny with tunable sensitivity and thickness."""
    if low_threshold < 0 or high_threshold < 0:
        raise ValueError("Canny thresholds must be >= 0")
    if low_threshold >= high_threshold:
        raise ValueError("low_threshold must be lower than high_threshold")

    denoised = apply_median_blur(image, median_blur_kernel)
    adj_low, adj_high = _apply_sensitivity_to_canny(low_threshold, high_threshold, sensitivity)
    edges = cv2.Canny(denoised, adj_low, adj_high)
    edges = adjust_edge_thickness(edges, edge_thickness)
    if invert:
        edges = cv2.bitwise_not(edges)
    return edges


def detect_edges_adaptive(
    image: np.ndarray,
    block_size: int = 9,
    c_value: int = 2,
    median_blur_kernel: int = 5,
    sensitivity: float = 1.0,
    edge_thickness: int = 1,
    invert: bool = False,
) -> np.ndarray:
    """Detect edges using adaptive thresholding for varied lighting."""
    _validate_odd(block_size, 3, "block_size")
    denoised = apply_median_blur(image, median_blur_kernel)

    # Higher sensitivity means smaller C so threshold is easier to pass.
    adjusted_c = int(round(c_value / max(sensitivity, 0.1)))
    thresholded = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        adjusted_c,
    )
    edges = cv2.bitwise_not(thresholded)
    edges = adjust_edge_thickness(edges, edge_thickness)
    if invert:
        edges = cv2.bitwise_not(edges)
    return edges


def detect_cartoon_edges(image: np.ndarray, params: EdgeParams) -> np.ndarray:
    """Dispatch edge detection by method."""
    if params.method == "canny":
        return detect_edges_canny(
            image=image,
            low_threshold=params.canny_low,
            high_threshold=params.canny_high,
            median_blur_kernel=params.median_blur_kernel,
            sensitivity=params.sensitivity,
            edge_thickness=params.edge_thickness,
            invert=params.invert,
        )
    if params.method == "adaptive":
        return detect_edges_adaptive(
            image=image,
            block_size=params.adaptive_block_size,
            c_value=params.adaptive_c,
            median_blur_kernel=params.median_blur_kernel,
            sensitivity=params.sensitivity,
            edge_thickness=params.edge_thickness,
            invert=params.invert,
        )
    raise ValueError(f"Unsupported method: {params.method}")


def detect_cartoon_edges_from_path(
    image_path: str,
    params: EdgeParams | None = None,
    image_type: ImageType = "object",
) -> np.ndarray:
    """
    Load an image from disk and return cartoon-style edge map.

    If params is omitted, recommended preset values are used for image_type.
    """
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image from path: {image_path}")
    effective_params = params or recommended_params(image_type)
    return detect_cartoon_edges(image, effective_params)


def compare_original_and_edges(
    image: np.ndarray,
    edge_map: np.ndarray,
    label_original: str = "Original",
    label_edges: str = "Edges",
) -> np.ndarray:
    """Create a labeled side-by-side comparison image."""
    original = _validate_image(image)
    if original.ndim == 2:
        original = cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)

    if edge_map.ndim != 2:
        raise ValueError("edge_map must be grayscale (H,W)")
    edge_bgr = cv2.cvtColor(edge_map, cv2.COLOR_GRAY2BGR)

    if original.shape[:2] != edge_bgr.shape[:2]:
        edge_bgr = cv2.resize(edge_bgr, (original.shape[1], original.shape[0]), interpolation=cv2.INTER_NEAREST)

    panel = np.hstack([original, edge_bgr])
    cv2.putText(panel, label_original, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(
        panel,
        label_edges,
        (original.shape[1] + 20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return panel


def recommended_params(image_type: ImageType) -> EdgeParams:
    """Recommended parameter presets from local experiments for cartoon-like edges."""
    if image_type in OPTIMAL_SETTINGS:
        selected = OPTIMAL_SETTINGS[image_type]
        return EdgeParams(
            method=selected["method"],
            canny_low=selected.get("canny_low", 70),
            canny_high=selected.get("canny_high", 140),
            adaptive_block_size=selected.get("adaptive_block_size", 9),
            adaptive_c=selected.get("adaptive_c", 2),
            median_blur_kernel=selected.get("median_blur_kernel", 5),
            sensitivity=selected.get("sensitivity", 1.0),
            edge_thickness=selected.get("edge_thickness", 1),
            invert=selected.get("invert", False),
        )
    raise ValueError(f"Unsupported image_type: {image_type}")


def optimal_settings_documentation() -> dict[ImageType, dict[str, object]]:
    """Return documented optimal settings and notes by image type."""
    return {key: dict(value) for key, value in OPTIMAL_SETTINGS.items()}
