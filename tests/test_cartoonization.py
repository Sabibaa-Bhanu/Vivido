import cv2
import numpy as np

from utils.cartoonization import (
    CartoonParams,
    apply_bilateral_filter,
    benchmark_classic_cartoon,
    color_quantize_kmeans,
    compare_original_and_cartoon,
    create_classic_cartoon,
    create_base_cartoon_effect,
    documented_classic_intensity_settings,
    documented_style_settings,
    profile_parameter_combinations,
    recommended_classic_params,
    recommended_style_params,
)


def _sample_scene(width: int = 320, height: int = 240) -> np.ndarray:
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (210, 220, 235)
    cv2.rectangle(img, (25, 30), (150, 180), (50, 120, 190), -1)
    cv2.circle(img, (230, 100), 48, (80, 190, 110), -1)
    cv2.line(img, (0, height - 30), (width, height - 70), (35, 35, 35), 4)
    cv2.putText(img, "V", (140, 140), cv2.FONT_HERSHEY_SIMPLEX, 2, (20, 20, 20), 3, cv2.LINE_AA)
    return img


def _portrait_like(width: int = 320, height: int = 420) -> np.ndarray:
    img = np.full((height, width, 3), 215, dtype=np.uint8)
    cv2.circle(img, (width // 2, height // 3), 72, (170, 185, 215), -1)
    cv2.ellipse(img, (width // 2, int(height * 0.68)), (92, 118), 0, 0, 360, (145, 170, 200), -1)
    cv2.circle(img, (width // 2 - 22, height // 3 - 12), 8, (60, 60, 60), -1)
    cv2.circle(img, (width // 2 + 22, height // 3 - 12), 8, (60, 60, 60), -1)
    cv2.ellipse(img, (width // 2, height // 3 + 24), (24, 10), 0, 0, 180, (40, 40, 40), 2)
    return img


def _landscape_like(width: int = 520, height: int = 320) -> np.ndarray:
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (178, 208, 236)
    cv2.rectangle(img, (0, int(height * 0.58)), (width, height), (88, 165, 100), -1)
    cv2.line(img, (0, int(height * 0.58)), (width, int(height * 0.6)), (70, 120, 72), 4)
    cv2.circle(img, (int(width * 0.8), int(height * 0.2)), 30, (230, 240, 255), -1)
    cv2.polylines(img, [np.array([[40, 210], [120, 130], [205, 220]], dtype=np.int32)], False, (70, 70, 70), 4)
    return img


def _object_like(width: int = 360, height: int = 280) -> np.ndarray:
    img = np.full((height, width, 3), 238, dtype=np.uint8)
    cv2.rectangle(img, (95, 70), (270, 230), (60, 90, 170), -1)
    cv2.rectangle(img, (95, 70), (270, 230), (20, 25, 35), 4)
    cv2.circle(img, (182, 150), 28, (220, 220, 220), 3)
    cv2.line(img, (182, 70), (182, 230), (20, 25, 35), 2)
    return img


def test_bilateral_filter_preserves_shape_dtype():
    image = _sample_scene()
    out = apply_bilateral_filter(image, d=9, sigma_color=80.0, sigma_space=80.0, passes=2)
    assert out.shape == image.shape
    assert out.dtype == np.uint8


def test_color_quantization_reduces_palette():
    image = _sample_scene()
    quantized = color_quantize_kmeans(image, num_colors=8, attempts=2, sample_pixels=5000, random_seed=7)
    assert quantized.shape == image.shape
    assert quantized.dtype == np.uint8
    unique_colors = np.unique(quantized.reshape(-1, 3), axis=0).shape[0]
    assert unique_colors <= 8
    assert unique_colors >= 2


def test_create_base_cartoon_effect_runs_with_downsample_optimization():
    image = _sample_scene(420, 300)
    params = CartoonParams(
        num_colors=10,
        bilateral_d=9,
        bilateral_sigma_color=85.0,
        bilateral_sigma_space=85.0,
        bilateral_passes=2,
        downsample_scale=0.8,
        sample_pixels=6000,
    )
    cartoon = create_base_cartoon_effect(image, params)
    assert cartoon.shape == image.shape
    assert cartoon.dtype == np.uint8


def test_compare_original_and_cartoon_panel_shape():
    image = _sample_scene()
    cartoon = create_base_cartoon_effect(image, CartoonParams())
    panel = compare_original_and_cartoon(image, cartoon)
    assert panel.shape[0] == image.shape[0]
    assert panel.shape[1] == image.shape[1] * 2
    assert panel.shape[2] == 3


def test_style_presets_available_and_valid():
    docs = documented_style_settings()
    assert set(docs.keys()) == {"soft_paint", "classic_cartoon", "bold_poster", "comic_ink"}
    for style in docs:
        params = recommended_style_params(style)
        assert isinstance(params, CartoonParams)


def test_profile_parameter_combinations_returns_sorted_results():
    image = _sample_scene()
    variants = [
        CartoonParams(num_colors=8, bilateral_passes=1, sample_pixels=5000),
        CartoonParams(num_colors=12, bilateral_passes=2, sample_pixels=5000),
    ]
    results = profile_parameter_combinations(image, variants, runs_per_setting=1)
    assert len(results) == 2
    assert results[0]["avg_ms"] <= results[1]["avg_ms"]
    assert results[0]["unique_colors"] >= 1


def test_classic_cartoon_pipeline_runs_for_various_image_types():
    scenarios = [_portrait_like(), _landscape_like(), _object_like()]
    for image in scenarios:
        out = create_classic_cartoon(image, intensity="medium", edge_method="auto")
        assert out.shape == image.shape
        assert out.dtype == np.uint8
        assert int(np.count_nonzero(out)) > 0


def test_classic_intensity_settings_available():
    docs = documented_classic_intensity_settings()
    assert set(docs.keys()) == {"light", "medium", "strong"}
    medium = recommended_classic_params("medium")
    assert medium.base.num_colors >= 8


def test_classic_cartoon_performance_under_five_seconds_for_standard_image():
    image = _landscape_like(640, 480)
    stats = benchmark_classic_cartoon(image, intensity="medium", edge_method="auto", runs=1)
    assert stats["avg_ms"] < 5000.0
