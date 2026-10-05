from lambdas.youtube import metadata_optimizer


def test_generate_title_uses_capitalized_phrase():
    text = "Maya Angelou once said: rise above it all."
    title, description = metadata_optimizer.generate_title_and_description(
        text, "someuser", "https://reddit.com/r/quotes/x"
    )
    assert "Maya Angelou" in title
    assert "someuser" in description


def test_generate_title_skips_denylisted_phrase():
    text = "Quote mentions Adolf Hitler, but humanity moved forward."
    title, _ = metadata_optimizer.generate_title_and_description(
        text, "someuser", "https://reddit.com/r/quotes/x"
    )
    assert "Adolf Hitler" not in title
    assert "Daily Inspiration" in title


def test_generate_title_falls_back_when_no_matches():
    text = "just lowercase words with no proper nouns"
    title, _ = metadata_optimizer.generate_title_and_description(
        text, "someuser", "https://reddit.com/r/quotes/x"
    )
    assert "Daily Inspiration" in title


def test_optimize_metadata_returns_expected_shape():
    title, description, keywords, thumbnail = metadata_optimizer.optimize_metadata(
        "Some inspirational text", "author", "https://reddit.com/r/quotes/x"
    )
    assert isinstance(title, str)
    assert isinstance(description, str)
    assert isinstance(keywords, list)
    assert thumbnail is None
