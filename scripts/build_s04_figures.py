#!/usr/bin/env python3
"""Figures from saved S04 predictions/stages plus a labelled synthetic pixel stress case."""
import argparse
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from scholarready.pipeline import write_json
from scholarready.preprocessing import morph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    def read(variant, name):
        return json.loads((args.run / variant / name).read_text())
    def page_for(variant, sample):
        row = next(r for r in read(variant, 'ocr_evaluation.json')['samples'] if r['sample_id'] == sample)
        result = read(variant, 'result.json')
        doc = next(d for d in result['documents'] if d['document_id'] == row['document_id'])
        return row, doc, next(p for p in doc['processing'] if p['page_id'] == row['page_id'])
    sample = 'src-001-p01-low_contrast'
    row, doc, processing = page_for('C', sample)
    fig, axes = plt.subplots(2, 4, figsize=(16, 12))
    for ax, stage in zip(axes.flat, processing['stages']):
        with Image.open(args.run / 'C' / stage['image_path']) as image:
            ax.imshow(image, cmap='gray', vmin=0, vmax=255)
        ax.set_title(stage['name'])
        ax.axis('off')
    for ax in list(axes.flat)[len(processing['stages']):]:
        ax.axis('off')
    fig.suptitle(f'{sample}: saved C stages (identity 1x1 morphology)\n{row["run_id"]}', fontsize=12)
    fig.tight_layout()
    fig.savefig(args.output / 'stage_panel.png', dpi=140)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for label in ['ingested_original', 'clahe', 'adaptive']:
        stage = next(s for s in processing['stages'] if s['name'] == label)
        with Image.open(args.run / 'C' / stage['image_path']) as image:
            gray = np.asarray(image.convert('L'))
        axes[0].hist(gray.ravel(), bins=np.arange(257), histtype='step', label=label)
    axes[0].set_yscale('log')
    axes[0].set_xlabel('Intensity (0 black, 255 white)')
    axes[0].set_ylabel('Pixel count, logarithmic')
    axes[0].legend(fontsize=8)
    axes[0].set_title('Low-contrast page histogram')
    sample = 'src-001-p01-rotation'
    for ax, variant in zip(axes[1:], ['A', 'C']):
        row, doc, processing = page_for(variant, sample)
        with Image.open(args.run / variant / processing['stages'][-1]['image_path']) as image:
            ax.imshow(image, cmap='gray', vmin=0, vmax=255)
        ax.set_title(f'{sample}\n{variant} CER {row["metrics"]["cer"]:.4%}')
        ax.axis('off')
    fig.tight_layout()
    fig.savefig(args.output / 'histogram_and_rotation.png', dpi=140)
    plt.close(fig)

    summary = json.loads((args.run / 'comparison.json').read_text())
    names = [v['name'] for v in summary['variants']]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].barh(names, [v['aggregate']['cer'] * 100 for v in summary['variants']])
    axes[0].set_xlabel('Corpus CER (%)')
    axes[0].invert_yaxis()
    for key, label in [('preprocessing_seconds', 'DIP/stage save'), ('ocr_seconds', 'OCR')]:
        axes[1].plot([v[key] for v in summary['variants']], names, 'o-', label=label)
    axes[1].invert_yaxis()
    axes[1].set_xlabel('Sequential observed seconds (14 selected development pages)')
    axes[1].legend()
    fig.suptitle(summary['comparison_id'] + '\nProvisional synthetic references; descriptive timing, no held-out claim', fontsize=10)
    fig.tight_layout()
    fig.savefig(args.output / 'metrics.png', dpi=140)
    plt.close(fig)

    fig, axes = plt.subplots(4, 1, figsize=(12, 7))
    for ax, variant in zip(axes, ['A', 'B', 'C', 'C_kernel_2x2']):
        row, doc, processing = page_for(variant, 'src-001-p01-low_contrast')
        # Fixed display ROI in this 1200x1600, zero-deskew development page only.
        assert np.allclose(processing['transform']['matrix'], np.eye(3))
        with Image.open(args.run / variant / processing['stages'][-1]['image_path']) as image:
            ax.imshow(image.crop((80, 704, 410, 758)), cmap='gray', vmin=0, vmax=255, interpolation='nearest')
        line = next((line for line in row['prediction_text'].splitlines() if 'percentage' in line.casefold()), '(label not recognized)')
        ax.set_title(f'{variant} actual OCR: {line}', fontsize=11)
        ax.axis('off')
    fig.suptitle('Observed development harm: 72.5 -> 725 after 2x2 opening/closing\nSame low-contrast page/settings; fixed display crop is not an inference input.', fontsize=12)
    fig.tight_layout()
    fig.savefig(args.output / 'decimal_harm.png', dpi=150)
    plt.close(fig)

    # Deliberately constructed educational stress input, not a dataset performance sample.
    binary = np.full((16, 24), 255, np.uint8)
    binary[4:12, 3:7] = 0
    binary[4:12, 8:12] = 0
    binary[11, 17] = 0
    cases = [('identity', binary), ('opening 2x2', morph(binary, 'open', [2, 2])),
             ('closing 1x2', morph(binary, 'close', [1, 2])),
             ('open then close 2x2', morph(binary, 'open_close', [2, 2]))]
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.5))
    values = []
    for ax, (label, image) in zip(axes, cases):
        ax.imshow(image, cmap='gray', vmin=0, vmax=255, interpolation='nearest')
        components = cv2.connectedComponents(255 - image)[0] - 1
        ax.set_title(f'{label}\n{components} ink components')
        ax.set_xticks([])
        ax.set_yticks([])
        values.append(dict(case=label, ink_components=components, ink_pixels=int(np.count_nonzero(image == 0)),
            decimal_at_original_location_retained=bool(image[11, 17] == 0)))
    fig.suptitle('Constructed pixel stress example: dot removal and stroke joining\nBlack text; even-kernel anchors may shift strokes. Not an OCR performance measurement.', fontsize=10)
    fig.tight_layout()
    fig.savefig(args.output / 'morphology_harm.png', dpi=150)
    plt.close(fig)
    write_json(args.output / 'morphology_harm.json', values)
    print('Saved five PNG figures and numeric morphology stress evidence.')


if __name__ == '__main__':
    main()
