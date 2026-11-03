import pytest
from scholarready.evaluation.ocr_metrics import aggregate, edit_distance, normalize, score


def test_known_edits_and_unicode():
    assert edit_distance('kitten', 'sitting') == 3
    assert edit_distance('abc', 'abc') == 0
    assert normalize('  CAFÉ\nfoo ') == normalize('cafe\u0301 FOO')
    result = score('a cat', 'a bat')
    assert result['character_edits'] == 1 and result['word_edits'] == 1
    assert result['cer'] == pytest.approx(1 / 5)
    assert result['wer'] == .5


def test_empty_outputs_and_insertions():
    assert score('abc', '')['cer'] == 1
    both = score('', '')
    assert both['cer'] is None and both['wer'] is None
    inserted = score('', 'hello there')
    assert inserted['empty_reference_insertions'] == 11
    assert inserted['character_edits'] == 11 and inserted['cer'] is None
    assert score('a', 'aaaa')['cer'] == 3
    combined = aggregate([score('a', ''), inserted])
    assert combined['cer'] == 12 and combined['empty_reference_count'] == 1
    assert aggregate([])['cer'] is None
