# ScholarReady — Project 042 specification

Team: Sakshi Gupta and Jigisha Baiswar. Roll numbers, institution, final approved topic refinements, instructor feedback and final submission deadline are **NOT PROVIDED**. S01 was implemented with AI assistance; student review has not been recorded.

## Problem, objectives and scope

Applicants may upload incomplete, difficult-to-read or inconsistent supporting documents. The project aims to show which document requirements have usable evidence and which need action. It concerns document readiness only; it does not authenticate certificates, detect fraud, verify signatures, determine eligibility or award scholarships.

Planned inputs are local printed English JPG/PNG and image-rasterized PDFs, including multipage scans. Five supported types are marksheet, income, bonafide, domicile and category certificates; `other` is a separate unsupported-example label. The demonstration checklist is fictional and category applicability is an explicit user attribute. No paid API or external applicant-document upload belongs to the core workflow.

The research questions are whether declared DIP alternatives change OCR errors on the same samples, how downstream document/field/readiness errors propagate, and where uncertainty should prompt review. No positive improvement, accuracy threshold or real-world generalization is assumed.

## Architecture and present capability

```text
local image/PDF -> validated pages -> A/B/C pixel processing -> local Tesseract
  -> document classification -> evidence-linked field extraction
  -> configured requirements + uncertainty -> shared JSON -> CLI / Streamlit
```

S01 provides an isolated tested stack, schema/config validation, a foundation command, and a tiny renderer/OCR environment smoke. Document ingestion/analysis begins in S03; DIP alternatives in S04; learned classification in S05; full extraction in S06; full rules in S07; UI in S08. The smoke PDF is an environment fixture, not a pilot dataset or OCR evaluation.

A uses original ingested pixels, B grayscale + Otsu, and C a validation-chosen sequence of deskew/CLAHE/filtering/adaptive threshold/morphology. Paired comparisons keep OCR/settings/downstream policy fixed when isolating DIP. S10 reports measured CER/WER, macro-F1, field accuracy, requirement/outcome agreement, false-ready counts/denominator and scoped runtime in [the error analysis](ERROR_ANALYSIS.md). Source/applicant/variant/bundle reuse stays grouped; final test was protected until the S09 freeze and was consumed in S10. See [handoff](../HANDOFF.md) and [contracts](CONTRACTS.md).

## Course guideline mapping

The preserved [three-page source](reference/DIP_Course_Project_Guidelines_2026.pdf) is the course authority. This mapping follows the established handoff reading; it adds no new course requirements.

| Guideline expectation | Planned project evidence |
| --- | --- |
| Individual or two-student project, consistent topic/partner details | Named team, registration draft below; actual contributions recorded separately |
| Clear input/data source | Synthetic watermarked pages, provenance and review manifest in S02/S09 |
| Substantive DIP connection | Recorded algorithms/parameters and intermediate comparisons in S04/S10 |
| Baseline and alternative | A/B/C on identical held-out samples, neutral/negative effects included |
| Relevant AI/CV component | TF-IDF + Logistic Regression versus keyword baseline in S05 |
| Interpretable results and failure analysis | Token/field evidence, stage images, readiness issues, measured breakdowns in S06–S10 |
| Working reproducible implementation | Shared package/CLI, lock, setup checks; clean reproduction in S11 |
| Final report, presentation and member explanations | Verified results, demo, viva notes and honest contribution ledger in S12 |

Streamlit, this stack, the sprint count and dataset-size targets are project choices. The source lists a registration deadline of 18 October 2026; no final project deadline is supplied. Administrative confirmation does not block local coding.

## Registration draft — not submitted

Project ID: **042**. Title: **Scholarship Document Readiness and Missing-Requirement Detection using Digital Image Processing and Data Science**. Students: **Sakshi Gupta (roll number NOT PROVIDED)** and **Jigisha Baiswar (roll number NOT PROVIDED)**. Each student's separate form should use the same title/ID and accurate partner details if a form is still applicable. This is a draft for student use; no registration, contact or submission has occurred.

Proposed description: ScholarReady will process printed English scholarship-document images using digital image processing and local OCR, classify selected document types, extract evidence-linked fields and compare them with a fictional configurable checklist. Baselines and alternatives will be evaluated reproducibly with errors, uncertainty and limitations visible. It will assess document readiness only.

## Assumptions and limitations

The selected environment is CPython 3.12 on Ubuntu x86_64; Windows/macOS and other Python series are unverified. Synthetic data is the default; consented real examples are unavailable so far. Synthetic template success would not establish broad real-world reliability. Reference annotations remain separate from inference. Unknown conditions, missing evidence and component errors must never become fabricated values or confident ready decisions. Both students are expected to understand the whole pipeline, but no claim of student work, mastery or approval has been made.
