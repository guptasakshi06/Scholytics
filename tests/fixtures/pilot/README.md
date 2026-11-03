# Small fictional pilot fixtures

Nine byte-for-byte copies from seed-42 `pilot-1.0`, retained for local smoke and later integration tests. These are development fixtures, with no held-out/final-test status. The rest of the generated media is ignored. [The inventory](inventory.json) binds each copy to its original relative path, sample IDs and SHA256; references are in the [pilot annotations](../../../data/annotations/pilot).

| File | Purpose |
| --- | --- |
| src-001.png | Clean inline-layout marksheet |
| src-002.png | Clean applicant/guardian/annual-income example |
| src-003.png | Clean bonafide document for the standalone CLI demo |
| src-004.png | Clean domicile document for the standalone CLI demo |
| src-005.png | Clean category document for the standalone CLI demo |
| src-007.jpg | JPEG marksheet with stacked label/value layout |
| src-014.pdf | Single-page income PDF |
| src-025.pdf | Two-page marksheet; page 2 supplements rather than repeats target fields |
| src-002-p01-erased_content.png | Unreadable upload with visible synthetic header |

Do not derive a class or readiness answer from these filenames. New runtime analysis must work on arbitrary user paths without reading reference files. Copies preserve their source/applicant grouping. Font notices are preserved in the [Bitstream Vera license](../../../docs/reference/BITSTREAM_VERA_LICENSE.txt). Only refresh fixture bytes/inventory after reviewing an intentional dataset change.

S03 adds copies 003–005 so `python -m scholarready demo` uses five versioned images without generating or reading references. Their hashes/group identities remain those of `pilot-1.0`; they are not new independent sources.
