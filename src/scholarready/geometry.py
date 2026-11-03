"""Pixel-centre homogeneous coordinates, original -> processed; no perspective guesses."""
import cv2
import numpy as np


def rotation_matrix(width: int, height: int, degrees: float) -> np.ndarray:
    return np.vstack([cv2.getRotationMatrix2D(((width - 1) / 2, (height - 1) / 2), degrees, 1.), [0., 0., 1.]])


def map_points(points, matrix):
    points = np.asarray(points, dtype=float)
    homogeneous = np.column_stack([points, np.ones(len(points))]) @ np.asarray(matrix).T
    return homogeneous[:, :2] / homogeneous[:, 2:]


def estimate_skew(gray: np.ndarray, max_degrees: float = 6., step_degrees: float = .25,
                  min_gain: float = 1.05) -> dict:
    """Search projection sharpness on a bounded thumbnail; abstain on weak evidence.

    Output angle is the OpenCV CORRECTION, not the page's input rotation.
    This is a heuristic for near-horizontal dark printed text, not orientation detection.
    """
    result = dict(correction_degrees=0., candidate_degrees=0., applied=False,
                  reason='insufficient_text_evidence', score_gain=None)
    if min(gray.shape) < 50 or float(gray.std()) < 3:
        return result
    scale = min(1., 900 / max(gray.shape))
    thumb = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    _, ink = cv2.threshold(thumb, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    count, _, stats, _ = cv2.connectedComponentsWithStats(ink)
    letters = sum(2 <= s[4] <= ink.size * .02 for s in stats[1:])
    fraction = float(np.count_nonzero(ink) / ink.size)
    if count < 21 or letters < 20 or not .002 <= fraction <= .30:
        return result
    h, w = ink.shape
    angles = np.arange(-max_degrees, max_degrees + step_degrees / 2, step_degrees)
    angles = np.unique(np.append(angles, 0.))
    scores = []
    for angle in angles:
        rotated = cv2.warpAffine(ink, rotation_matrix(w, h, float(angle))[:2], (w, h),
                                flags=cv2.INTER_NEAREST, borderValue=0)
        projection = (rotated > 0).sum(axis=1).astype(float)
        scores.append(float(np.square(np.diff(projection)).sum()))
    best = int(np.argmax(scores))
    zero = scores[int(np.argmin(abs(angles)))]
    gain = scores[best] / max(zero, 1.)
    angle = float(angles[best])
    result.update(candidate_degrees=angle, score_gain=gain, reason='no_material_projection_gain')
    distant = [s for a, s in zip(angles, scores) if abs(a - angle) >= .75]
    if abs(angle) >= max_degrees - step_degrees / 2:
        result['reason'] = 'search_boundary_requires_review'
    elif abs(angle) >= step_degrees / 2 and gain >= min_gain and scores[best] > max(distant, default=0) * 1.015:
        result.update(correction_degrees=angle, applied=True, reason='projection_gain_heuristic')
    return result
