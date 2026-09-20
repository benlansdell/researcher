from research_wiki.markdown import (
    MANAGED_END,
    MANAGED_START,
    REFS_END,
    REFS_START,
    add_reference,
    human_text,
    replace_region,
    topic_template,
)


def test_replace_region_is_idempotent():
    text = "# Note\n\nhello\n"
    a = replace_region(text, MANAGED_START, MANAGED_END, "## Related\n\n- [[X]]")
    b = replace_region(a, MANAGED_START, MANAGED_END, "## Related\n\n- [[X]]")
    assert a == b
    assert a.count(MANAGED_START) == 1


def test_human_text_removes_managed_block():
    text = f"# N\nHuman\n\n{MANAGED_START}\nAI\n{MANAGED_END}\n"
    cleaned = human_text(text)
    assert "Human" in cleaned
    assert "AI" not in cleaned


def test_add_reference_deduplicates():
    text = topic_template("Agency")
    a = add_reference(text, "Daily/2026-01-01.md", "Interesting thought")
    b = add_reference(a, "Daily/2026-01-01.md", "Interesting thought")
    assert a == b
    assert b.count("Interesting thought") == 1
