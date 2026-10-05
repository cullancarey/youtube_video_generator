from lambdas.youtube import content_safety


def test_find_denylisted_term_detects_match():
    assert (
        content_safety.find_denylisted_term("A quote from Adolf Hitler")
        == "Adolf Hitler"
    )


def test_find_denylisted_term_is_case_insensitive():
    assert content_safety.find_denylisted_term("praising the NAZI regime") == "NAZI"


def test_find_denylisted_term_respects_word_boundaries():
    # "assassin" contains no denylisted substring as a whole word.
    assert content_safety.find_denylisted_term("the assassin crept away") is None


def test_find_denylisted_term_returns_none_for_clean_text():
    assert (
        content_safety.find_denylisted_term("Believe you can and you're halfway there")
        is None
    )


def test_find_denylisted_term_handles_empty_text():
    assert content_safety.find_denylisted_term("") is None
    assert content_safety.find_denylisted_term(None) is None


def test_is_text_safe():
    assert content_safety.is_text_safe("A normal inspirational quote") is True
    assert content_safety.is_text_safe("Quoting Hitler here") is False
