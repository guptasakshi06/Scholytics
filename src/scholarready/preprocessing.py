"""A identity, B grayscale/Otsu, C ordered configurable DIP; save every enabled stage."""
from pathlib import Path
from time import perf_counter
from typing import Literal, Self

import cv2
import numpy as np
from PIL import Image
from pydantic import Field, StrictBool, model_validator

from .geometry import estimate_skew, rotation_matrix
from .quality import QualityConfig
from .schemas import Contract, GeometricTransform, PageImage, ProcessingResult, ProcessingStage


class PreprocessingConfig(Contract):
    config_version: Literal['dip-1.0'] = 'dip-1.0'
    quality: QualityConfig = Field(default_factory=QualityConfig)
    deskew: StrictBool = True
    max_skew_degrees: float = Field(default=6., gt=0, le=10)
    skew_step_degrees: float = Field(default=.25, ge=.1, le=1)
    skew_min_gain: float = Field(default=1.05, ge=1.01, le=2)
    clahe: StrictBool = True
    clahe_clip_limit: float = Field(default=2., gt=0, le=10)
    clahe_grid: int = Field(default=8, ge=1, le=32)
    denoise: Literal['none', 'median', 'gaussian'] = 'median'
    filter_size: int = Field(default=3, ge=3, le=7)
    threshold: Literal['none', 'adaptive', 'otsu'] = 'adaptive'
    adaptive_block_size: int = Field(default=31, ge=3, le=101)
    adaptive_c: float = Field(default=15., ge=-50, le=50)
    morphology: Literal['none', 'open', 'close', 'open_close'] = 'open_close'
    kernel: list[int] = Field(default_factory=lambda: [1, 1], min_length=2, max_length=2)

    @model_validator(mode='after')
    def choices(self) -> Self:
        if self.filter_size % 2 == 0 or self.adaptive_block_size % 2 == 0:
            raise ValueError('filter_size and adaptive_block_size must be odd')
        if any(type(n) is not int or not 1 <= n <= 5 for n in self.kernel):
            raise ValueError('kernel is [height, width], each integer 1..5')
        if self.morphology != 'none' and self.threshold == 'none':
            raise ValueError('binary morphology requires a threshold stage; disable morphology too')
        return self


def load_preprocessing(path: Path | None = None) -> PreprocessingConfig:
    return PreprocessingConfig.model_validate_json(Path(path).read_text()) if path else PreprocessingConfig()


def morph(binary, operation: str, kernel: list[int]):
    """Black ink is inverted to white foreground; open then close when combined.

    Even kernels use the explicit OpenCV anchor (width//2,height//2). They may
    shift strokes; morphological pixel changes are not an invertible geometric warp.
    """
    if operation == 'none':
        return binary.copy()
    foreground = 255 - binary
    element = np.ones(tuple(kernel), dtype=np.uint8)
    anchor = (kernel[1] // 2, kernel[0] // 2)
    for op in (['open', 'close'] if operation == 'open_close' else [operation]):
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN if op == 'open' else cv2.MORPH_CLOSE,
            element, anchor=anchor, iterations=1, borderType=cv2.BORDER_CONSTANT, borderValue=0)
    return 255 - foreground


def process(page: PageImage, output: Path, branch: str, config: PreprocessingConfig) -> ProcessingResult:
    target = page.coordinate_space if branch == 'A' else f'{page.page_id}:{branch}:processed_pixels'
    matrix = np.eye(3)
    stages = [ProcessingStage(name='ingested_original', parameters={'enhancement': 'none',
        'exif_orientation': 'applied', 'alpha_background': 'white', 'pdf_dpi': page.rasterization_dpi},
        image_path=page.original_image_path, runtime_seconds=0.)]
    errors = []
    try:
        if branch not in {'A', 'B', 'C'}:
            raise ValueError('branch must be A/B/C')
        if branch != 'A':
            folder = output / 'stages' / page.page_id / branch
            folder.mkdir(parents=True, exist_ok=False)
            def stage(name, params, operation):
                nonlocal image
                started = perf_counter()
                image = operation(image)
                path = folder / f'{len(stages):02d}-{name}.png'
                Image.fromarray(image).save(path)
                stages.append(ProcessingStage(name=name, parameters=params,
                    image_path=path.relative_to(output).as_posix(), runtime_seconds=perf_counter() - started))
            with Image.open(output / page.original_image_path) as original:
                image = np.asarray(original.convert('RGB'))
            stage('grayscale', {'conversion': 'RGB2GRAY'}, lambda a: cv2.cvtColor(a, cv2.COLOR_RGB2GRAY))
            if branch == 'B':
                used = {}
                def otsu(a):
                    threshold, out = cv2.threshold(a, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                    used['selected_threshold'] = float(threshold)
                    return out
                stage('otsu', used, otsu)
            else:
                if config.deskew:
                    started = perf_counter()
                    estimate = estimate_skew(image, config.max_skew_degrees, config.skew_step_degrees, config.skew_min_gain)
                    estimate['estimation_seconds'] = perf_counter() - started
                    matrix = rotation_matrix(page.width, page.height, estimate['correction_degrees'])
                    stage('deskew', dict(estimate, interpolation='linear', canvas='same_size_white_border',
                        edge_crop_possible=True), lambda a: cv2.warpAffine(a, matrix[:2], (page.width, page.height),
                        flags=cv2.INTER_LINEAR, borderValue=255) if estimate['applied'] else a.copy())
                if config.clahe:
                    stage('clahe', {'clip_limit': config.clahe_clip_limit, 'tile_grid': config.clahe_grid},
                        lambda a: cv2.createCLAHE(config.clahe_clip_limit, (config.clahe_grid, config.clahe_grid)).apply(a))
                if config.denoise != 'none':
                    stage(config.denoise, {'size': config.filter_size}, lambda a: cv2.medianBlur(a, config.filter_size)
                        if config.denoise == 'median' else cv2.GaussianBlur(a, (config.filter_size, config.filter_size), 0))
                if config.threshold != 'none':
                    params = {'method': config.threshold}
                    def threshold(a):
                        if config.threshold == 'otsu':
                            value, out = cv2.threshold(a, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                            params['selected_threshold'] = float(value)
                            return out
                        block = min(config.adaptive_block_size, min(a.shape) if min(a.shape) % 2 else min(a.shape) - 1)
                        params.update(block_size=max(block, 0), c=config.adaptive_c, method='gaussian')
                        if block < 3:
                            params['fallback'] = 'otsu_for_tiny_page'
                            value, out = cv2.threshold(a, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                            params['selected_threshold'] = float(value)
                            return out
                        return cv2.adaptiveThreshold(a, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, config.adaptive_c)
                    stage(config.threshold, params, threshold)
                if config.morphology != 'none':
                    stage('morphology', {'operation': config.morphology, 'kernel_height_width': config.kernel,
                        'anchor_xy': [config.kernel[1] // 2, config.kernel[0] // 2], 'iterations': 1,
                        'foreground': 'white_ink_internal_black_ink_output', 'border_foreground': 0},
                        lambda a: morph(a, config.morphology, config.kernel))
    except (OSError, ValueError, cv2.error) as exc:
        errors.append(f'{type(exc).__name__}: {exc}')
    return ProcessingResult(page_id=page.page_id, branch_id=branch, stages=stages,
        width=page.width, height=page.height, transform=GeometricTransform(source_space=page.coordinate_space,
        target_space=target, matrix=matrix.tolist()), errors=errors)


def ocr_page(page: PageImage, processed: ProcessingResult) -> PageImage:
    """OCR adapter only: DocumentResult.pages always retain the true originals."""
    return page.model_copy(update=dict(original_image_path=processed.stages[-1].image_path,
        color_space=page.color_space if processed.branch_id == 'A' else 'L',
        coordinate_space=processed.transform.target_space, width=processed.width, height=processed.height))
