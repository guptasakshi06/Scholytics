"""Minimal conservative checklist baseline shared by every caller (S03)."""
import re
from .config import ScholarshipConfig, condition_applicability
from .schemas import ApplicantProfile, DocumentResult, RequirementResult


def _name(value):
    return ' '.join(re.findall(r'\w+', str(value).casefold()))


def evaluate(config: ScholarshipConfig, profile: ApplicantProfile, documents: list[DocumentResult]):
    requirements = []
    unresolved = [d for d in documents if d.prediction.decision != 'classified']
    issues = [f'{d.document_id}: {d.prediction.reason}' for d in unresolved]
    issues += [error for d in documents for error in d.errors]
    # Only compare applicant/student role fields; guardian names never participate.
    names = { _name(f.normalized_value) for d in documents for f in d.fields
              if f.person_role in {'applicant', 'student'} and f.validation_state == 'valid' }
    if profile.expected_name and names and names != {_name(profile.expected_name)}:
        issues.append('Applicant name evidence differs from the user-provided expected name; review required')
    if len(names) > 1:
        issues.append('Applicant name evidence conflicts across documents; review required')
    for definition in config.requirements:
        applicable = condition_applicability(definition, profile)
        selected = [d for d in documents if d.prediction.document_type == definition.document_type]
        state, reasons = 'satisfied', ['Configured document and required label-anchored fields found']
        if applicable is None:
            state, reasons = 'needs_review', ['Category applicability is unknown; set the explicit profile attribute']
        elif applicable is False:
            state, reasons = 'not_applicable', ['Explicit profile attribute resolves this conditional item as not applicable']
        elif not selected:
            hinted = [d for d in unresolved if d.declared_type_hint == definition.document_type]
            if hinted:
                state, reasons = 'unreadable', ['User hint identifies a possible upload; its type/fields remain unverified']
                selected = hinted
            elif unresolved:
                state, reasons = 'needs_review', ['Unresolved upload could satisfy this item; absence is not confirmed']
                selected = unresolved
            else:
                state, reasons = 'missing', ['Resolved upload inventory has no document of this type']
        else:
            # Duplicate evidence requires manual review in this limited baseline.
            if len(selected) > 1:
                state, reasons = 'needs_review', ['Multiple documents of this type; baseline cannot resolve duplicates']
            else:
                fields = {f.field_name: f for f in selected[0].fields}
                bad = [name for name in definition.required_fields if name not in fields or fields[name].validation_state != 'valid']
                if bad:
                    state, reasons = 'unreadable', [f'Unresolved required field: {name}' for name in bad]
                    if any(name in fields and fields[name].validation_state in {'invalid', 'ambiguous'} for name in bad):
                        state = 'needs_review'
                for constraint in definition.constraints:
                    field = fields.get(constraint.field_name)
                    if field is None or field.validation_state != 'valid':
                        continue
                    matched = (field.unit == constraint.value if constraint.kind == 'unit_equals' else
                               re.fullmatch(constraint.value, str(field.normalized_value)) is not None)
                    if not matched:
                        state = 'needs_review'
                        reasons.append(f'Configured {constraint.kind} constraint failed for {constraint.field_name}')
        requirements.append(RequirementResult(
            requirement_id=definition.requirement_id, state=state, reasons=reasons,
            actions=[] if state in {'satisfied', 'not_applicable'} else [definition.action],
            document_references=[d.document_id for d in selected],
            field_references=[f'{d.document_id}:{f.field_name}' for d in selected for f in d.fields if f.field_name in definition.required_fields],
            page_references=[p.page_id for d in selected for p in d.pages],
            applicable=applicable, included_in_denominator=applicable))
    issues += [f'{r.requirement_id}: {reason}' for r in requirements
               if r.state not in {'satisfied', 'not_applicable'} for reason in r.reasons]
    if not requirements or not any(r.applicable for r in requirements):
        issues.append('No resolved applicable checklist items; readiness cannot be established')
    states = {r.state for r in requirements}
    # Unresolved inventory is always review, even if every required type is otherwise present.
    review = (unresolved or 'needs_review' in states or len(names) > 1
              or (profile.expected_name and names and names != {_name(profile.expected_name)})
              or not requirements or not any(r.applicable for r in requirements))
    overall = ('needs_review' if review else 'needs_clearer_upload' if 'unreadable' in states else
               'incomplete' if 'missing' in states else 'ready')
    applicable_items = [r for r in requirements if r.applicable]
    if any(r.applicable is None for r in requirements) or not applicable_items:
        completeness, explanation = None, 'Unknown applicability or empty applicable denominator'
    else:
        completeness = 100.0 * sum(r.state == 'satisfied' for r in applicable_items) / len(applicable_items)
        explanation = '100 * satisfied applicable document items / resolved applicable document items; independent of quality'
    return requirements, issues, overall, completeness, explanation
