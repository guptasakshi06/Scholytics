# ScholarReady fictional datasets

S09 adds a separate frozen, source-reviewed test described below. The original pilot remains development-only and its historical review limits are unchanged.

## Original pilot: pilot-1.0

Created locally in S02, 2026-11-03 (Asia/Kolkata), by Codex with AI assistance. No real applicant documents, public certificate scans, official seals, IDs, consent claims or external generation services were used. Every clean page has the same `SYNTHETIC - FOR ACADEMIC DEMONSTRATION` header. The deliberate erased example retains that header. This is document-readiness development data, with no authenticity or scholarship-approval meaning.

## Reproduce and inspect

Run from `/home/ubuntu/Documents/ChatGPT/DIP_` after the [verified setup](../README.md):

```bash
.venv/bin/python scripts/generate_pilot.py --output data/synthetic/pilot --seed 42
.venv/bin/python scripts/validate_dataset.py --manifest data/manifests/pilot.jsonl
.venv/bin/python scripts/inspect_pilot.py --output docs/verification/s02
```

The generator overwrites its generated pilot media, annotations, bundle specifications and manifest. Keep manual corrections/review attestations separately, bound to hashes. Use `--root <temporary-directory>` to generate an isolated copy; paths inside saved files stay repository-relative. `--output` changes the media directory within that root. Negative seeds and output paths escaping the root are rejected. Bulk images are ignored by Git and must be regenerated after copying/cloning the repository. Generation used roughly 87 MiB of media before font embedding; actual final disk usage is recorded in the verification entry, not an installation requirement.

No OCR, model training or requirement evaluation occurs in these commands. Generation/reference tools may read reference data; future inference must accept only actual input images/PDFs and explicit user profile/hints. Reference `expected.json`, source/class labels and annotations must never supply predictions. The [input-only complete scenario](../data/bundles/pilot/complete/inputs.json) lists real local input files; its [expected reference](../data/bundles/pilot/complete/expected.json) is separate.

## Actual support

| Label | Distinct source documents | Clean pages | Derived pages | All samples |
| --- | ---: | ---: | ---: | ---: |
| marksheet | 5 | 6 | 24 | 30 |
| income_certificate | 5 | 5 | 21 | 26 |
| bonafide_certificate | 5 | 5 | 20 | 25 |
| domicile_certificate | 5 | 5 | 20 | 25 |
| category_certificate | 5 | 5 | 20 | 25 |
| other | 5 | 5 | 20 | 25 |
| Total | 30 | 31 | 125 | 156 |

There are **five fictional applicant groups**, not 156 statistically independent examples. Each applicant has six distinct source documents. `src-025.pdf` has two linked marksheet pages. Variants preserve the source document, applicant and clean-source page. Bundle reuse adds connections: the mismatch bundle joins applicants `fictional-04` and `fictional-05`. S05 joins all connected applicant/source/hash/file/input-bundle reuse into four components. The [development split](../data/manifests/pilot.splits.jsonl) keeps those components intact with nested train/validation/layout-diagnostic assignments; see [classification and EDA](CLASSIFICATION.md). No final test exists within the pilot. Every pilot record is `development_only` and this heavily inspected pilot must not become an untouched final test.

Two layout families occur in every class: `layout_a` puts labels and values on one line; `layout_b` puts bold labels above indented values. Clean-page counts are 19 and 12 respectively. These are simple academic layouts, not captured real forms. The five `other` sources are a library notice, bus timetable, laboratory notice, club agenda and reading-room notice. They do not represent all possible unsupported inputs.

The 155 distinct input files comprise 106 PNG, 37 JPEG and 12 PDFs (11 single-page, one two-page); page-level samples total 156. Source formats are 12 PNG, six JPEG and 12 PDF documents. All pixel references use 1200 x 1600 RGB pages; PDFs are 600 x 800 points, rendered by PDFium at 144 DPI. This smaller pilot rasterization is an explicit fixture setting; S03 ingestion's intended starting setting remains approximately 300 DPI and must record its actual dimensions/scale when comparing boxes.

## Generation and provenance

[The generator](../scripts/generate_pilot.py) uses manually specified fictional content for Aster, Birch, Clover, Dahlia and Elm, labelled guardian names, fictional colleges/regions, printed academic years, printed dates and modest illustrative annual-income values. Those values define no eligibility threshold. There are no student-provided names, IDs or personal documents. The source specification is deterministic; NumPy's `default_rng` supplies only synthetic noise. `pilot.metadata.json` records dataset/generator versions, seed, dependency versions, font hashes, manifest SHA256 and SHA256 of all 321 media/reference/bundle artifacts. The manifest's `source_hash` always refers to the clean input file (shared across its PDF pages), while the inventory also hashes derived inputs and annotations.

ReportLab's packaged Bitstream Vera regular/bold fonts are embedded for stable PDF appearance; font files are not fetched from the internet. Their [license](reference/BITSTREAM_VERA_LICENSE.txt) is preserved. The first standard-font build showed serif substitution with the second renderer, Poppler; the final embedded-font build was rendered and inspected with both PDFium and Poppler. The dependency lock remains unchanged. Byte reproducibility was checked by generating the entire final pilot twice in separate roots with seed 42 and comparing manifest bytes and all inventory hashes; this is evidence for the tested stack, not a promise across library/platform updates.

| Variant | Page count | Declared operation |
| --- | ---: | --- |
| clean | 31 | PDF source render or stored PNG/JPEG; clean JPEG quality 95, subsampling 0 |
| low_contrast | 31 | Per channel `clip(0.18 * pixel + 205, 0, 255)`, uint8 truncation |
| rotation | 31 | Seed-selected +4/-4 degrees, bicubic, white fill, fixed canvas; seed 42 yields -4 degrees on all pages |
| blur_noise | 31 | Pillow Gaussian blur radius 1.8 then independent Gaussian noise sigma 8 per RGB channel, clip and uint8 truncation |
| compression | 31 | JPEG quality 18, subsampling 2, same dimensions |
| erased_content | 1 | Income page below y=110 erased to white; explicit unreadable-inventory example |

Each variant starts from its clean raster rather than from another degradation. JPEG source variants start from the decoded stored JPEG. The seed formula is `base_seed + source_zero_based_index * 100 + source_page_index * 10 + variant_index`, with variant indices 1..5 in the table order after clean. Each record saves the actual seed and operation parameters. No variant creates a new independent source. A seed change changes noise/rotation, not the fixed fictional applicant specification.

## Reference format and review

[Dataset integrity contracts](../src/scholarready/dataset.py) extend the shared S01 contract deliberately. Every page has ordered complete reference text including synthetic/header/footer/page text, line boxes, and all selected fields in the class catalog. Present fields include raw text, normalized values, role, unit and value boxes. Unprinted fields are explicit `absent` with null values; erased fields are `unreadable` with null values. Annual income is an integer in INR/year; percentage is the printed decimal string; dates and academic years remain printed ISO-like strings. No amount/percentage is reconstructed. The continuation page has subject lines but no named target fields: per-page absence cannot be treated as whole-document absence.

Boxes are `[x, y, width, height]` with a top-left pixel origin in `<sample_id>:original_pixels`. They are conservative text-metric rectangles, not manually segmented ink masks. A 3 x 3 `source_to_sample` matrix maps clean 144-DPI column-vector coordinates into the uploaded sample. Rotation maps every box corner and takes its axis-aligned enclosing rectangle. All other variants use identity. A landmark test checks the rotation against actual moved pixels, and two rendered overlays were visually checked. These are reference boxes, not predicted OCR boxes.

`DatasetRecord.source_page_index` is an optional additive v1.0 field: when omitted it defaults semantically to `page_index`. S02 sets it explicitly. `page_index` indexes the actual input file: a PNG made from PDF page 2 has `page_index=1, source_page_index=2`. All PDF pages and source links are validated.

Every generated annotation and bundle expectation is labelled **provisional**. Separate [review attestations](../data/annotations/pilot_review.json) record Codex's visual reference checks, exact hashes and scope. **10/156 page references** received full-text/value/role/absence inspection (nine clean pages covering six labels, both layouts and a continuation, plus the erased page); **146/156 remain unreviewed at that level**. This does not imply that all boxes or degraded transcriptions were independently reviewed. A contact sheet covers all 31 clean pages for gross layout inspection, four degradation images were visually inspected, and two box overlays were checked. Review materials are in [S02 verification](verification/S02.md).

Method: read the rendered pixels, compare every visible line with `full_text`, compare visible selected values/person roles/units with annotations, and distinguish printed absence from erased content. This visual method is separate from the drawing specification; no production pipeline output is treated as truth. Regeneration never automatically approves references. A review attestation is stale if its hashes change. All **five bundle reference expectations remain provisional**, with their input inventories and intended reasoning inspectable; no complete independent bundle-reference approval or student sign-off is claimed. Before S09 freeze, independently review every item intended for final testing. No final-test evidence is supplied here.

## Named readiness scenarios

| Scenario directory under `data/bundles/pilot/` | Intended reference | Reason |
| --- | --- | --- |
| complete | ready | Five readable required types for Aster; category explicitly true |
| missing_document | incomplete, income missing | Four known readable types for Birch; no income upload |
| conditional_not_applicable | ready, category not_applicable | Four mandatory types for Clover; category explicitly false |
| unreadable | needs_clearer_upload, income unreadable | Erased income upload with explicit unverified user type hint; needs_review is a conservative alternative |
| mismatch | needs_review | Elm income name conflicts with Dahlia profile/other applicant-role evidence |

These are manually specified expected behaviors for the fictional config, not measured model outputs. The erased fixture must never become ready or confidently missing; the hint establishes only a user-declared candidate type. The mismatch intentionally reuses a different applicant's source and retains that true source applicant in the manifest. Guardian names are never compared as if they were applicant names. Conditional unknown, conflicting duplicates and broader failure cases are still S07 work.

## Limits, intended use and learning

Use this pilot for local smoke checks, pipeline debugging and development-only comparisons. Repeated templates, only five applicant groups, one English font family, little semantic diversity, fixed source resolutions, uniform synthetic header and narrow `other` coverage severely limit generalization. Layout is correlated with applicant and source format. Repeated class-specific content is ordinary document text; grouping metadata, filenames, reference text/labels and generator choices are forbidden model features. This validator's registered fictional-name and contact/long-number guard is a narrow project check, not a general PII detector or a guarantee for arbitrary files. No real-world accuracy, statistical significance, readiness performance or authenticity claim is supported.

Both students' review exercise: compare a source with its noisy variant and explain why they must share a split; locate the guardian versus applicant boxes; explain why page 2 alone cannot prove missing required fields; open `inputs.json` and `expected.json` and explain why only the former supplies inference inputs. Sakshi can focus on degradation and transforms, Jigisha on full transcriptions, roles and provisional labels; both should explain the entire boundary. These are learning prompts, not completed student contributions.


## S09 expansion: expanded-s09-1.0

Created locally on 2026-11-04 by Codex, with no real documents or external generation. The [generator](../scripts/generate_expanded.py) creates108 distinct filled source documents for18 fictional applicants, six labels each. There are108 clean pages,54 rotated pages (deterministic ±4 degrees),54 low-contrast pages (same0.18 scale/+205 operation as the pilot) and18 income derivatives with the complete amount label/value erased: **234 pages**,126 derived. There are36 source PNGs,36 JPEGs (quality95/subsampling0) and36 single-page PDFs. Derivatives are PNGs. Source references render PDF geometry at144DPI; runtime PDFs use300DPI. Vera regular/bold font hashes are preserved; all pages retain the same synthetic header and no official seal/identifier.

This gives **138 total sources /139 clean pages /390 total samples** across pilot and expansion, not390 independent documents. New applicant names, institutions, dates, years, amounts, totals and percentages vary. Four layout families use left/indented inline and left/right stacked fields; three are known during training, and one right-stacked family is test-only. A single font family and closely related template structure remain strong limitations. Unsupported sources include library/bus notices, fee receipts, event posters and course timetables with distinct activity themes. This is limited synthetic diversity, not a broad unknown-document benchmark. No final-test multipage or real-image benchmark exists.

| New partition | Groups | Sources / clean pages | Derived pages | Total pages | Bundles |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 10 | 60 | 70 | 130 | 60 |
| Validation | 4 | 24 | 28 | 52 | 24 |
| Test | 4 | 24 | 28 | 52 | 24 |

Applicant/source/hash/file/input-bundle connected grouping is checked before tuning. All original pilot samples remain excluded from this experiment. Partitions were predeclared by new applicant indices; review does not choose easy pages from production output. Exact/full-text and near-duplicate diagnostics are recorded in [review diagnostics](verification/s09/source_review_final/duplicates.json), with cross-pilot comparison in [acceptance](verification/s09/acceptance.json). The initially repeated notices failed grouping and were repaired before tuning. Many sparse-paper pixel candidates persist because templates repeat; all have different visible filled content and remain an explicit known-layout dependence. This does not justify treating documents/pages/bundles as independent population observations.

Six scenarios per applicant are complete, missing income, category false, category unknown, profile expected-name mismatch and no readable amount. Inventories and expectations are separate. There are108 correlated scenario specifications, including24 final-test applications (four applicant groups); expected outcomes are manually specified from the written fictional checklist, never production answers. They benchmark readiness, not authenticity or eligibility. Unsupported sources are used in page classification; these new bundle scenarios do not measure arbitrary unknown replacements, conflicts, corrupt inputs or rotated bundles.

**Review:** Codex opened all24 test-source sheets and read all52 test pages (including every low-contrast/rotation/no-amount derivative), checked full text/class/selected values/role/unit against the annotation and separately inspected24 actual test inventories/profiles/expectations. The [hash-bound attestation](../data/annotations/expanded_review.json) records concrete observed values, method, source-sheet hashes and scope. It is a separate same-agent inspection pass, not a second human reviewer or student sign-off. Box transforms/bounds are checked mechanically; no manually segmented-box evaluation is claimed. The182 train/validation pages and84 train/validation bundle expectations remain provisional. Only checked references enter final test; byte changes invalidate the attestation. No production final-test prediction or metric was generated in S09.

The smaller-than-target expansion allows full inspectable final-reference coverage in a bounded local study. Adding more deterministic filled forms would not by itself establish independent document-style diversity. There is no real data, calibration claim, population confidence interval or guaranteed false-ready bound. Consult [the exact frozen protocol](EVALUATION_PROTOCOL.md), [S09 checks](verification/S09.md), seed2026 and the recorded dependency/font hashes. Generation in a fresh destination is deterministic on the tested stack and was checked against687 artifact hashes in an isolated second root; it refuses existing media/annotation directories. Preserve the separately reviewed attestation rather than approving regenerated data automatically.


S10 evaluated the frozen expanded test without changing its data/review/splits: **final test consumed YES** on2026-11-04. See [measured analysis](ERROR_ANALYSIS.md), [S10 verification](verification/S10.md) and [consumption/run registry](verification/s10/run_registry.json). Original pilot/development roles and reference-review limitations remain unchanged.
