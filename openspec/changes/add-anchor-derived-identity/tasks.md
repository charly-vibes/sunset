## 1. Audit and ruling

- [ ] 1.1 List every deployed requirement and validator rule that depends on array position in set-like sections; record findings in design.md
- [ ] 1.2 Decide Open Question 1 (additive vs 0.4) with the owner

## 2. Identity profile

- [x] 2.1 RED: two independent processes derive identical ids for identical anchors
- [x] 2.2 Implement anchor tuple, digest form and `identity` profile kind with pinned version and digest
- [x] 2.3 Collision detection with witness naming both tuples
- [x] 2.4 Validator: under the profile, reject ids that do not equal the derivation

## 3. Canonical order

- [x] 3.1 RED: permuting set-like arrays yields identical canonical bytes in reader A and reader B
- [x] 3.2 Implement ascending-id order in both independent readers without sharing code
- [x] 3.3 Roundtrip stability test (parse canonical → re-serialize → identical)

## 4. Geometry

- [x] 4.1 Quantized integer boxes with declared quantum and rounding rule
- [x] 4.2 Record quantization as an explicit transform with extractor version
- [x] 4.3 Replace tolerance-0 claim in space fixtures with an exact-integer property over real native boxes

## 5. Migration and adoption

- [x] 5.1 `migrate` emits relabel-table evidence; content values unchanged (test)
- [x] 5.2 `native` emits identity-profile descriptors; remove prefix-matching of annotations to pages (`digitization/native.py` `an{page}-`)
- [x] 5.3 Assembly: replace "left operand first" ordering with canonical order under the profile (enables the join-law tasks in define-document-composition-semantics)
- [x] 5.4 Re-run all fixture carriers; record byte-identity across two processes in docs/src/status.md as agent-executed
