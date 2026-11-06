# ScholarReady viva notes

Prepared for Sakshi Gupta and Jigisha Baiswar, Project 042. Both students should be able to explain the full pipeline. These are learning notes and prompts, not evidence of completed student review or mastery. The report and slides retain Codex assistance and the unknown administrative fields.

## A one minute explanation

ScholarReady reads local printed-English images and PDFs. It measures original image quality, runs an explicit image-processing branch, and obtains real Tesseract text and token boxes. A document classifier selects field rules. Spatial anchors extract values with their roles, units and evidence. A fictional JSON checklist reports satisfied, missing, unreadable, review or not-applicable items. The same pipeline produces CLI, evaluation and Streamlit results. Readiness is separate from authenticity, eligibility and scholarship approval.

The central finding is that full C preprocessing increased OCR errors on the small synthetic test. A/B/C produced 3/22/50 character edits over 14,900 characters. A learned improved the observed unsupported classification cases but did not improve extraction. All routes had zero observed false ready among 16 non-ready scenarios. Four applicant groups and related synthetic layouts limit what those counts establish.

## Image processing questions

**What does the original-image baseline mean?** Branch A uses the ingested image after common decoding, EXIF orientation, white alpha compositing and PDF rasterization. It adds no external branch-specific enhancement. Tesseract still performs its own internal processing. A is therefore a strong baseline, rather than a pipeline with no processing anywhere.

**How do Otsu and adaptive thresholds differ?** Otsu chooses one global threshold by separating the grayscale histogram into two classes. Adaptive thresholding derives a local threshold from each neighborhood. C uses a Gaussian-weighted neighborhood mean minus 15, with block size 31. Local processing can respond to uneven intensity but can also damage faint strokes or amplify artifacts. The comparison keeps OCR settings fixed.

**What is CLAHE?** Contrast Limited Adaptive Histogram Equalization redistributes intensities in local tiles and limits histogram amplification. C uses clip limit 2 and an 8 by 8 grid. It can make weak details visible, but it may also amplify noise or alter punctuation. The final experiment, rather than an attractive image, decides its measured benefit within this pipeline.

**Why median filtering?** A 3 by 3 median filter replaces the center pixel with the neighborhood median. It can suppress isolated noise but can erase fine dots and strokes. Gaussian filtering is implemented as an option but is not an extra frozen measured variant. Do not invent a Gaussian result.

**What do erosion, dilation, opening and closing do?** On white foreground ink, erosion shrinks the foreground and dilation expands it. Opening applies erosion then dilation. Closing applies dilation then erosion. ScholarReady inverts black document ink internally, applies opening then closing, then returns black ink. Kernel dimensions are height by width. Always state the foreground convention before explaining an effect.

**Why test identity and small kernels?** A 1 by 1 kernel is a control with no morphological change. Its agreement with no morphology checks the control. Fixed 1 by 2, 2 by 1 and 2 by 2 rectangles test sensitivity to stroke direction and scale. Even kernels can shift strokes under their anchor convention. Larger or darker strokes do not guarantee better OCR.

**What does deskew assume?** It assumes near-horizontal dark printed text on a light page. It searches row-projection sharpness over correction angles within ±6 degrees, in 0.25 degree increments, with evidence/gain gates. Blank, sparse or ambiguous pages can abstain. The same-size rotated canvas can crop edges. There is no perspective correction or arbitrary page-orientation solution.

**Which image owns an OCR box?** For B/C it is the processed image. The recorded 3 by 3 transform maps original ingested pixels to processed pixels. Map all box corners if changing coordinate spaces. A correct inverse matrix cannot reconstruct resampled or removed ink. PDF-point-to-raster conversion is separately recorded. The report appendix illustrates actual processed-coordinate token boxes.

**Does Laplacian variance prove readability?** No. Noise may increase it, while a blank page has little edge energy. Resolution, typography and page coverage influence the measurement. Brightness, standard deviation and Laplacian variance are raw indicators with heuristic flags, not calibrated quality probabilities or readiness scores.

## OCR and Data Science questions

**Why is Tesseract separate from pytesseract?** Tesseract is the executable and trained language data. Pytesseract is the Python wrapper. Installing the wrapper alone does not install the OCR engine. The verified engine is 5.3.4 with eng, OEM 3, PSM 3 and a 20 second page timeout. PDF input is rasterized at 300 DPI instead of extracting embedded text as an OCR shortcut.

**What are CER and WER?** They are edit distance divided by reference character or word count. For reference `cat` and prediction `cut`, one substitution gives CER 1/3 and WER 1/1. They count insertions and deletions too, and can exceed one. The frozen policy normalizes Unicode NFC, case and whitespace. Empty-reference rates are null while raw edits remain accounted for. A footer typo and a wrong amount may contribute similarly to OCR error but have different practical impact.

**What is TF-IDF?** It weights terms using their frequency within a document and rarity in the training corpus. The vocabulary and inverse-document frequencies are learned from training text. The saved pipeline then transforms new OCR using that fixed vocabulary. It must not learn vocabulary from final-test text.

**What does Logistic Regression do here?** It learns class weights from TF-IDF text features and estimates class scores using those weights. This is classification despite the word regression. The frozen model uses C=4, seed 2026, probability threshold 0.6 and top-two margin 0.2. C is the inverse regularization strength, so a larger C weakens regularization. Scores are uncalibrated. The original frozen model SHA256 is recorded in the handoff and metadata.

**What differs between other and uncertain?** Other is a label for observed unsupported document types. Uncertain is a decision state for inadequate or ambiguous evidence. Keywords abstain on four of eight test other pages. The learned route resolves those eight examples but does not guarantee rejection of every future unknown.

**What is macro-F1?** Calculate F1 per class, then average over the six fixed classes. This gives each class equal weight rather than each page. Unresolved outputs remain false negatives. Absent classes have zero F1 under the frozen convention, so a one-class breakdown needs its support context. Keyword macro-F1 is 0.944444 and learned A is 1.0 on this test, not a real-world guarantee.

**How do groups prevent leakage?** One original, its degraded versions, documents from the same applicant and reused bundle content are related. Splitting pages independently can teach the model near-duplicates of held-out items. ScholarReady uses connected groups and propagates one split to every related source/variant. The expanded train/validation/test split has 10/4/4 groups. The heavily inspected pilot stays development-only. A held-out template close to training templates provides narrow evidence.

**Why separate validation and final test?** Validation chooses settings before the test. S09 froze the choices and S10 recorded consumption before inference. Inspecting final results and choosing the no-threshold diagnostic as the replacement would make a post-test selection. A changed method needs development work and new confirmatory data. S12 recomputes original routes from saved OCR to check them, without claiming a new performance experiment.

## Extraction and readiness questions

**Why use spatial anchors?** A document can contain multiple names and dates. A bounded label-neighbor rule selects candidates with token geometry and retains raw text, normalized value, role, unit, page and box. A global first-date rule could choose date of birth when the required field is issue date. A guardian name belongs to a different role from the applicant.

**What counts as an exact field match?** Normalized value, unit and person role must agree with the reviewed reference. Every present target remains in the denominator, even if extraction fails. A/B/C have 161/153/158 exact matches of 164 present targets. Four unreadable income references are separate. True-type and predicted-type totals agree here because classification abstentions have no supported targets. They need not agree in general.

**Why keep null?** Null plus a reason preserves missing or uncertain information. Zero is a possible amount and must never be fabricated as a default. Monthly income remains monthly. Ambiguous dates and competing candidate values require review. Valid formatting cannot establish that OCR recognized the right number.

**How does category applicability work?** True requires the category item. False produces not_applicable and excludes it from completeness. Unknown produces needs_review and null completeness because the applicable denominator is unresolved. No implicit false value or guessed real scholarship policy is used.

**How is completeness calculated?** Multiply satisfied applicable items divided by applicable items by 100. In the demo, four of five gives 80%. The score cannot override unresolved required checks. Quality is separate. Mismatch can implicate all five items and give 0%, rather than merely removing the one mismatching income item.

**Why distinguish missing and unreadable?** Missing means a sufficiently resolved inventory supports absence. Unreadable means a relevant value cannot be resolved. An uncertain upload may be the required type, so claiming absence would be too strong. The S12 omitted-amount fixture gives needs_clearer_upload. The different S11 erased-content smoke fixture gives needs_review. Different evidence can legitimately lead to different conservative states.

**What is false ready?** Count reference non-ready applications predicted ready, divided by every reference non-ready application. Here the count is 0/16 in every route. It is not 0/24. The false-ready share among predicted-ready applications uses a different denominator. Empty denominators mean not estimable. Zero observed false ready may coexist with too many false unreadable or review results: kernel 2 by 2 agrees on only 18/24 headlines.

**Why can OCR metrics and readiness disagree?** A wrong optional course field can hurt exact extraction without changing the configured required subset. A correct OCR amount can fail a token-score heuristic and wrongly request a clearer upload. Thus CER, field correctness, classification, item states and headline outcomes measure different layers. The report includes all of them.

## Reproduction and honest contribution prompts

Read the [report and slides inventory](../output/README.md), [demo script](../output/demo/DEMO_SCRIPT.md), [reproduction guide](REPRODUCIBILITY.md), [error analysis](ERROR_ANALYSIS.md) and [contribution ledger](CONTRIBUTIONS.md). The S11 source/frozen-evidence package plus its separate Linux wheels supplies the executable study. S12 supplies the companion academic artifacts. A source-only checkout omits required ignored assets.

Both students should perform these exercises before claiming their own review:

1. Run the four-case demo, inspect the source images and explain each item state without reading an expected-result file.
2. Trace one field from OCR token box through normalization to the checklist. State the image coordinate space and person role.
3. Explain why C worsened OCR, why the diagnostic is not a new winner, and why all 12 ablations remain reported.
4. Calculate CER on a tiny edit example, completeness with true/false/unknown category, and the correct false-ready denominator.
5. Describe what smoke mode executes versus what saved-OCR final mode verifies. State that final test is permanently consumed.
6. Swap suggested learning roles and explain the other's modules. Record actual work, review dates and remaining questions in the contribution ledger.

Sakshi's proposed learning lead is DIP and geometry. Jigisha's is classification, extraction and rules. Both remain responsible for understanding every stage. No assignment is evidence of work already performed. Roll numbers, institution, supervisor, template, approved-title refinements and deadline remain NOT PROVIDED. Confirm them with the course before submission, and preserve all numerical evidence when adapting the format.
