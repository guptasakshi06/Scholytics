# Local fictional development data

See [the dataset card](../docs/DATASET_CARD.md) for provenance, exact counts, generation, review coverage and limits. Everything in this pilot is fictional and development-only. The [S05 split](manifests/pilot.splits.jsonl) adds nested development train/validation/layout-diagnostic assignments while preserving the outer development-only role. No final test exists. See [classification and EDA](../docs/CLASSIFICATION.md).

From the repository root:

```bash
.venv/bin/python scripts/generate_pilot.py --output data/synthetic/pilot --seed 42
.venv/bin/python scripts/validate_dataset.py --manifest data/manifests/pilot.jsonl
```

- `synthetic/pilot/`: generated bulk media, ignored by Git; regenerate before validating.
- `manifests/pilot.jsonl` and `pilot.metadata.json`: portable sample/source/page provenance, seeds and hash inventory.
- `annotations/pilot/`: generated full-page text/selected-field references, all labelled provisional.
- `annotations/pilot_review.json`: separate hash-bound visual spot-check attestations; regeneration does not approve anything.
- `bundles/pilot/<scenario>/inputs.json`: input file inventory, explicit applicant profile and any unverified type hints.
- `bundles/pilot/<scenario>/expected.json`: provisional reference outcomes, prohibited as inference input.
- `private/`: ignored; no private applicant data was used or created.

The six small versioned media [fixtures](../tests/fixtures/pilot/README.md) are separate from generated bulk data. Never count a fixture copy, degraded variant, repeated bundle use or second PDF page as a new independent applicant/source. Changing a source or correcting a reference requires new hashes and explicit review; do not silently keep old approvals.
