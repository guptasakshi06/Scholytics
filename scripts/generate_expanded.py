#!/usr/bin/env python3
"""S09 fictional sources; deterministic generation does not approve references."""
import argparse
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import reportlab
from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from generate_pilot import ABSENT, IDENTITY, degrade, render_bytes
from scholarready.dataset import LABELS, WATERMARK, PageAnnotation, sha256
from scholarready.pipeline import write_json
from scholarready.schemas import BundleInput, DatasetRecord, FIELD_CATALOG
from scholarready.splitting import connected_groups, bundle_members

VERSION = 'expanded-s09-1.0'
NAMES = ('Amber Brook', 'Basil Fern', 'Coral Finch', 'Daisy Glen', 'Ember Hill', 'Flora Lake',
         'Garnet Moss', 'Hazel Pine', 'Indigo Reed', 'Jade Rose', 'Lilac Sage', 'Maple Snow',
         'Nectar Stone', 'Olive Vale', 'Pearl Willow', 'Quartz Wren', 'Ruby Yarrow', 'Saffron Zephyr')
TITLES = ('ACADEMIC MARKSHEET', 'INCOME CERTIFICATE', 'BONAFIDE CERTIFICATE',
          'DOMICILE CERTIFICATE', 'CATEGORY CERTIFICATE')
NOTICES = (('LIBRARY NOTICE', 'Book exchange desk opens on Monday', 'Bring a reading list for the group session'),
           ('FEE RECEIPT', 'Workshop materials payment recorded', 'This receipt concerns a fictional art activity'),
           ('EVENT POSTER', 'Science exhibition opens on Thursday', 'Visitors may join the model making session'),
           ('COURSE TIMETABLE', 'Morning studio session followed by seminar', 'Afternoon activities include group discussion'),
           ('BUS NOTICE', 'Campus shuttle departs after the afternoon class', 'Use the west gate waiting area'))
TOPICS = ('Watercolor landscapes', 'Clay animal models', 'Paper flower folding', 'Woodland sound study',
          'Cloud painting', 'Leaf shape drawing', 'River ecology', 'Night sky stories', 'Garden poetry',
          'Stone mosaics', 'Winter bird sketches', 'Sand sculpture', 'Rainfall diaries', 'Meadow photography',
          'Forest maps', 'Wind powered toys', 'Seed collections', 'Sunlight experiments')


def definitions(label, i):
    name = 'Fictional ' + NAMES[i]
    college = f'Fictional {NAMES[i].split()[1]} College'
    year = f'{2022+i%4}-{2023+i%4}'
    date = f'2026-{1+i%9:02d}-{10+i%17:02d}'
    return {
        'marksheet': [('student_name', 'Student name', name, name, 'applicant', None),
                      ('institution', 'Institution', college, college, None, None),
                      ('academic_year', 'Academic year', year, year, None, None),
                      ('stated_percentage', 'Stated percentage', f'{65+i}.25', f'{65+i}.25', None, '%'),
                      ('stated_total', 'Stated total', str(650+11*i), str(650+11*i), None, None)],
        'income_certificate': [('applicant_name', 'Applicant name', name, name, 'applicant', None),
                      ('guardian_name', 'Guardian name', 'Fictional Guardian '+NAMES[i].split()[1],
                       'Fictional Guardian '+NAMES[i].split()[1], 'guardian', None),
                      ('annual_income', 'Annual income (INR/year)', str(81000+7351*i), 81000+7351*i, None, 'INR/year'),
                      ('issue_date', 'Issue date', date, date, None, None)],
        'bonafide_certificate': [('student_name', 'Student name', name, name, 'applicant', None),
                      ('institution', 'Institution', college, college, None, None),
                      ('course', 'Course', ('BSc Physics', 'BA History', 'BCom', 'BSc Chemistry')[i%4],
                       ('BSc Physics', 'BA History', 'BCom', 'BSc Chemistry')[i%4], None, None),
                      ('academic_year', 'Academic year', year, year, None, None)],
        'domicile_certificate': [('applicant_name', 'Applicant name', name, name, 'applicant', None),
                      ('domicile_region', 'Domicile region', f'Fictional {NAMES[i].split()[1]} Region',
                       f'Fictional {NAMES[i].split()[1]} Region', None, None),
                      ('issue_date', 'Issue date', date, date, None, None)],
        'category_certificate': [('applicant_name', 'Applicant name', name, name, 'applicant', None),
                      ('stated_category', 'Stated category', ('Demo Group A', 'Demo Group B', 'Demo Group C')[i%3],
                       ('Demo Group A', 'Demo Group B', 'Demo Group C')[i%3], None, None),
                      ('issue_date', 'Issue date', date, date, None, None)],
        'other': [],
    }[label]


def draw(canvas, label, i, layout):
    lines, fields = [], {n: deepcopy(ABSENT) for n in sorted(FIELD_CATALOG.get(label, set()))}
    def line(text, x, y, size=12, font='Expanded'):
        canvas.setFont(font, size); canvas.drawString(x, y, text)
        box = [x*2, (800-y-size)*2, stringWidth(text, font, size)*2, size*2.5]
        lines.append(dict(text=text, box=box)); return box
    x = (42, 62, 95, 160)[layout]
    line(WATERMARK, 40, 766, 10)
    line(TITLES[LABELS.index(label)] if label != 'other' else NOTICES[i%5][0], 40, 715, 19, 'ExpandedBold')
    line('Fictional teaching sample - document readiness only', 40, 680, 11)
    y = 620
    for name, caption, raw, value, role, unit in definitions(label, i):
        size = 11 + i%3 * .5
        if layout in (0, 2):
            box = line(caption+': '+raw, x, y, size)
            box = [box[0]+2*stringWidth(caption+': ', 'Expanded', size), box[1],
                   2*stringWidth(raw, 'Expanded', size), box[3]]
            y -= 70
        else:
            line(caption, x, y, 11, 'ExpandedBold')
            box = line(raw, x+8, y-23, size)
            y -= 85
        fields[name] = dict(state='present', raw_text=raw, normalized_value=value,
                            person_role=role, unit=unit, box=box)
    if label == 'other':
        for text in NOTICES[i%5][1:]:
            line(text, 40, y, 12); y -= 45
        line('Activity theme: '+TOPICS[i], 40, y, 12)
    line('No official seal, identifier or authenticity claim', 40, 78, 10)
    line('Page 1 of 1', 40, 50, 10)
    canvas.showPage()
    return dict(width=1200, height=1600, coordinate_space='pending', full_text='\n'.join(l['text'] for l in lines),
                lines=lines, fields=fields, source_to_sample=deepcopy(IDENTITY))


def generate(root):
    media = root/'data/synthetic/expanded'; media.mkdir(parents=True, exist_ok=False)
    annotations = root/'data/annotations/expanded'; annotations.mkdir(parents=True, exist_ok=False)
    fonts = Path(reportlab.__file__).parent/'fonts'
    for name, file in [('Expanded', 'Vera.ttf'), ('ExpandedBold', 'VeraBd.ttf')]:
        registerFont(TTFont(name, str(fonts/file)))
    records, bundles, indexed = [], [], {}
    def relative(p): return p.relative_to(root).as_posix()
    def add(i, label, layout, role, source, path, annotation, variant, parameters):
        sid = source+'-'+variant
        annotation.update(sample_id=sid, clean_sample_id=source+'-clean', coordinate_space=sid+':original_pixels')
        reference = annotations/(sid+'.json')
        write_json(reference, PageAnnotation.model_validate(annotation))
        r = DatasetRecord(sample_id=sid, source_document_id=source, applicant_id=f'expanded-{i:02d}',
            layout_id=f'expanded_layout_{layout}', relative_path=relative(path), document_type=label,
            page_index=1, source_page_index=1, variant_id=variant,
            degradation=dict(type='none' if variant=='clean' else variant, parameters=parameters, seed=2026+i),
            source_category='synthetic', consent_note='Wholly fictional generated content; no real documents or identifiers.',
            source_hash=sha256(indexed[i,label,'source']), annotation_path=relative(reference), development_role=role)
        records.append(r); indexed[i,label,variant] = r
    for i in range(18):
        role = 'train' if i<10 else 'validation' if i<14 else 'test'
        layout = i%3 if i!=17 else 3
        for j, label in enumerate(LABELS):
            source = f'exp-{i:02d}-{j}'
            buffer = BytesIO(); canvas = Canvas(buffer, pagesize=(600,800), invariant=1, pageCompression=1)
            canvas.setTitle('Fictional academic document fixture')
            ref = draw(canvas, label, i, layout); canvas.save(); content = buffer.getvalue()
            extension = ('.png','.jpg','.pdf')[(i+j)%3]
            path = media/(source+extension)
            image = render_bytes(content, 1)
            if extension=='.pdf': path.write_bytes(content)
            else: image.save(path, **(dict(quality=95,subsampling=0) if extension=='.jpg' else {}))
            indexed[i,label,'source'] = path
            if extension=='.jpg':
                with Image.open(path) as stored: image = stored.convert('RGB').copy()
            add(i,label,layout,role,source,path,deepcopy(ref),'clean',dict(dpi=144, renderer='pypdfium2'))
            variant = 'rotation' if (i+j)%2 else 'low_contrast'
            changed, annotation, parameters, _ = degrade(image,ref,variant,2026+i)
            vpath=media/(source+'-'+variant+'.png'); changed.save(vpath)
            add(i,label,layout,role,source,vpath,annotation,variant,parameters)
            if label=='income_certificate':
                # Omit the entire income label/value line while preserving title, name and date.
                changed=image.copy(); box=ref['fields']['annual_income']['box']
                label_line=next(l for l in ref['lines'] if l['text'].startswith('Annual income'))
                top=min(box[1],label_line['box'][1])-5
                changed.paste('white',(0,int(top),1200,int(box[1]+box[3]+6)))
                if layout in (1,3):
                    changed.paste('white',(0,int(top-46),1200,int(top)))
                annotation=deepcopy(ref)
                annotation['lines']=[l for l in annotation['lines'] if not l['text'].startswith('Annual income')
                                     and l['text'] != str(81000+7351*i)]
                annotation['full_text']='\n'.join(l['text'] for l in annotation['lines'])
                annotation['fields']['annual_income']=dict(ABSENT, state='unreadable')
                vpath=media/(source+'-no_amount.png'); changed.save(vpath)
                add(i,label,layout,role,source,vpath,annotation,'no_amount',dict(operation='erase labelled income region', rectangle=[0,int(top-46 if layout in (1,3) else top),1200,int(box[1]+box[3]+6)]))
        for scenario in ('complete','missing_income','category_false','category_unknown','name_mismatch','no_amount'):
            chosen=[indexed[i,label,'no_amount' if scenario=='no_amount' and label=='income_certificate' else 'clean']
                    for label in LABELS[:-1] if not (scenario=='missing_income' and label=='income_certificate')
                    and not (scenario=='category_false' and label=='category_certificate')]
            name='Fictional '+NAMES[i]
            profile=dict(applicant_reference=f'expanded-{i:02d}', expected_name='Fictional Different Person' if scenario=='name_mismatch' else name,
                         category_certificate_required=False if scenario=='category_false' else None if scenario=='category_unknown' else True)
            sid=f'expanded-{i:02d}-{scenario}'
            folder=root/'data/bundles/expanded'/sid; folder.mkdir(parents=True)
            inputs=BundleInput(scenario_id=sid,profile=profile,files=[r.relative_path for r in chosen],declared_type_hints={})
            write_json(folder/'inputs.json',inputs)
            states=dict.fromkeys(('marksheet','income','bonafide','domicile','category'),'satisfied')
            overall='ready'; score=100.
            if scenario=='missing_income': states['income']='missing'; overall='incomplete'; score=80.
            if scenario=='category_false': states['category']='not_applicable'
            if scenario=='category_unknown': states['category']='needs_review'; overall='needs_review'; score=None
            if scenario=='name_mismatch': states=dict.fromkeys(states,'needs_review'); overall='needs_review'; score=0.
            if scenario=='no_amount': states['income']='unreadable'; overall='needs_clearer_upload'; score=80.
            write_json(folder/'expected.json',dict(scenario_id=sid,requirements=states,overall_state=overall,completeness=score,
                rationale={'complete':'Five labelled types and all required fields for the named applicant.',
                'missing_income':'Four resolved supported uploads, no income document.', 'category_false':'Explicit false excludes only category.',
                'category_unknown':'Applicability unresolved, denominator null.', 'name_mismatch':'Every applicant-role name differs from explicitly expected name; guardian role excluded.',
                'no_amount':'Income title/name/date remain, amount and label erased; no invented value.'}[scenario],reference_status='provisional'))
            bundles.append(dict(input_path=relative(folder/'inputs.json'),reference_path=relative(folder/'expected.json'),partition=role))
    manifest=root/'data/manifests/expanded.jsonl'
    manifest.parent.mkdir(parents=True,exist_ok=True)
    manifest.write_text(''.join(r.model_dump_json()+'\n' for r in records))
    groups=connected_groups(records,bundle_members(root,records,[b['input_path'] for b in bundles]))
    splits=[dict(schema_version='1.0',sample_id=r.sample_id,group_id=groups[r.sample_id],split=r.development_role,
                 seed=2026,manifest_version=VERSION,manifest_hash=sha256(manifest),development_partition=None) for r in records]
    split_path=root/'data/manifests/expanded.splits.jsonl'
    split_path.write_text(''.join(json.dumps(s)+'\n' for s in splits))
    paths={r.relative_path for r in records}|{r.annotation_path for r in records}|{b[k] for b in bundles for k in ('input_path','reference_path')}
    write_json(manifest.with_suffix('.metadata.json'),dict(dataset_version=VERSION,seed=2026,synthetic_only=True,
        manifest_sha256=sha256(manifest),splits_sha256=sha256(split_path),bundles=bundles,
        artifact_hashes={p:sha256(root/p) for p in sorted(paths)},font_hashes={f:sha256(fonts/f) for f in ('Vera.ttf','VeraBd.ttf')},
        partition_policy='Predeclared applicant indices 0..9 train,10..13 validation,14..17 test; no outcome used. Pilot excluded.',
        unseen_layout='expanded_layout_3: applicant17 test only; other test layouts known.'))
    print(json.dumps(dict(sources=108,pages=len(records),applicants=18,bundles=len(bundles),manifest_sha256=sha256(manifest))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--root',type=Path,default=Path.cwd())
    generate(parser.parse_args().root.resolve())
