"""Connected-component development splits; no reference annotation files are read."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random

from .dataset import resolve_inside, sha256
from .schemas import BundleInput, DatasetRecord, SplitRecord


def load_records(manifest):
    records = [DatasetRecord.model_validate_json(line) for line in Path(manifest).read_text().splitlines()]
    if not records or len({r.sample_id for r in records}) != len(records):
        raise ValueError('Empty manifest or duplicate sample IDs')
    return records


def connected_groups(records, bundles=()):
    parent = {r.sample_id: r.sample_id for r in records}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def join(ids):
        ids = list(ids)
        if not ids:
            return
        if set(ids) - parent.keys():
            raise ValueError('Bundle references unknown sample')
        for item in ids[1:]:
            parent[find(item)] = find(ids[0])

    keys = defaultdict(list)
    for r in records:
        for key in (('applicant', r.applicant_id), ('source', r.source_document_id),
                    ('hash', r.source_hash), ('file', r.relative_path)):
            keys[key].append(r.sample_id)
    for ids in keys.values():
        join(ids)
    for ids in bundles:
        join(ids)
    components = defaultdict(list)
    for r in records:
        components[find(r.sample_id)].append(r.sample_id)
    return {sid: 'group-' + hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()[:16]
            for ids in components.values() for sid in ids}


def bundle_members(root, records, bundle_paths):
    by_file = defaultdict(list)
    for r in records:
        by_file[r.relative_path].append(r.sample_id)
    groups = []
    for relative in bundle_paths:
        bundle = BundleInput.model_validate_json(resolve_inside(root, relative).read_text())
        if set(bundle.files) - by_file.keys():
            raise ValueError('Bundle input file absent from dataset')
        groups.append([sid for file in bundle.files for sid in by_file[file]])
    return groups


def context(manifest, root):
    records = load_records(manifest)
    meta_path = Path(manifest).with_suffix('.metadata.json')
    meta = json.loads(meta_path.read_text())
    if meta['manifest_sha256'] != sha256(Path(manifest)):
        raise ValueError('Dataset metadata/manifest hash mismatch')
    paths = [b['input_path'] for b in meta['bundles']]
    hashes = {p: sha256(resolve_inside(root, p)) for p in paths}
    return records, meta, connected_groups(records, bundle_members(root, records, paths)), hashes


def make_development_splits(records, groups, manifest_hash, version, seed=42):
    if any(r.development_role != 'development_only' for r in records):
        raise ValueError('S05 accepts development_only data; protected roles are not consumed')
    members = defaultdict(list)
    for r in records:
        members[groups[r.sample_id]].append(r)
    ids = sorted(members)
    random.Random(seed).shuffle(ids)
    if len(ids) < 3:
        raise ValueError('At least three connected groups required for development split')
    # Fixed diagnostic: fit on layout_a; inspect layout_b without tuning to that probe.
    pure_a = [g for g in ids if {r.layout_id for r in members[g]} == {'layout_a'}]
    pure_b = [g for g in ids if {r.layout_id for r in members[g]} == {'layout_b'}]
    remaining = [g for g in ids if g not in pure_a + pure_b]
    if len(pure_a) >= 2 and pure_b and remaining:
        assignment = {g: 'train' for g in ids}
        assignment[pure_b[0]] = 'layout_probe'
        assignment[remaining[0]] = 'validation'
    else:
        assignment = {g: ('validation' if i == 0 else 'train') for i, g in enumerate(ids)}
    labels = {r.document_type for r in records}
    for partition in ('train', 'validation'):
        if {r.document_type for r in records if assignment[groups[r.sample_id]] == partition} != labels:
            raise ValueError('Connected groups cannot supply all classes in train/validation; collect more development data')
    return [SplitRecord(sample_id=r.sample_id, group_id=groups[r.sample_id], split='development_only',
                       development_partition=assignment[groups[r.sample_id]], seed=seed,
                       manifest_version=version, manifest_hash=manifest_hash) for r in records]


def validate_splits(records, splits, groups, manifest_hash):
    if len(splits) != len(records) or {s.sample_id for s in splits} != {r.sample_id for r in records}:
        raise ValueError('Split must cover every sample exactly once')
    if len({s.sample_id for s in splits}) != len(splits):
        raise ValueError('Duplicate split sample')
    group_partitions = defaultdict(set)
    for s in splits:
        if s.manifest_hash != manifest_hash or s.group_id != groups[s.sample_id]:
            raise ValueError('Stale manifest or incorrect connected group')
        if s.split != 'development_only' or s.development_partition is None:
            raise ValueError('S05 requires nested development partitions; test roles are protected')
        group_partitions[s.group_id].add(s.development_partition)
    if any(len(parts) > 1 for parts in group_partitions.values()):
        raise ValueError('Connected applicant/source/hash/bundle group crosses partitions')
    if any(r.development_role != 'development_only' for r in records):
        raise ValueError('Protected dataset role')
    if len({s.seed for s in splits}) != 1 or len({s.manifest_version for s in splits}) != 1:
        raise ValueError('Inconsistent split seed/version')
    return {'status': 'passed', 'samples': len(splits), 'connected_groups': len(group_partitions),
            'partitions': {p: sum(s.development_partition == p for s in splits)
                           for p in ('train', 'validation', 'layout_probe')}, 'final_test_consumed': False}
