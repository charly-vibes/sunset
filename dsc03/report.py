# Purpose: Four independent outcome reports for one descriptor run
#   (sunset-r68.8, tasks.md 3.3).
# Responsibilities: Assess a descriptor plus resolved profiles and produce
#   separate outcomes: (1) schema validity per dsc03.validator, (2) per-profile
#   resolution per dsc03.profiles, (3) source coverage per dsc03.coverage
#   (skipped when schema is invalid or a needed profile did not resolve), and
#   (4) interpretive assessment of annotations: supported stays supported,
#   disputed stays disputed, asserted_without_evidence maps to the external
#   report outcome "unverifiable". No aggregate implies preservation.
# Rationale: add-dsc-03 document-adapters "Partial results carry loss accounting"
#   and document-semantics "Source observations vs claims".
"""Separate schema / profile / source-coverage / interpretation reports."""


def assess(descriptor, resolved_profiles, registry, enumerator=None):
    """Run the four reports. Each is independent; coverage runs only when the
    schema is valid and the coverage-referenced profiles resolved."""
    reasons = validator_reasons(descriptor)
    schema = {"status": "valid" if not reasons else "invalid", "reasons": reasons}

    unresolved = [
        p["id"]
        for p in descriptor.get("profiles", [])
        if resolved_profiles.get(p["id"], ("unavailable", None))[0] != "resolved"
    ]
    prof_report = {
        "status": "resolved" if not unresolved else "unresolved_profiles",
        "unresolved": unresolved,
    }

    if schema["status"] != "valid":
        coverage = {"status": "skipped", "reasons": [], "summaries": {}, "source_coverage": "unexamined"}
        coverage["reasons"] = ["schema_invalid"]
    elif unresolved:
        coverage = {
            "status": "skipped",
            "reasons": ["unresolved_profile"],
            "summaries": {},
            "source_coverage": "unexamined",
        }
    else:
        from dsc03 import coverage as coverage_mod

        coverage = coverage_mod.verify(descriptor, resolved_profiles, enumerator)

    interpretation = interpret(descriptor)
    return {
        "schema": schema,
        "profiles": prof_report,
        "coverage": coverage,
        "interpretation": interpretation,
    }


def validator_reasons(descriptor):
    from dsc03 import validator

    try:
        return validator.validate(descriptor)
    except (validator.Duplicate, ValueError, UnicodeError) as e:
        return ["parse_error:" + str(e)]


def interpret(descriptor):
    """Report annotation-level interpretive outcomes. Schema validity never
    promotes a claim: supported requires evidence (validator-enforced), disputed
    stays disputed, and asserted_without_evidence is externally unverifiable."""
    by_annotation = {}
    counts = {"supported": 0, "disputed": 0, "unverifiable": 0}
    for a in descriptor.get("annotations", []):
        status = a.get("status")
        if status == "supported":
            outcome = "supported"
        elif status == "disputed":
            outcome = "disputed"
        else:  # asserted_without_evidence
            outcome = "unverifiable"
        by_annotation[a["id"]] = outcome
        counts[outcome] += 1
    return {"by_annotation": by_annotation, "counts": counts}
