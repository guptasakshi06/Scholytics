"""Original-image measurements; flags are uncalibrated hints, never readiness scores."""
import cv2
import numpy as np
from PIL import Image
from pydantic import Field

from .schemas import Contract, QualityAssessment


class QualityConfig(Contract):
    config_version: str = 'quality-1.0'
    dark_mean_below: float = Field(default=80., ge=0, le=255)
    low_contrast_std_below: float = Field(default=25., ge=0, le=128)
    low_laplacian_variance_below: float = Field(default=60., ge=0)
    small_short_side_below: int = Field(default=600, gt=0)


def measure(image: Image.Image, page_id: str, config: QualityConfig) -> QualityAssessment:
    gray = cv2.cvtColor(np.asarray(image.convert('RGB')), cv2.COLOR_RGB2GRAY)
    brightness, contrast = float(gray.mean()), float(gray.std())
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    flags = []
    if brightness < config.dark_mean_below:
        flags.append('dark_image_heuristic')
    if contrast < config.low_contrast_std_below:
        flags.append('low_contrast_or_sparse_content_heuristic')
    if blur < config.low_laplacian_variance_below:
        flags.append('low_edge_energy_blur_or_blank_heuristic')
    if min(image.size) < config.small_short_side_below:
        flags.append('small_pixel_dimensions_heuristic')
    return QualityAssessment(page_id=page_id, brightness=brightness, contrast=contrast,
        blur_measure=blur, width=image.width, height=image.height, heuristic_flags=flags,
        thresholds={k: float(v) for k, v in config.model_dump().items()
                    if k not in {'schema_version', 'config_version'}}, config_version=config.config_version)
