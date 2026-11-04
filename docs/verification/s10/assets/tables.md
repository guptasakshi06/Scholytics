# Generated final-test tables

Source: [original run metadata](run/run.json), [summary](run/summary.json), [provenance](provenance.json). Each variant links to its exact metric artifact. All rows use the same 52 pages / 24 sources / four applicant groups; synthetic only. Rates shown as percentages are rounded for display; JSON/CSV retain full values.

## OCR, classification and extraction

| Variant / route | Character edits / 14900 | CER % | Word edits / 2092 | WER % | Macro-F1 | Exact fields / 164 | Missing / wrong nonnull |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [A / keyword](run/A/keyword_metrics.json) | 3 | 0.0201 | 4 | 0.1912 | 0.944444 | 161 | 2 / 1 |
| [A / learned](run/A/learned_metrics.json) | 3 | 0.0201 | 4 | 0.1912 | 1.000000 | 161 | 2 / 1 |
| [B / keyword](run/B/keyword_metrics.json) | 22 | 0.1477 | 22 | 1.0516 | 0.944444 | 153 | 9 / 2 |
| [C / keyword](run/C/keyword_metrics.json) | 50 | 0.3356 | 46 | 2.1989 | 0.944444 | 158 | 6 / 0 |
| [C_no_deskew / keyword](run/C_no_deskew/keyword_metrics.json) | 37 | 0.2483 | 35 | 1.6730 | 0.944444 | 159 | 5 / 0 |
| [C_no_clahe / keyword](run/C_no_clahe/keyword_metrics.json) | 165 | 1.1074 | 110 | 5.2581 | 0.944444 | 160 | 3 / 1 |
| [C_no_filter / keyword](run/C_no_filter/keyword_metrics.json) | 35 | 0.2349 | 55 | 2.6291 | 0.944444 | 161 | 3 / 0 |
| [C_no_threshold_or_morphology / keyword](run/C_no_threshold_or_morphology/keyword_metrics.json) | 0 | 0.0000 | 0 | 0.0000 | 0.944444 | 164 | 0 / 0 |
| [C_no_morphology / keyword](run/C_no_morphology/keyword_metrics.json) | 50 | 0.3356 | 46 | 2.1989 | 0.944444 | 158 | 6 / 0 |
| [C_gray_only / keyword](run/C_gray_only/keyword_metrics.json) | 3 | 0.0201 | 4 | 0.1912 | 0.944444 | 161 | 2 / 1 |
| [C_kernel_1x2 / keyword](run/C_kernel_1x2/keyword_metrics.json) | 83 | 0.5570 | 84 | 4.0153 | 0.944444 | 158 | 6 / 0 |
| [C_kernel_2x1 / keyword](run/C_kernel_2x1/keyword_metrics.json) | 111 | 0.7450 | 88 | 4.2065 | 0.944444 | 158 | 5 / 1 |
| [C_kernel_2x2 / keyword](run/C_kernel_2x2/keyword_metrics.json) | 158 | 1.0604 | 124 | 5.9273 | 0.944444 | 142 | 19 / 3 |

Four unreadable-reference income amounts are separate from the 164 present targets. True-type and predicted-type exact counts agree on these data for all routes; full separate [per-field results](fields_per_type.csv) include states and support. This equality does not establish classification-independent extraction in general.

## Application and requirement outcomes

| Variant / route | Headlines / 24 | Item states / 120 | Completeness / 24 | Missing P / R / F1 | False ready / 16 | Predicted ready |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| A / keyword | 24 | 120 | 24 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 8 |
| A / learned | 24 | 120 | 24 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 8 |
| B / keyword | 22 | 117 | 22 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 6 |
| C / keyword | 24 | 120 | 24 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 8 |
| C_no_deskew / keyword | 24 | 120 | 24 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 8 |
| C_no_clahe / keyword | 24 | 120 | 24 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 8 |
| C_no_filter / keyword | 20 | 115 | 20 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 6 |
| C_no_threshold_or_morphology / keyword | 24 | 120 | 24 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 8 |
| C_no_morphology / keyword | 24 | 120 | 24 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 8 |
| C_gray_only / keyword | 24 | 120 | 24 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 8 |
| C_kernel_1x2 / keyword | 24 | 120 | 24 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 8 |
| C_kernel_2x1 / keyword | 24 | 120 | 24 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 8 |
| C_kernel_2x2 / keyword | 18 | 106 | 16 | 1.0000 / 1.0000 / 1.0000 | 0 / 16 | 4 |

All 120 items remain in the confirmed-missing binary accounting. Unreadable/review states are retained separately in the original confusion matrices; a zero false-ready count does not imply that all ready applications were accepted.

## Recorded timing

| Variant / route | Page batch s | OCR s | Preprocessing s | Cached bundle rules s |
| --- | ---: | ---: | ---: | ---: |
| A / keyword | 24.075 | 18.756 | 0.000 | 0.074 |
| A / learned | 24.075 | 18.756 | 0.000 | 0.126 |
| B / keyword | 21.940 | 14.245 | 1.590 | 0.078 |
| C / keyword | 27.428 | 14.523 | 6.634 | 0.095 |
| C_no_deskew / keyword | 24.798 | 14.390 | 4.199 | 0.092 |
| C_no_clahe / keyword | 27.350 | 14.974 | 5.877 | 0.100 |
| C_no_filter / keyword | 28.388 | 15.547 | 6.178 | 0.091 |
| C_no_threshold_or_morphology / keyword | 27.177 | 15.524 | 5.128 | 0.082 |
| C_no_morphology / keyword | 27.245 | 14.921 | 5.960 | 0.100 |
| C_gray_only / keyword | 22.378 | 15.216 | 0.829 | 0.092 |
| C_kernel_1x2 / keyword | 28.167 | 14.972 | 6.861 | 0.085 |
| C_kernel_2x1 / keyword | 28.601 | 15.122 | 7.080 | 0.132 |
| C_kernel_2x2 / keyword | 27.999 | 14.822 | 6.812 | 0.099 |

A learned uses the same measured A page inference, rather than another fresh page run. Page batches include ingestion/rendering, saving stages, quality, DIP, OCR and baseline downstream work; exclude model load/final JSON. Cached bundle rules exclude upload/OCR. Timings are observed once, with uncontrolled OS caching/scheduling; no speed superiority claim.

## Core layout and degradation support

| Route | Breakdown | Pages | Sources | Groups | Character edits | Exact / present fields |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A/keyword | layout_status: known | 39 | 18 | 3 | 3 | 120 / 123 |
| A/keyword | layout_status: reserved | 13 | 6 | 1 | 0 | 41 / 41 |
| A/keyword | degradation: clean | 24 | 24 | 4 | 0 | 76 / 76 |
| A/keyword | degradation: low_contrast | 12 | 12 | 4 | 0 | 38 / 38 |
| A/keyword | degradation: no_amount | 4 | 4 | 4 | 0 | 12 / 12 |
| A/keyword | degradation: rotation | 12 | 12 | 4 | 3 | 35 / 38 |
| A/learned | layout_status: known | 39 | 18 | 3 | 3 | 120 / 123 |
| A/learned | layout_status: reserved | 13 | 6 | 1 | 0 | 41 / 41 |
| A/learned | degradation: clean | 24 | 24 | 4 | 0 | 76 / 76 |
| A/learned | degradation: low_contrast | 12 | 12 | 4 | 0 | 38 / 38 |
| A/learned | degradation: no_amount | 4 | 4 | 4 | 0 | 12 / 12 |
| A/learned | degradation: rotation | 12 | 12 | 4 | 3 | 35 / 38 |
| B/keyword | layout_status: known | 39 | 18 | 3 | 21 | 115 / 123 |
| B/keyword | layout_status: reserved | 13 | 6 | 1 | 1 | 38 / 41 |
| B/keyword | degradation: clean | 24 | 24 | 4 | 0 | 75 / 76 |
| B/keyword | degradation: low_contrast | 12 | 12 | 4 | 0 | 37 / 38 |
| B/keyword | degradation: no_amount | 4 | 4 | 4 | 0 | 12 / 12 |
| B/keyword | degradation: rotation | 12 | 12 | 4 | 22 | 29 / 38 |
| C/keyword | layout_status: known | 39 | 18 | 3 | 44 | 118 / 123 |
| C/keyword | layout_status: reserved | 13 | 6 | 1 | 6 | 40 / 41 |
| C/keyword | degradation: clean | 24 | 24 | 4 | 0 | 76 / 76 |
| C/keyword | degradation: low_contrast | 12 | 12 | 4 | 24 | 37 / 38 |
| C/keyword | degradation: no_amount | 4 | 4 | 4 | 0 | 12 / 12 |
| C/keyword | degradation: rotation | 12 | 12 | 4 | 26 | 33 / 38 |

Breakdowns overlap across dimensions. Within each dimension the pages partition the same 52 items. All [breakdowns](breakdowns.json) include the fixed six-class metric; a stratum containing only income has macro-F1 1/6 even when every income prediction is correct, because absent classes have F1=0. Use its class supports rather than interpreting that as an overall collapse.

## Per-class classification and per-field extraction

[Per-class precision/recall/F1/support](classification_per_class.csv), [true-type and predicted-type per-field counts](fields_per_type.csv), [all page rows](pages.csv), [all bundle rows](bundles.csv), [all errors with evidence](errors.json), [figure source index](figure_index.json).
