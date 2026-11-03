# ScholarReady image methods (S04)

The shared pipeline runs local Tesseract on an explicitly selected A/B/C branch. The default remains **A**. These alternatives are experiments: the measured default C was worse on this selected development set. Neither visual sharpness nor a quality flag proves readability. No classifier was trained or final test consumed in S04.

## Original-image measurements

`quality.measure` runs on the ingested original, before branch-specific changes. Ingestion includes decoding, EXIF orientation, alpha-to-white compositing and PDF rasterization; it is not the untouched PDF byte stream. Brightness is mean OpenCV RGB-to-grayscale intensity (0–255), contrast is population standard deviation, and the blur indicator is population variance of a CV_64F Laplacian (default kernel size 1). Resolution is recorded as width/height in pixels; PDF DPI remains separately recorded in `PageImage`. JPEG DPI metadata does not establish physical scan resolution.

[The config](../configs/preprocessing.json) stores quality thresholds/version: mean below 80, standard deviation below 25, Laplacian variance below 60, short side below 600. These starting heuristics are **not calibrated probabilities or pass/fail document validators**. Blank/sparse white pages can have low contrast and edge energy; noise can raise the blur measure; measurements depend on resolution, font and page coverage. Flags name these ambiguities and never change checklist completeness or authorize `ready`. There is no combined quality percentage.

## Branches and exact order

| Branch | Enabled order | Default parameters |
| --- | --- | --- |
| A | ingested original -> OCR | no enhancement; image unchanged |
| B | original -> grayscale -> Otsu -> OCR | RGB2GRAY; global binary Otsu, selected threshold saved per page |
| C | original -> grayscale -> deskew -> CLAHE -> median -> adaptive threshold -> morphology -> OCR | settings below; stages can be disabled explicitly |

C defaults: skew search ±6° in 0.25° increments, gain floor 1.05; CLAHE clip 2 and 8×8 tiles; median 3×3; Gaussian adaptive threshold, block 31, C=15; opening then closing, **identity 1×1** kernel. C is a configurable alternative, not a promised improvement. Config validation rejects even filter/block sizes, invalid kernels and grayscale morphology without a threshold. The JSON snapshot is authoritative for each run. The CLI without `--preprocessing` uses the same validated `dip-1.0` defaults; pass the file explicitly when editing settings.

Otsu chooses one threshold from the gray histogram; it need not separate faint text under uneven lighting. Adaptive threshold compares pixels to a local weighted mean minus C; it can amplify noise and fragment faint strokes. The requested odd block size is capped to the page's smaller odd dimension. Pages smaller than 3 pixels use an explicitly recorded Otsu fallback. CLAHE limits local histogram amplification, but can amplify artifacts or change punctuation. Median removes impulse-like noise but can remove fine strokes; Gaussian is a selectable alternative with kernel size and OpenCV sigma=0. Each step also supports omission (`false` or `none`); grayscale is the common entry to B/C.

These definitions follow the upstream descriptions of [thresholding](https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html) and [CLAHE](https://docs.opencv.org/4.x/d5/daf/tutorial_py_histogram_equalization.html). Installed OpenCV headless 5.0.0.93 was exercised locally; upstream 4.x tutorial descriptions are algorithm references, not a claim that the installed version is 4.x. Tesseract also performs internal image processing; external DIP therefore need not help ([Tesseract guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)).

## Conservative skew and geometry

Deskew assumes near-horizontal dark text on a light background, not arbitrary camera orientation, perspective or an upside-down page. A thumbnail with maximum side 900 uses Otsu ink and component-count/ink-coverage checks. Pages under 50 pixels on either side, nearly constant pages (std <3), fewer than 20 plausible ink components, or ink coverage outside 0.2–30% abstain. These component tests are heuristics and do not identify letters semantically.

The estimator searches horizontal projection sharpness (sum of squared adjacent row-count differences) over correction rotations. It requires improvement over zero and a 1.5% margin over candidates at least 0.75° away; a boundary maximum abstains. It records candidate, applied correction, reason and score gain. Zero correction means no material evidence to rotate, not proof of an aligned/readable page. In the comparison only the -4° synthetic rotation received +4° correction; the erased low-text page abstained. Tests separately exercise ±2°/±4° known rotations, blank/random-noise/low-text cases.

The homogeneous 3×3 matrix maps **original ingested pixel coordinates to processed pixel coordinates**, using the pixel-center convention and center `((width-1)/2, (height-1)/2)`. It is the OpenCV rotation matrix extended with `[0,0,1]`. White fill and linear interpolation preserve the same canvas dimensions and processing pixel limits. **Edge content can be cropped**; this is recorded, and deskew can be disabled. No perspective correction was added. The [affine mapping reference](https://docs.opencv.org/4.x/d4/d61/tutorial_warp_affine.html) defines this mapping convention.

OCR and extracted evidence use the processed coordinate space for B/C; `DocumentResult.pages` retains originals. All current evidence overlays must use the last saved processed stage. Although inverse matrices are tested, S04 does not provide original-image box overlays or claim invertible restoration of resampled/morphologically changed ink. For a future box overlay, map all four corners and describe the polygon/enclosing-box approximation. Metadata for PDF points -> ingested originals remains separate.

## Morphology and damage

Binary input/output uses **black ink on white**. Internally ink is inverted to white foreground. Opening is erosion then dilation; closing is dilation then erosion. Combined mode applies **opening then closing**, once each. Kernel lists are **[height, width]**; explicit anchor is `(width//2,height//2)` with constant zero foreground border. Even kernels can shift strokes, which is a morphological pixel effect, not an extra geometric warp. The [OpenCV morphology description](https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html) explains the foreground convention and operations.

Identity 1×1 and no morphology are controls. Small 1×2/2×1/2×2 rectangles can remove dots, detach or join strokes. The [constructed pixel stress figure](verification/s04/morphology_harm.png) shows component counts 3 -> 2 (opening removes the dot), 3 -> 2 (closing joins strokes), and 3 -> 1 (combined). This is labelled educational synthetic evidence, not an OCR benchmark. [A real development crop](verification/s04/decimal_harm.png) shows low-contrast `72.5` read as `725` under C+2×2 while default C retains `72.5`. The image transform is identity on this page, allowing the same display crop; no annotation/ROI is used by inference.

## Paired experiment and ablations

See [S04 verification](verification/S04.md) for all results, exact commands, artifact hashes and acceptance mapping. All 12 variants use the same 14 selected provisional synthetic development pages, including two pages of a PDF, all six labels, the four degradation types and erased content. These are eight source documents/four applicant groups, not 14 independent samples. Tesseract 5.3.4, eng, OEM3, PSM3, 20-second timeout and 300-DPI PDF rendering are identical. All references are opened after every inference variant has returned. Protected train/validation/test roles are rejected by this development runner. Empty/failed predictions remain in denominators under the existing NFC/casefold/whitespace normalization.

The matrix is saved **before inference**: A, B, default C; C without deskew, CLAHE, filtering, threshold+mandatory binary morphology, morphology; C grayscale-only; C+1×2, C+2×1, C+2×2. Removing threshold also removes morphology because grayscale morphology would change the binary definition; this coupled ablation cannot isolate threshold alone. All other step-removal variants retain the explicit C order. No morphology and 1×1 are intentionally identical controls. Gaussian/alternate threshold choices are supported and tested, but are not extra measured variants. No per-page winner is selected using references.

A/B/C corpus CER is **0.0534% / 0.2404% / 0.4274%**; WER **0.3861% / 1.3514% / 2.8958%**. Grayscale-only has zero edits on this selected set. This is exploratory development evidence, not a selection/freeze for future test data, universal superiority or readiness accuracy. Default C can damage text despite its darker appearance; deskew helps alignment here without guaranteeing better OCR. No step is tuned after inspecting these results in S04.

Stage time includes the operation and PNG save. Deskew estimation has a separately recorded time, added in the comparison's preprocessing total. Quality, image loading/ingestion and orchestration are in end-to-end time, outside stage totals. OCR includes wrapper/image serialization. Final JSON writes/CLI discovery are excluded from pipeline end-to-end time. [Hardware/conditions](verification/s04/hardware.json) and all observed times are retained. Variants run sequentially without CPU/cache isolation; late variants overlap the test suite/verification. Do not interpret timing differences as a controlled speed ranking.

## Running and inspecting

```bash
.venv/bin/python -m scholarready demo --branch C --preprocessing configs/preprocessing.json --output artifacts/runs/my-C-demo
.venv/bin/python -m scholarready analyze --input tests/fixtures/pilot/src-025.pdf --branch B --output artifacts/runs/my-B-pdf
```

Use new output names. Per-run `settings.json`, `preprocessing.json`, `code_snapshot.json`, `metadata.json`, `result.json` and stage PNGs are linked by page/branch IDs. `metadata.config_hash` remains the canonical scholarship config hash; preprocessing has its separate complete JSON snapshot and comparison artifact SHA256 inventory. Development comparison JSONs and all stage-image hashes have compact preserved copies under `docs/verification/s04/runs/`; bulk images remain ignored under `artifacts/runs/` and can be regenerated.

Joint review: explain global versus adaptive thresholding; why blank and noisy images defeat simplistic blur scores; why a 1×1 control matters; the direction of the rotation matrix; why `72.5` -> `725` is more serious than a footer typo; and why synthetic development improvements cannot establish final-test performance. These are learning prompts, not claims of completed student review.
