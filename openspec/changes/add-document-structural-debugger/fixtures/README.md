# Fixtures and oracles to implement

All fixtures are specified, not asserted to exist. Do not distribute Ahira or third-party PDF/EPUB pages without checking rights.

| ID | Carrier | Mutation or oracle | Expected |
|---|---|---|---|
| native-pdf-rotated | Text-layer PDF | rotate/crop page | selectors remap to same region |
| native-epub-reflow | Reflowable EPUB | resize viewport | stable element/text identity |
| ahira-wrong-order | Scanned magazine | swap known article reading edges | oracle mismatch; witness |
| hybrid-two-origins | Native + image PDF | overlapping observations | distinct origins preserved |
| financial-sign-loss | Bank statement | remove spatial column info | cannot certify sign preservation |
| graph-cycle | Any | containment cycle | structural violation + cycle |
| missing-evidence | Any | unresolved source anchor | explicit unresolved |
| same-title-editions | PDF/EPUB | distinct actual editions | no implied equivalence |
| private-redaction | Statement | omit secret source bytes | nonreplayable unless alternative fixture |
