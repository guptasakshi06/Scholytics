"""Conservative JSON checklist over document evidence, shared by CLI/UI/evaluation."""
from collections import defaultdict
from datetime import date
from difflib import SequenceMatcher
import json
import re
import unicodedata

from .config import ScholarshipConfig, condition_applicability
from .schemas import ApplicantProfile, DocumentResult, RequirementResult

ENGINE_VERSION = 'requirements-s07-1.0'
NAME_RULE = 'name-comparison-s07-1.0'


def normalize_name(value: str) -> str:
    """Case/Unicode/spacing/punctuation only; no initials, reordering or spelling repair."""
    text = unicodedata.normalize('NFC', value).casefold()
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in text).split())


def _role(field):
    return 'applicant' if field.person_role in {'applicant', 'student'} else field.person_role


def _signature(field):
    value = (normalize_name(str(field.normalized_value)) if field.field_name in {
        'applicant_name', 'student_name', 'guardian_name'} else field.normalized_value)
    return json.dumps([value, field.unit, _role(field)], sort_keys=True, ensure_ascii=False)


def _failures(document):
    """Check underlying failure channels even when the caller forgot to promote them."""
    failures = list(document.errors)
    failures += [f'{p.page_id}: {e}' for p in document.processing for e in p.errors]
    failures += [f'{o.page_id}: {o.reason}' for o in document.ocr if o.status == 'error']
    return list(dict.fromkeys(failures))


def _constraint_passes(constraint, field):
    if constraint.kind == 'unit_equals':
        return field.unit == constraint.value
    if constraint.kind == 'format_regex':
        return re.fullmatch(constraint.value, str(field.normalized_value)) is not None
    try:
        raw = str(field.normalized_value)
        actual = date.fromisoformat(raw)
        if actual.isoformat() != raw:
            return False
        bound = date.fromisoformat(constraint.value)
        return actual >= bound if constraint.kind == 'date_on_or_after' else actual <= bound
    except ValueError:
        return False


def _name_findings(documents, profile):
    by_role = defaultdict(list)
    for d in documents:
        if d.prediction.decision != 'classified':
            continue
        for f in d.fields:
            if f.field_name in {'applicant_name', 'student_name', 'guardian_name'} and f.validation_state == 'valid':
                expected_role = 'guardian' if f.field_name == 'guardian_name' else 'applicant'
                if _role(f) == expected_role:
                    by_role[expected_role].append((d.document_id, normalize_name(str(f.normalized_value))))
    findings = defaultdict(list)
    for role, values in by_role.items():
        targets = {v for _, v in values}
        if role == 'applicant' and profile.expected_name:
            targets.add(normalize_name(profile.expected_name))
        if len(targets) > 1 or '' in targets:
            ordered = sorted(targets)
            similarity = max((SequenceMatcher(None, a, b, autojunk=False).ratio()
                              for i, a in enumerate(ordered) for b in ordered[i+1:]), default=0.)
            reason = (f'{role} name evidence differs after {NAME_RULE}; review required. '
                      f'Largest pairwise string similarity {similarity:.3f} is review-only, not identity evidence')
            for doc_id, _ in values:
                findings[doc_id].append(reason)
    return findings


def evaluate(config: ScholarshipConfig, profile: ApplicantProfile, documents: list[DocumentResult]):
    """Return requirement results, all issues, headline, completeness, explanation.

    Each uploaded file is a document; its pages were aggregated by extraction.
    Agreeing complete duplicates count once. Separate incomplete files are never
    spliced into a fictional complete certificate. Hints never resolve classification.
    """
    config = ScholarshipConfig.model_validate(config.model_dump(mode='json'))
    profile = ApplicantProfile.model_validate(profile.model_dump(mode='json'))
    documents = [DocumentResult.model_validate(d.model_dump(mode='json')) for d in documents]
    if len({d.document_id for d in documents}) != len(documents):
        raise ValueError('Duplicate document IDs; each upload needs a distinct occurrence ID')
    failures = {d.document_id: _failures(d) for d in documents}
    unresolved = [d for d in documents if d.prediction.decision != 'classified' or failures[d.document_id]]
    issues = [f'{d.document_id}: unresolved upload: {d.prediction.reason}; inspect or replace this upload'
              for d in unresolved]
    issues += [f'{d.document_id}: {error}; inspect or retry the failed input/page'
               for d in documents for error in failures[d.document_id]]
    names = _name_findings(documents, profile)
    issues += [f'{doc_id}: {reason}; check the labelled person and user-provided expected name'
               for doc_id, reasons in names.items() for reason in reasons]
    requirements = []
    for definition in config.requirements:
        applicable = condition_applicability(definition, profile)
        selected = [d for d in documents if d.prediction.decision == 'classified'
                    and d.prediction.document_type == definition.document_type]
        findings = []
        if applicable is None:
            state, reasons = 'needs_review', ['Applicability is unknown; set category_certificate_required explicitly']
        elif applicable is False:
            state, reasons = 'not_applicable', ['Explicit false profile attribute excludes this conditional item']
        elif not selected:
            hinted = [d for d in unresolved if d.declared_type_hint == definition.document_type]
            selected = hinted or unresolved
            if hinted:
                state, reasons = 'unreadable', ['User-declared type suggests a candidate; document type/fields remain unverified']
            elif unresolved:
                state, reasons = 'needs_review', ['Unresolved upload could satisfy this item; absence is not confirmed']
            else:
                state, reasons = 'missing', ['Resolved upload inventory contains no document of this type']
        else:
            for d in selected:
                if failures[d.document_id]:
                    findings.append(('needs_review', f'{d.document_id}: processing failure leaves evidence unresolved'))
                if d.document_id in names:
                    findings.extend(('needs_review', f'{d.document_id}: {reason}') for reason in names[d.document_id])
                fields = defaultdict(list)
                for f in d.fields:
                    fields[f.field_name].append(f)
                for name in definition.required_fields:
                    candidates = fields[name]
                    if not candidates:
                        findings.append(('unreadable', f'{d.document_id}: no evidence for required field {name}'))
                    if len(candidates) > 1:
                        findings.append(('needs_review', f'{d.document_id}: duplicate aggregate field {name}'))
                    for f in candidates:
                        if f.validation_state != 'valid':
                            state = 'needs_review' if f.validation_state in {'invalid', 'ambiguous', 'unsupported'} else 'unreadable'
                            findings.append((state, f'{d.document_id}: required {name} is {f.validation_state}: {f.reason}'))
                        elif name in {'applicant_name', 'student_name', 'guardian_name'}:
                            role = 'guardian' if name == 'guardian_name' else 'applicant'
                            if _role(f) != role or not normalize_name(str(f.normalized_value)):
                                findings.append(('needs_review', f'{d.document_id}: required {name} has unresolved/mismatched person role or empty name'))
                for constraint in definition.constraints:
                    for f in fields[constraint.field_name]:
                        if f.validation_state == 'valid' and not _constraint_passes(constraint, f):
                            findings.append(('needs_review', f'{d.document_id}: configured fictional {constraint.kind} failed for {constraint.field_name} (expected {constraint.value})'))
            # Compare all readable catalog evidence in duplicates, including optional fields;
            # optional missing/unreadable fields do not become additional requirements.
            signatures = defaultdict(set)
            for d in selected:
                for f in d.fields:
                    if f.validation_state == 'valid':
                        signatures[f.field_name].add(_signature(f))
            for name, values in signatures.items():
                if len(values) > 1:
                    findings.append(('needs_review', f'Conflicting duplicate evidence for {name}; retain all documents/pages for review'))
            state = ('needs_review' if any(s == 'needs_review' for s, _ in findings) else
                     'unreadable' if findings else 'satisfied')
            reasons = [r for _, r in findings] or [
                'Configured document and required fields satisfy all explicit fictional constraints'
                + ('; multiple agreeing complete uploads count as one requirement' if len(selected) > 1 else '')]
        requirements.append(RequirementResult(
            requirement_id=definition.requirement_id, state=state, reasons=list(dict.fromkeys(reasons)),
            actions=[] if state in {'satisfied', 'not_applicable'} else [definition.action],
            document_references=[d.document_id for d in selected],
            field_references=list(dict.fromkeys(f'{d.document_id}:{f.field_name}' for d in selected for f in d.fields
                if f.field_name in definition.required_fields or state == 'needs_review')),
            page_references=[p.page_id for d in selected for p in d.pages],
            applicable=applicable, included_in_denominator=applicable))
    issues += [f'{r.requirement_id}: {reason}; action: {action}' for r in requirements
               if r.state not in {'satisfied', 'not_applicable'} for reason in r.reasons for action in r.actions]
    applicable_items = [r for r in requirements if r.applicable is True]
    if not applicable_items:
        issues.append('No resolved applicable checklist items; configure at least one applicable item and review')
    states = {r.state for r in requirements}
    overall = ('needs_review' if unresolved or names or 'needs_review' in states or not applicable_items else
               'needs_clearer_upload' if 'unreadable' in states else 'incomplete' if 'missing' in states else 'ready')
    if any(r.applicable is None for r in requirements):
        completeness, explanation = None, 'Unknown conditional applicability; denominator is unresolved'
    elif not applicable_items:
        completeness, explanation = None, 'Empty applicable denominator; readiness cannot be established'
    else:
        satisfied = sum(r.state == 'satisfied' for r in applicable_items)
        completeness = 100. * satisfied / len(applicable_items)
        explanation = (f'100 * {satisfied} satisfied / {len(applicable_items)} resolved applicable named items; '
                       'not_applicable excluded; duplicates count once; quality and global unresolved issues are separate')
    return requirements, list(dict.fromkeys(issues)), overall, completeness, explanation
