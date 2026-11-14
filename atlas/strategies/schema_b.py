"""Owner: Core. The schema of strategy B: domain classes and typed relations.

Written from the design competency questions only (split == "design") and approved by a person.
The model never invents a relation: it fills these, or it reports an open point.
"""

CLASSES = {
    "Act": "A legal act: regulation, directive, decree, corrigendum.",
    "Provision": "An article, paragraph or annex point of an act.",
    "Machinery": "Machinery or a related product placed on the market or used at work.",
    "MachineryCategory": "A category of machinery listed in an annex (e.g. Annex I, Part A).",
    "SafetyComponent": "A component that fulfils a safety function and is placed on the market separately.",
    "ConformityProcedure": "A conformity assessment procedure or module (A, B, C, G, H; internal checks; type-examination).",
    "NotifiedBody": "A conformity assessment body notified to carry out a procedure.",
    "EconomicOperator": "Manufacturer, authorised representative, importer or distributor.",
    "Employer": "The employer who makes work equipment available to workers.",
    "EssentialRequirement": "An essential health and safety requirement of an annex.",
    "Risk": "A risk or hazard that a requirement addresses.",
    "ProtectiveMeasure": "A guard, protective device or other measure a requirement asks for.",
    "Document": "A document that must exist: declaration, instructions, technical documentation, record.",
    "PeriodicVerification": "A verification or check of work equipment that recurs or has a time limit.",
    "VerifyingBody": "The body that carries out a verification (e.g. INAIL, ASL, an authorised body).",
}

# predicate: (subject class, value class or datatype, what to copy from the text)
RELATIONS = {
    "requiresProcedure": ("MachineryCategory", "ConformityProcedure",
                          "the conformity assessment procedure(s) or module(s) that apply to a category of machinery"),
    "listedIn": ("MachineryCategory", "Provision",
                 "a category of machinery or safety component and the annex, part and point that lists it"),
    "appliesFrom": ("Act", "date", "the date from which an act or a provision applies"),
    "repealedFrom": ("Act", "date", "an act that is repealed and the date from which the repeal has effect"),
    "placingAllowedUntil": ("Machinery", "date",
                            "until when products conforming to an earlier act may still be placed on the market"),
    "retentionPeriod": ("Document", "duration", "for how long a document or record must be kept, and by whom"),
    "definedAs": ("Provision", "text", "a defined term and its definition"),
    "mustAccompany": ("Machinery", "Document", "what must accompany the machinery or product"),
    "hasObligation": ("EconomicOperator", "text", "an obligation of a manufacturer, importer, distributor or employer"),
    "becomesManufacturer": ("EconomicOperator", "text", "who is considered the manufacturer, and in which case"),
    "addressesRisk": ("EssentialRequirement", "Risk", "the risk a numbered essential requirement addresses"),
    "requiresMeasure": ("EssentialRequirement", "ProtectiveMeasure",
                        "the guard, protective device or measure a requirement asks for"),
    "verifiedBy": ("PeriodicVerification", "VerifyingBody", "who carries out a verification or check"),
    "hasTimeLimit": ("PeriodicVerification", "duration",
                     "the time limit or interval of a verification, check or request"),
}


def describe() -> str:
    """The schema as the model sees it."""
    lines = ["Relations (predicate: subject class -> value; what to copy):"]
    for name, (subject, value, what) in RELATIONS.items():
        lines.append(f"- {name}: {subject} -> {value}; {what}")
    return "\n".join(lines)
