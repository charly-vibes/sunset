---
id: document.space.layer
kind: intent
statement: "THE DSC substrate SHALL represent stable source locators and spatial predicates relative to explicit coordinate frames, independent of transient rendering and OCR."
---

## Constraints
| id | kind | expr | traces_to |
|---|---|---|---|
| carrier_coordinate_frames | invariant | `Each geometric observation identifies carrier, source identifier, coordinate frame and units or a stable nongeometric selector.` | [[document.space.layer]] |
| frame_compatibility | invariant | `Spatial predicates operate only on compatible frames or with an explicit pinned transform; otherwise return unknown with reason.` | [[document.space.layer]] |
| geometry_transform | invariant | `When an invertible view transform is available, source geometry transformed forward and back is equivalent under a declared numeric tolerance.` | [[document.space.layer]] |
| epub_stable_identity | invariant | `EPUB logical location is identified by spine resource and stable selector; viewport XY never provides persistent element identity.` | [[document.space.layer]] |
| mixed_observations | invariant | `Native PDF text, vector, raster and OCR observations may coexist with separately declared origin and evidence.` | [[document.space.layer]] |
| spatial_order_separation | invariant | `No above/left-of/overlap relation automatically implies reading order or containment.` | [[document.space.layer]] |

## Model
### States
- `located`
- `source_declared`
- `spatial_evaluated`
- `spatial_unknown`

### Transitions
| id | from | to | guard |
|---|---|---|---|
| locate | source_declared | located | `typed locator resolves in declared frame` [[document.space.layer.carrier_coordinate_frames]] |
| compare | located | spatial_evaluated | `frames compatible or transformed` [[document.space.layer.frame_compatibility]] [[document.space.layer.geometry_transform]] [[document.categorical.model.layer.conditional_equivalence]] |
| unknown | located | spatial_unknown | `incomparable or absent frames` [[document.space.layer.frame_compatibility]] [[document.space.layer.epub_stable_identity]] |

## Properties
| id | kind | derives_from | generator | predicate |
|---|---|---|---|---|
| pdf_rotation | unit | [[document.space.layer.carrier_coordinate_frames]] | `page_box_rotation_90()` | `normalized source locus matches expected transformed geometry` |
| cross_page_unknown | unit | [[document.space.layer.frame_compatibility]] | `two_regions_on_different_pages()` | `above returns unknown` |
| epub_reflow | unit | [[document.space.layer.epub_stable_identity]] | `same_epub_section_two_viewports()` | `stable selector unchanged while XY may differ` |
| native_ocr_coexist | unit | [[document.space.layer.mixed_observations]] | `hybrid_pdf_page()` | `native and OCR observations coexist without forced equality` |
| spatial_not_order | unit | [[document.space.layer.spatial_order_separation]] | `overlapping_figure_caption()` | `no precedes inferred` |
| roundtrip_transform | unit | [[document.space.layer.geometry_transform]] | `rotated_page_forward_back()` | `forward then inverse transform returns the original source locus within the declared numeric tolerance` |
| no_spatial_reading_order | unit | [[document.space.layer.spatial_order_separation]] | `two_column_layout_fixture()` | `above/left-of/overlap never emit a precedes or contains edge` |
