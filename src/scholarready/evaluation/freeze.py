"""Hash-bound experiment selection and grouped integrity. No inference on import."""
from collections import Counter, defaultdict
import json
from pathlib import Path

from ..dataset import PageAnnotation, resolve_inside, sha256
from ..schemas import SplitRecord
from ..splitting import context


def audit_dataset(root, manifest, splits_path, review=None):
    records, metadata, groups, bundle_hashes = context(manifest, root)
    splits=[SplitRecord.model_validate_json(l) for l in splits_path.read_text().splitlines()]
    if len(splits)!=len(records) or len({s.sample_id for s in splits})!=len(splits) or {s.sample_id for s in splits}!={r.sample_id for r in records}:
        raise ValueError('Split must cover every sample exactly once')
    by_id={s.sample_id:s for s in splits}; roles=defaultdict(set)
    for r in records:
        s=by_id[r.sample_id]
        if s.manifest_hash!=sha256(manifest) or s.group_id!=groups[r.sample_id] or s.split!=r.development_role or s.development_partition is not None:
            raise ValueError('Stale split, forged group or role mismatch')
        if s.manifest_version!=metadata['dataset_version'] or s.seed!=metadata['seed']:
            raise ValueError('Inconsistent split version/seed')
        roles[s.group_id].add(s.split)
    if any(len(p)!=1 for p in roles.values()): raise ValueError('Connected group crosses partitions')
    if sha256(splits_path)!=metadata['splits_sha256']: raise ValueError('Split hash mismatch')
    for p,h in metadata['artifact_hashes'].items():
        if sha256(resolve_inside(root,p))!=h: raise ValueError('Dataset artifact hash mismatch: '+p)
    clean={r.source_document_id:r for r in records if r.variant_id=='clean'}
    content_roles=defaultdict(set)
    for r in records:
        source=clean.get(r.source_document_id)
        if source is None or (r.applicant_id,r.document_type,r.layout_id,r.source_hash)!=(source.applicant_id,source.document_type,source.layout_id,source.source_hash):
            raise ValueError('Invalid source/variant identity')
        if sha256(root/source.relative_path)!=r.source_hash: raise ValueError('Source hash mismatch')
        annotation=PageAnnotation.model_validate_json((root/r.annotation_path).read_text())
        if annotation.sample_id!=r.sample_id or annotation.clean_sample_id!=source.sample_id:
            raise ValueError('Annotation source/sample mismatch')
        if r.variant_id=='clean':
            key=' '.join(annotation.full_text.casefold().split())
            content_roles[key].add(r.development_role)
    if any(len(v)>1 for v in content_roles.values()): raise ValueError('Exact content duplicate crosses partitions')
    for b in metadata['bundles']:
        from ..schemas import BundleInput
        inputs=BundleInput.model_validate_json((root/b['input_path']).read_text())
        selected=[r for r in records if r.relative_path in inputs.files]
        if len({groups[r.sample_id] for r in selected})!=1 or {r.development_role for r in selected}!={b['partition']}:
            raise ValueError('Bundle crosses groups or has a stale partition')
    if review is not None:
        if review.get('status')!='reviewed' or review.get('manifest_sha256')!=sha256(manifest) or review.get('splits_sha256')!=sha256(splits_path):
            raise ValueError('Missing or stale review')
        for r in records:
            if r.development_role=='test':
                att=review.get('pages',{}).get(r.sample_id,{})
                if att.get('input_sha256')!=sha256(root/r.relative_path) or att.get('annotation_sha256')!=sha256(root/r.annotation_path) or att.get('status')!='reviewed':
                    raise ValueError('Unchecked/stale test page: '+r.sample_id)
        for b in metadata['bundles']:
            if b['partition']=='test':
                att=review.get('bundles',{}).get(b['input_path'],{})
                if att.get('reference_sha256')!=sha256(root/b['reference_path']) or att.get('input_sha256')!=sha256(root/b['input_path']) or att.get('status')!='reviewed':
                    raise ValueError('Unchecked/stale test bundle')
    return dict(status='passed',connected_groups=len(roles),partitions={p:dict(
        pages=len(items:=[r for r in records if r.development_role==p]),
        clean_pages=sum(r.variant_id=='clean' for r in items),sources=len({r.source_document_id for r in items}),
        groups=len({groups[r.sample_id] for r in items}),by_class=dict(Counter(r.document_type for r in items)),
        by_layout=dict(Counter(r.layout_id for r in items)),by_variant=dict(Counter(r.variant_id for r in items)),
        bundles=sum(b['partition']==p for b in metadata['bundles'])) for p in ('train','validation','test')})


def validate_freeze(root, config_path):
    config=json.loads(config_path.read_text())
    freeze_path=root/config['freeze_record']; frozen=json.loads(freeze_path.read_text())
    for p,h in frozen['artifact_hashes'].items():
        if sha256(resolve_inside(root,p))!=h: raise ValueError('Frozen artifact changed: '+p)
    if frozen['evaluation_config_sha256']!=sha256(config_path): raise ValueError('Evaluation config changed')
    # New or removed implementation files also invalidate the snapshot.
    actual={p.relative_to(root).as_posix() for p in (root/'src').rglob('*.py')}
    if actual!=set(frozen['implementation_files']): raise ValueError('Frozen implementation inventory changed')
    if 'environment' in frozen:
        from importlib.metadata import version
        import platform
        from ..ocr import engine_version
        expected=frozen['environment']
        if platform.python_version()!=expected['python'] or engine_version()!=expected['tesseract']:
            raise ValueError('Frozen Python/Tesseract environment changed')
        if any(version(n)!=v for n,v in expected['libraries'].items()):
            raise ValueError('Frozen library environment changed')
        for name,item in expected.get('external_files',{}).items():
            if sha256(Path(item['path']))!=item['sha256']:
                raise ValueError('Frozen executable/language data changed: '+name)
    review=json.loads((root/config['review']).read_text())
    audit=audit_dataset(root,root/config['manifest'],root/config['splits'],review)
    return config,frozen,audit


def selected_records(root, config, partition):
    from ..splitting import load_records
    if partition not in ('train','validation','test'): raise ValueError('Unknown partition')
    records=[r for r in load_records(root/config['manifest']) if r.development_role==partition]
    if [r.sample_id for r in records]!=config['sample_ids'][partition]: raise ValueError('Frozen selection changed')
    return records
