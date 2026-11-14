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

# The relations of the law texts, as first written: describe() without arguments shows exactly these,
# so the committed extraction of the law (and its cached model calls) stays reproducible.
LAW_RELATIONS = dict(RELATIONS)

# Classes the manufacturer, guidance and company layers add.
LAYER_CLASSES = {
    "Machine": "A named machine or product of a manual: a robot arm, a safety laser scanner, a vehicle lift.",
    "ProtectiveDevice": "A device that detects people or stops the hazard: safety laser scanner, light curtain, guard.",
    "SafetyFunction": "A safety function of a machine or device (e.g. emergency stop, protective stop, joint speed limit).",
    "Integrator": "Who builds the machine into a complete application or cell and answers for the result.",
    "RoboticCell": "A robot with the machines it serves and the safeguarded space around them.",
    "Standard": "A technical standard a document names (e.g. EN ISO 10218-1, ISO 13855, EN 1493).",
    "Check": "A check, test, inspection or maintenance task that a document asks for.",
    "Register": "A register or record of checks and maintenance that must be kept.",
    "Quantity": "A value with its unit, as written (850 mm, 5 kg, 1,600 mm/s, 6 months).",
}
CLASSES.update(LAYER_CLASSES)

# What the manuals, the guidance documents and the company guidelines state that the law relations cannot hold.
LAYER_RELATIONS = {
    "hasReach": ("Machine", "Quantity", "the reach or working radius of a machine, with its unit"),
    "hasMaxPayload": ("Machine", "Quantity", "the maximum payload or rated load capacity of a machine, with its unit"),
    "isPartlyCompletedMachinery": ("Machine", "text",
                                   "that a machine is partly completed machinery (the words that say so)"),
    "hasDeclaration": ("Machine", "Document",
                       "the declaration that comes with a machine (of incorporation or of conformity) and the act or annex it follows"),
    "conformsToStandard": ("Machine", "Standard", "a standard or directive the machine is declared to conform to"),
    "putIntoServiceOnlyWhen": ("Machine", "text",
                               "the condition under which a machine may be put into service (e.g. only once integrated into a complete machine)"),
    "integratorResponsibleFor": ("Integrator", "text",
                                 "what the integrator or the user is responsible for when the machine is built into an application"),
    "hasSafetyFunction": ("Machine", "SafetyFunction", "a safety function of the machine, or how many it has and at which performance level"),
    "hasStoppingLimit": ("Machine", "Quantity", "a stopping time, stopping distance, response time or safety limit with its unit"),
    "minimumDistanceRule": ("ProtectiveDevice", "text",
                            "the formula or rule for the minimum distance between a protective device and the hazard"),
    "minimumDistanceParameter": ("ProtectiveDevice", "Quantity",
                                 "the value of one term of the minimum distance rule (approach speed, supplement, resolution limit)"),
    "protectiveFieldRange": ("ProtectiveDevice", "Quantity", "the range or size of the protective field, with its unit"),
    "requiresCheckAfter": ("Check", "text",
                           "what must be checked or verified again, and the change or event after which (value = the change or event)"),
    "requiresPeriodicCheck": ("Check", "duration",
                              "what must be checked, tested or maintained regularly, and how often (value = the interval)"),
    "safeguardedSpaceRule": ("RoboticCell", "text",
                             "how the protected space around a robotic cell is bounded and when it may be entered"),
    "mustKeepRegister": ("Employer", "Register", "a register or record that must be kept, and what goes into it"),
    "maintenanceRule": ("Check", "text", "who may carry out maintenance, on what basis, or what maintenance must respect"),
}
# Law relations the other layers also state (who checks, how often, who must do what, how long to keep a record).
SHARED_WITH_LAYERS = ("hasObligation", "verifiedBy", "hasTimeLimit", "retentionPeriod", "definedAs")
RELATIONS.update(LAYER_RELATIONS)


def describe(relations: dict | None = None) -> str:
    """The schema as the model sees it. Without arguments: the relations of the law texts."""
    lines = ["Relations (predicate: subject class -> value; what to copy):"]
    for name, (subject, value, what) in (LAW_RELATIONS if relations is None else relations).items():
        lines.append(f"- {name}: {subject} -> {value}; {what}")
    return "\n".join(lines)


def describe_layers() -> str:
    """The schema shown for manuals, guidance documents and company guidelines."""
    return describe(LAYER_RELATIONS | {name: LAW_RELATIONS[name] for name in SHARED_WITH_LAYERS})
