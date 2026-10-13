# Frozen DSC 0.2 validation limitations

The preserved `validator.py` implements the eleven supplied descriptor fixtures;
it is not a hardened validator for arbitrary inputs. This page records observed
limits without changing the research artifact or claiming 0.3 implementation.

## Malformed relation endpoints can crash

Replacing a relation's string endpoint with an array reaches a dictionary
membership operation before type validation. The result is an uncaught
`TypeError`, not the intended typed `invalid` outcome.

Reproduce from the repository root without modifying any fixture:

```bash
python3 -B - <<'PY'
import importlib.util
from pathlib import Path

root = Path('spec/document-model-specodelic-v3')
spec = importlib.util.spec_from_file_location('frozen', root / 'validator.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
descriptor = validator.load(root / 'fixtures/valid/two-regions.json')
descriptor['relations'][0]['from'] = []
try:
    print(validator.validate(descriptor))
except TypeError as error:
    print(type(error).__name__, str(error))
PY
```

The successor's [Validation outcome states](../../openspec/changes/add-dsc-03/specs/document-core/spec.md#requirement-validation-outcome-states)
requires field-type checks before lookups, stable error codes, and explicit
resource-limit reporting. Those requirements are not yet implemented.

## Text fidelity and format checks are limited

The baseline rejects decomposed text such as `U+0065 U+0301` with `not_nfc`.
The active 0.3 proposal permits exact text code points and records normalization
as a separate transform. Migrating existing normalized values cannot recover
original code points without access to source observations.

The baseline also accepts `source.format: "PDF"` although its written contract
requires a lowercase term. Passing baseline validation therefore does not prove
every written constraint. These are known limits, not an exhaustive audit.

## What passing checks establish

`PASS 11 descriptor fixtures` establishes only the supplied positive/negative
cases and valid-fixture canonical roundtrips. It does not establish total error
handling, real PDF/EPUB extraction, profile resolution or 0.3 conformance.
The research executable remains frozen; successor implementation is tracked
in Beads as `sunset-r68`.
