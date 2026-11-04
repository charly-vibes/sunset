# Native PDF extraction baseline

## Test shape before implementation

Use a generated two-page PDF with known text and geometry. Invoke the public
command in fresh processes twice into different directories. Assert exact text,
page/word mappings, identical semantic digests, valid DSC and inspectable artifacts.
Negative cases cover invalid page selection, existing output, malformed/encrypted
input, scanned and blank pages, mixed native/image content, rotation and Unicode.

## Decisions

- Extend the existing Python workflow. Assess reuse of `describe_pdf`, frame
  transforms, DSC selectors/profiles, source inventories, search mappings and
  inspection integrity validation before adding abstractions. The current
  page-text adapter alone does not satisfy the word-location contract.
- Require source and a new output directory; default to all pages and a documented
  native extraction profile. Optional page selection uses one-based PDF indices.
  No hand-authored recognition configuration is required. The lead selected `python3 -m digitization native --source PDF --output NEW_DIR`
  with optional `--pages 2,3`. Keep this proposed syntax out of the current-command
  quickstart until its fresh-process acceptance test passes.
- Pin effective configuration, extractor and dependency versions. Reuse existing
  page-frame conventions and register geometry/offset profiles through existing
  mechanisms. Coordinates are page points, top-left origin, x-right/y-down, with
  rotation and source-to-frame transforms explicit. Boxes bound words; line
  grouping is extractor-produced structure, not an inferred reading-order truth.
- Retain extractor-returned raw Unicode and whitespace before normalization.
  Search offsets are half-open Unicode code-point ranges. Map every search token
  to its raw span and word box(es); retain line grouping and transformations.
- Keep descriptor, raw/search text, source maps and pinned profiles/configuration
  as the semantic artifact set. Their hashes and selected source pages define
  the semantic digest. Run IDs, paths, timestamps and timing belong in the run
  envelope and cannot affect semantic IDs or artifact bytes. Record the format
  version and equality scope in the manifest.
- Use native extraction only. Scanned or textless pages remain explicitly
  unresolved/unexamined; empty text never proves a page blank. Images and other
  unsupported features retain scoped coverage/loss declarations even on pages
  with native text. No hidden OCR fallback or visual-completeness claim.

## Boundaries

Court, party, case-number and other semantic field extraction are later consumers
that can cite these mappings. OCR configuration gates apply to the scanned pilot,
not this local native route. Packaging, installation and distribution are separate.
Existing digitization operations and recorded-input behavior must keep working.
