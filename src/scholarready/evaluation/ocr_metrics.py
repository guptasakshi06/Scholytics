"""Development CER/WER: Unicode NFC + casefold + collapsed whitespace."""
import unicodedata

NORMALIZATION = 'nfc_casefold_collapse_whitespace_v1'


def normalize(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def edit_distance(reference, prediction) -> int:
    previous = list(range(len(prediction) + 1))
    for row, ref in enumerate(reference, 1):
        current = [row]
        for column, pred in enumerate(prediction, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (ref != pred)))
        previous = current
    return previous[-1]


def score(reference: str, prediction: str) -> dict:
    ref, pred = normalize(reference), normalize(prediction)
    chars, words = edit_distance(ref, pred), edit_distance(ref.split(), pred.split())
    return dict(normalization=NORMALIZATION, character_edits=chars, reference_characters=len(ref),
                word_edits=words, reference_words=len(ref.split()),
                cer=chars / len(ref) if ref else None,
                wer=words / len(ref.split()) if ref.split() else None,
                empty_reference=not bool(ref), empty_prediction=not bool(pred),
                empty_reference_insertions=len(pred) if not ref else 0)


def aggregate(rows: list[dict]) -> dict:
    chars = sum(r['reference_characters'] for r in rows)
    words = sum(r['reference_words'] for r in rows)
    char_edits = sum(r['character_edits'] for r in rows)
    word_edits = sum(r['word_edits'] for r in rows)
    return dict(sample_count=len(rows), character_edits=char_edits, reference_characters=chars,
                word_edits=word_edits, reference_words=words,
                cer=char_edits / chars if chars else None, wer=word_edits / words if words else None,
                empty_reference_count=sum(r['empty_reference'] for r in rows),
                empty_prediction_count=sum(r['empty_prediction'] for r in rows),
                normalization=NORMALIZATION)
