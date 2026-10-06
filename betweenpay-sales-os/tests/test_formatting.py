from sales_os.formatting import normalize_social_text


def test_literal_newlines_become_real_paragraph_breaks():
    text = "First paragraph.\\n\\nSecond paragraph."
    formatted = normalize_social_text(text, "facebook")
    assert "\\n" not in formatted
    assert formatted == "First paragraph.\n\nSecond paragraph."


def test_excessive_blank_lines_collapse():
    text = "One\n\n\n\nTwo"
    assert normalize_social_text(text, "facebook") == "One\n\nTwo"


def test_long_facebook_copy_gets_paragraph_spacing():
    text = (
        "Bills and goals can make the days before payday hard to plan. "
        "BetweenPay helps you see a clearer Safe-to-Spend number. "
        "It protects upcoming bills, goals and a safety buffer first. "
        "The full planner is $12.99 one time with no subscription. "
        "You can also try the free calculator before buying."
    )
    formatted = normalize_social_text(text, "facebook")
    assert "\n\n" in formatted
