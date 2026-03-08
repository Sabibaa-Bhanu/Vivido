"""Cartoonization utilities: bilateral filtering + color quantization.

This module provides the base painted/cartoon effect by combining:
1) bilateral smoothing to preserve edges while flattening texture/noise
2) K-means color quantization to reduce palette complexity

It also includes:
- adjustable parameters for effect intensity and performance
- style presets with documented recommended values
- lightweight profiling helpers for parameter comparison
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Iterable, Literal

import cv2
import numpy as np
from utils.edge_detection import EdgeParams, detect_cartoon_edges


StyleName = Literal["soft_paint", "classic_cartoon", "bold_poster", "comic_ink"]
IntensityLevel = Literal["light", "medium", "strong"]
EdgeChoice = Literal["auto", "canny", "adaptive"]

__all__ = [
    "CartoonParams",
    "ClassicCartoonParams",
    "StyleName",
    "IntensityLevel",
    "EdgeChoice",
    "STYLE_PRESETS",
    "apply_bilateral_filter",
    "color_quantize_kmeans",
    "create_base_cartoon_effect",
    "create_classic_cartoon",
    "create_classic_cartoon_from_path",
    "compare_original_and_cartoon",
    "profile_parameter_combinations",
    "benchmark_classic_cartoon",
    "recommended_style_params",
    "documented_style_settings",
]


@dataclass(frozen=True)
class CartoonParams:
    """Parameters controlling base cartoon effect strength and speed."""

    num_colors: int = 12
    bilateral_d: int = 9
    bilateral_sigma_color: float = 75.0
    bilateral_sigma_space: float = 75.0
    bilateral_passes: int = 1
    kmeans_attempts: int = 3
    # Optional speed optimization: run effect on smaller image and upscale.
    downsample_scale: float = 1.0
    # Optional speed optimization: train K-means on a pixel subset.
    sample_pixels: int = 12000
    random_seed: int = 42


@dataclass(frozen=True)
class ClassicCartoonParams:
    """Combined parameters for full cartoon effect (base + edges)."""

    base: CartoonParams
    edges: EdgeParams
    resize_max_dim: int = 1280
    pre_denoise_kernel: int = 3
    edge_line_opacity: float = 1.0


STYLE_PRESETS: dict[StyleName, dict[str, object]] = {
    "soft_paint": {
        "params": CartoonParams(
            num_colors=16,
            bilateral_d=9,
            bilateral_sigma_color=60.0,
            bilateral_sigma_space=60.0,
            bilateral_passes=1,
            downsample_scale=1.0,
            sample_pixels=14000,
        ),
        "notes": "Natural painterly look with gentle flattening and richer palette.",
    },
    "classic_cartoon": {
        "params": CartoonParams(
            num_colors=12,
            bilateral_d=9,
            bilateral_sigma_color=85.0,
            bilateral_sigma_space=85.0,
            bilateral_passes=2,
            downsample_scale=1.0,
            sample_pixels=12000,
        ),
        "notes": "Balanced cartoon look; clean surfaces without over-posterization.",
    },
    "bold_poster": {
        "params": CartoonParams(
            num_colors=8,
            bilateral_d=7,
            bilateral_sigma_color=95.0,
            bilateral_sigma_space=95.0,
            bilateral_passes=2,
            downsample_scale=0.9,
            sample_pixels=10000,
        ),
        "notes": "Strong flat regions and high stylization, good for graphics-like output.",
    },
    "comic_ink": {
        "params": CartoonParams(
            num_colors=10,
            bilateral_d=11,
            bilateral_sigma_color=110.0,
            bilateral_sigma_space=100.0,
            bilateral_passes=2,
            downsample_scale=0.85,
            sample_pixels=9000,
        ),
        "notes": "Heavy smoothing and aggressive palette reduction for comic-style tones.",
    },
}


CLASSIC_CARTOON_PRESETS: dict[IntensityLevel, ClassicCartoonParams] = {
    "light": ClassicCartoonParams(
        base=CartoonParams(
            num_colors=18,
            bilateral_d=9,
            bilateral_sigma_color=70.0,
            bilateral_sigma_space=70.0,
            bilateral_passes=2,
            kmeans_attempts=5,
            downsample_scale=1.0,
            sample_pixels=20000,
        ),
        edges=EdgeParams(
            method="adaptive",
            adaptive_block_size=11,
            adaptive_c=3,
            median_blur_kernel=5,
            sensitivity=0.9,
            edge_thickness=1,
            invert=False,
        ),
        resize_max_dim=1920,
        pre_denoise_kernel=3,
        edge_line_opacity=0.85,
    ),
    "medium": ClassicCartoonParams(
        base=CartoonParams(
            num_colors=16,
            bilateral_d=9,
            bilateral_sigma_color=90.0,
            bilateral_sigma_space=90.0,
            bilateral_passes=3,
            kmeans_attempts=5,
            downsample_scale=1.0,
            sample_pixels=20000,
        ),
        edges=EdgeParams(
            method="adaptive",
            adaptive_block_size=9,
            adaptive_c=2,
            median_blur_kernel=5,
            sensitivity=1.1,
            edge_thickness=2,
            invert=False,
        ),
        resize_max_dim=1920,
        pre_denoise_kernel=3,
        edge_line_opacity=1.0,
    ),
    "strong": ClassicCartoonParams(
        base=CartoonParams(
            num_colors=10,
            bilateral_d=11,
            bilateral_sigma_color=110.0,
            bilateral_sigma_space=105.0,
            bilateral_passes=3,
            kmeans_attempts=5,
            downsample_scale=1.0,
            sample_pixels=18000,
        ),
        edges=EdgeParams(
            method="canny",
            canny_low=55,
            canny_high=145,
            median_blur_kernel=7,
            sensitivity=1.25,
            edge_thickness=3,
            invert=False,
        ),
        resize_max_dim=1600,
        pre_denoise_kernel=5,
        edge_line_opacity=1.0,
    ),
}


def _validate_color_image(image: np.ndarray) -> np.ndarray:
    if not isinstance(image, np.ndarray):
        raise TypeError("image must be a numpy array")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image must be BGR color (H,W,3)")
    if image.dtype != np.uint8:
        raise ValueError("image must be uint8")
    return image


def _validate_params(params: CartoonParams) -> None:
    if params.num_colors < 2 or params.num_colors > 64:
        raise ValueError("num_colors must be in [2, 64]")
    if params.bilateral_d <= 0:
        raise ValueError("bilateral_d must be > 0")
    if params.bilateral_sigma_color <= 0 or params.bilateral_sigma_space <= 0:
        raise ValueError("bilateral sigma values must be > 0")
    if params.bilateral_passes < 1 or params.bilateral_passes > 6:
        raise ValueError("bilateral_passes must be in [1, 6]")
    if params.kmeans_attempts < 1 or params.kmeans_attempts > 20:
        raise ValueError("kmeans_attempts must be in [1, 20]")
    if params.downsample_scale <= 0 or params.downsample_scale > 1.0:
        raise ValueError("downsample_scale must be in (0, 1]")
    if params.sample_pixels < 256:
        raise ValueError("sample_pixels must be >= 256")


def _ensure_odd_at_least(value: int, minimum: int) -> int:
    if value < minimum:
        value = minimum
    if value % 2 == 0:
        value += 1
    return value


def preprocess_for_cartoon(
    image: np.ndarray,
    resize_max_dim: int = 1280,
    denoise_kernel: int = 3,
) -> tuple[np.ndarray, tuple[int, int]]:
    """Resize and denoise input for faster and cleaner stylization."""
    image = _validate_color_image(image)
    if resize_max_dim < 64:
        raise ValueError("resize_max_dim must be >= 64")

    original_h, original_w = image.shape[:2]
    working = image
    longest = max(original_h, original_w)
    if longest > resize_max_dim:
        scale = float(resize_max_dim) / float(longest)
        resized_w = max(32, int(round(original_w * scale)))
        resized_h = max(32, int(round(original_h * scale)))
        working = cv2.resize(image, (resized_w, resized_h), interpolation=cv2.INTER_AREA)

    kernel = _ensure_odd_at_least(denoise_kernel, 1)
    if kernel > 1:
        working = cv2.medianBlur(working, kernel)

    return working, (original_h, original_w)


def apply_bilateral_filter(
    image: np.ndarray,
    d: int = 9,
    sigma_color: float = 75.0,
    sigma_space: float = 75.0,
    passes: int = 1,
) -> np.ndarray:
    """Smooth while preserving edges (painted base look)."""
    image = _validate_color_image(image)
    if d <= 0:
        raise ValueError("d must be > 0")
    if sigma_color <= 0 or sigma_space <= 0:
        raise ValueError("sigma values must be > 0")
    if passes < 1:
        raise ValueError("passes must be >= 1")

    output = image.copy()
    for _ in range(passes):
        output = cv2.bilateralFilter(output, d=d, sigmaColor=sigma_color, sigmaSpace=sigma_space)
    return output


def _kmeans_centers_from_image(
    image: np.ndarray,
    num_colors: int,
    attempts: int,
    sample_pixels: int,
    random_seed: int,
) -> np.ndarray:
    pixels = image.reshape((-1, 3)).astype(np.float32)
    total = pixels.shape[0]

    if total > sample_pixels:
        rng = np.random.default_rng(random_seed)
        indices = rng.choice(total, size=sample_pixels, replace=False)
        train_pixels = pixels[indices]
    else:
        train_pixels = pixels

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.1)
    compactness, labels, centers = cv2.kmeans(
        train_pixels,
        num_colors,
        None,
        criteria,
        attempts,
        cv2.KMEANS_PP_CENTERS,
    )
    _ = compactness, labels
    return centers.astype(np.float32)


def _assign_to_centers(pixels: np.ndarray, centers: np.ndarray, chunk_size: int = 50000) -> np.ndarray:
    # Chunked nearest-center assignment avoids large memory spikes.
    out = np.empty_like(pixels, dtype=np.float32)
    for start in range(0, pixels.shape[0], chunk_size):
        end = min(start + chunk_size, pixels.shape[0])
        chunk = pixels[start:end]
        dist = np.sum((chunk[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        nearest = np.argmin(dist, axis=1)
        out[start:end] = centers[nearest]
    return out


def color_quantize_kmeans(
    image: np.ndarray,
    num_colors: int = 12,
    attempts: int = 3,
    sample_pixels: int = 12000,
    random_seed: int = 42,
) -> np.ndarray:
    """Reduce image to a limited color palette using K-means."""
    image = _validate_color_image(image)
    if num_colors < 2 or num_colors > 64:
        raise ValueError("num_colors must be in [2, 64]")
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    pixels = image.reshape((-1, 3)).astype(np.float32)
    centers = _kmeans_centers_from_image(
        image=image,
        num_colors=num_colors,
        attempts=attempts,
        sample_pixels=sample_pixels,
        random_seed=random_seed,
    )
    quantized_pixels = _assign_to_centers(pixels, centers)
    quantized = quantized_pixels.reshape(image.shape).astype(np.uint8)
    return quantized


def create_base_cartoon_effect(image: np.ndarray, params: CartoonParams) -> np.ndarray:
    """Create cartoon base by bilateral smoothing + color quantization."""
    image = _validate_color_image(image)
    _validate_params(params)

    working = image
    original_h, original_w = image.shape[:2]
    if params.downsample_scale < 1.0:
        scaled_w = max(32, int(original_w * params.downsample_scale))
        scaled_h = max(32, int(original_h * params.downsample_scale))
        working = cv2.resize(image, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)

    smooth = apply_bilateral_filter(
        image=working,
        d=params.bilateral_d,
        sigma_color=params.bilateral_sigma_color,
        sigma_space=params.bilateral_sigma_space,
        passes=params.bilateral_passes,
    )
    quantized = color_quantize_kmeans(
        image=smooth,
        num_colors=params.num_colors,
        attempts=params.kmeans_attempts,
        sample_pixels=params.sample_pixels,
        random_seed=params.random_seed,
    )

    if params.downsample_scale < 1.0:
        quantized = cv2.resize(quantized, (original_w, original_h), interpolation=cv2.INTER_LANCZOS4)

    return quantized


def overlay_edges(
    base_bgr: np.ndarray,
    edge_map: np.ndarray,
    line_color: tuple[int, int, int] = (0, 0, 0),
    opacity: float = 1.0,
) -> np.ndarray:
    """Overlay detected edges as colored lines (default black) on base image."""
    base = _validate_color_image(base_bgr)
    if edge_map.ndim != 2:
        raise ValueError("edge_map must be grayscale (H,W)")
    if edge_map.shape != base.shape[:2]:
        edge_map = cv2.resize(edge_map, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST)
    if opacity <= 0 or opacity > 1:
        raise ValueError("opacity must be in (0, 1]")

    _, binary_edges = cv2.threshold(edge_map, 127, 255, cv2.THRESH_BINARY)
    edge_mask = binary_edges > 0

    output = base.copy().astype(np.float32)
    color_arr = np.array(line_color, dtype=np.float32).reshape(1, 1, 3)
    output[edge_mask] = (output[edge_mask] * (1.0 - opacity)) + (color_arr.reshape(3) * opacity)
    return np.clip(output, 0, 255).astype(np.uint8)


def recommended_classic_params(intensity: IntensityLevel = "medium") -> ClassicCartoonParams:
    """Get preset parameters for light/medium/strong classic cartoon intensity."""
    if intensity not in CLASSIC_CARTOON_PRESETS:
        raise ValueError(f"Unsupported intensity: {intensity}")
    return CLASSIC_CARTOON_PRESETS[intensity]


def create_classic_cartoon(
    image: np.ndarray,
    intensity: IntensityLevel = "medium",
    edge_method: EdgeChoice = "auto",
) -> np.ndarray:
    """
    Create complete classic cartoon effect with bold black outlines.

    Pipeline:
    1) resize + denoise preprocessing
    2) bilateral smoothing + K-means color quantization
    3) edge detection (adaptive/Canny)
    4) black-line overlay on color-reduced base
    """
    source = _validate_color_image(image)
    preset = recommended_classic_params(intensity)
    working, (original_h, original_w) = preprocess_for_cartoon(
        source,
        resize_max_dim=preset.resize_max_dim,
        denoise_kernel=preset.pre_denoise_kernel,
    )

    base = create_base_cartoon_effect(working, preset.base)

    edge_params = preset.edges
    if edge_method != "auto":
        if edge_method == "canny":
            edge_params = EdgeParams(
                method="canny",
                canny_low=edge_params.canny_low if edge_params.method == "canny" else 70,
                canny_high=edge_params.canny_high if edge_params.method == "canny" else 150,
                median_blur_kernel=edge_params.median_blur_kernel,
                sensitivity=edge_params.sensitivity,
                edge_thickness=edge_params.edge_thickness,
                invert=False,
            )
        elif edge_method == "adaptive":
            edge_params = EdgeParams(
                method="adaptive",
                adaptive_block_size=edge_params.adaptive_block_size if edge_params.method == "adaptive" else 9,
                adaptive_c=edge_params.adaptive_c if edge_params.method == "adaptive" else 2,
                median_blur_kernel=edge_params.median_blur_kernel,
                sensitivity=edge_params.sensitivity,
                edge_thickness=edge_params.edge_thickness,
                invert=False,
            )
        else:
            raise ValueError(f"Unsupported edge_method: {edge_method}")

    edges = detect_cartoon_edges(working, edge_params)
    combined = overlay_edges(base, edges, line_color=(0, 0, 0), opacity=preset.edge_line_opacity)

    if combined.shape[:2] != (original_h, original_w):
        combined = cv2.resize(combined, (original_w, original_h), interpolation=cv2.INTER_LANCZOS4)
    return combined


def compare_original_and_cartoon(
    original_bgr: np.ndarray,
    cartoon_bgr: np.ndarray,
    label_original: str = "Original",
    label_cartoon: str = "Cartoon Base",
) -> np.ndarray:
    """Return labeled side-by-side comparison panel."""
    original = _validate_color_image(original_bgr)
    cartoon = _validate_color_image(cartoon_bgr)
    if cartoon.shape[:2] != original.shape[:2]:
        cartoon = cv2.resize(cartoon, (original.shape[1], original.shape[0]), interpolation=cv2.INTER_NEAREST)

    panel = np.hstack([original, cartoon])
    cv2.putText(panel, label_original, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(
        panel,
        label_cartoon,
        (original.shape[1] + 20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return panel


def profile_parameter_combinations(
    image: np.ndarray,
    parameter_sets: Iterable[CartoonParams],
    runs_per_setting: int = 2,
) -> list[dict[str, object]]:
    """Measure runtime for each parameter set and return sorted results."""
    image = _validate_color_image(image)
    if runs_per_setting < 1:
        raise ValueError("runs_per_setting must be >= 1")

    results: list[dict[str, object]] = []
    for params in parameter_sets:
        _validate_params(params)
        timings_ms: list[float] = []
        output_preview: np.ndarray | None = None

        for _ in range(runs_per_setting):
            start = perf_counter()
            output_preview = create_base_cartoon_effect(image, params)
            timings_ms.append((perf_counter() - start) * 1000.0)

        unique_colors = int(
            np.unique(output_preview.reshape(-1, 3), axis=0).shape[0] if output_preview is not None else 0
        )
        results.append(
            {
                "params": params,
                "avg_ms": float(np.mean(timings_ms)),
                "min_ms": float(np.min(timings_ms)),
                "max_ms": float(np.max(timings_ms)),
                "unique_colors": unique_colors,
            }
        )

    return sorted(results, key=lambda item: item["avg_ms"])


def create_classic_cartoon_from_path(
    image_path: str,
    intensity: IntensityLevel = "medium",
    edge_method: EdgeChoice = "auto",
) -> np.ndarray:
    """Convenience wrapper: load image from path and return classic cartoon result."""
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image from path: {image_path}")
    return create_classic_cartoon(image, intensity=intensity, edge_method=edge_method)


def benchmark_classic_cartoon(
    image: np.ndarray,
    intensity: IntensityLevel = "medium",
    edge_method: EdgeChoice = "auto",
    runs: int = 3,
) -> dict[str, float]:
    """Benchmark classic cartoon runtime (milliseconds)."""
    image = _validate_color_image(image)
    if runs < 1:
        raise ValueError("runs must be >= 1")

    timings: list[float] = []
    for _ in range(runs):
        start = perf_counter()
        _ = create_classic_cartoon(image, intensity=intensity, edge_method=edge_method)
        timings.append((perf_counter() - start) * 1000.0)
    return {
        "avg_ms": float(np.mean(timings)),
        "min_ms": float(np.min(timings)),
        "max_ms": float(np.max(timings)),
    }


def recommended_style_params(style: StyleName) -> CartoonParams:
    """Get tuned parameters for a named artistic style."""
    if style not in STYLE_PRESETS:
        raise ValueError(f"Unsupported style: {style}")
    return STYLE_PRESETS[style]["params"]


def documented_style_settings() -> dict[StyleName, dict[str, object]]:
    """Return style presets and rationale for documentation/presentation."""
    return {name: {"params": preset["params"], "notes": preset["notes"]} for name, preset in STYLE_PRESETS.items()}


def documented_classic_intensity_settings() -> dict[IntensityLevel, dict[str, object]]:
    """Return classic cartoon intensity presets for documentation/presentation."""
    return {
        intensity: {"params": params, "notes": f"{intensity.title()} intensity classic cartoon preset."}
        for intensity, params in CLASSIC_CARTOON_PRESETS.items()
    }