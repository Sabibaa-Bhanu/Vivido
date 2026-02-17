import cv2
import numpy as np

from utils.edge_detection import (
    EdgeParams,
    compare_original_and_edges,
    detect_cartoon_edges,
    detect_edges_adaptive,
    detect_edges_canny,
    recommended_params,
)


def _portrait_like_image(width: int = 320, height: int = 420) -> np.ndarray:
    img = np.full((height, width, 3), 210, dtype=np.uint8)
    cv2.circle(img, (width // 2, height // 3), 70, (165, 180, 210), -1)
    cv2.ellipse(img, (width // 2, int(height * 0.66)), (95, 120), 0, 0, 360, (140, 165, 195), -1)
    cv2.circle(img, (width // 2 - 24, height // 3 - 10), 8, (60, 60, 60), -1)
    cv2.circle(img, (width // 2 + 24, height // 3 - 10), 8, (60, 60, 60), -1)
    cv2.ellipse(img, (width // 2, height // 3 + 25), (24, 12), 0, 0, 180, (55, 55, 55), 2)
    return img


def _landscape_like_image(width: int = 420, height: int = 260) -> np.ndarray:
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (180, 210, 235)
    cv2.rectangle(img, (0, int(height * 0.55)), (width, height), (90, 170, 100), -1)
    cv2.line(img, (0, int(height * 0.55)), (width, int(height * 0.58)), (75, 120, 70), 4)
    cv2.circle(img, (int(width * 0.82), int(height * 0.2)), 26, (230, 240, 255), -1)
    cv2.polylines(
        img,
        [np.array([[30, 150], [85, 85], [145, 155]], dtype=np.int32)],
        False,
        (80, 80, 80),
        3,
    )
    return img


def _object_like_image(width: int = 360, height: int = 300) -> np.ndarray:
    img = np.full((height, width, 3), 235, dtype=np.uint8)
    cv2.rectangle(img, (95, 90), (265, 235), (60, 90, 170), -1)
    cv2.rectangle(img, (95, 90), (265, 235), (25, 30, 40), 4)
    cv2.circle(img, (180, 162), 24, (220, 220, 220), 3)
    cv2.line(img, (180, 90), (180, 235), (25, 30, 40), 2)
    return img


def test_canny_edges_shape_and_type():
    image = _object_like_image()
    edges = detect_edges_canny(image, low_threshold=70, high_threshold=150)
    assert edges.ndim == 2
    assert edges.shape == image.shape[:2]
    assert edges.dtype == np.uint8
    assert int(edges.sum()) > 0


def test_adaptive_edges_shape_and_type():
    image = _portrait_like_image()
    edges = detect_edges_adaptive(image, block_size=9, c_value=2)
    assert edges.ndim == 2
    assert edges.shape == image.shape[:2]
    assert edges.dtype == np.uint8
    assert int(edges.sum()) > 0


def test_edge_thickness_increases_edge_pixels():
    image = _landscape_like_image()
    thin = detect_edges_canny(image, low_threshold=60, high_threshold=140, edge_thickness=1)
    thick = detect_edges_canny(image, low_threshold=60, high_threshold=140, edge_thickness=3)
    thin_pixels = int(np.count_nonzero(thin))
    thick_pixels = int(np.count_nonzero(thick))
    assert thick_pixels >= thin_pixels


def test_sensitivity_detects_more_edges_when_higher():
    image = _landscape_like_image()
    low_sens = detect_edges_canny(image, low_threshold=80, high_threshold=180, sensitivity=0.8)
    high_sens = detect_edges_canny(image, low_threshold=80, high_threshold=180, sensitivity=1.4)
    assert int(np.count_nonzero(high_sens)) >= int(np.count_nonzero(low_sens))


def test_compare_original_and_edges_returns_side_by_side_panel():
    image = _portrait_like_image()
    edges = detect_edges_canny(image, low_threshold=70, high_threshold=150)
    panel = compare_original_and_edges(image, edges)
    assert panel.shape[0] == image.shape[0]
    assert panel.shape[1] == image.shape[1] * 2
    assert panel.shape[2] == 3


def test_recommended_presets_work_for_multiple_image_types():
    scenarios = [
        (_portrait_like_image(), "portrait"),
        (_landscape_like_image(), "landscape"),
        (_object_like_image(), "object"),
    ]
    for image, image_type in scenarios:
        params = recommended_params(image_type)
        edges = detect_cartoon_edges(image, params)
        assert edges.shape == image.shape[:2]
        assert int(np.count_nonzero(edges)) > 0
        panel = compare_original_and_edges(image, edges)
        assert panel.shape[1] == image.shape[1] * 2


def test_dispatcher_respects_method():
    image = _object_like_image()
    canny_edges = detect_cartoon_edges(
        image,
        EdgeParams(method="canny", canny_low=70, canny_high=140, median_blur_kernel=5),
    )
    adaptive_edges = detect_cartoon_edges(
        image,
        EdgeParams(method="adaptive", adaptive_block_size=9, adaptive_c=2, median_blur_kernel=5),
    )
    assert canny_edges.shape == adaptive_edges.shape == image.shape[:2]
    assert int(np.abs(canny_edges.astype(np.int16) - adaptive_edges.astype(np.int16)).sum()) > 0

