from app.llm.context import sanitize_assistant_text


def test_removes_bracket_image_placeholder():
    out = sanitize_assistant_text("Veja o imóvel:\n\n[Imagem geoespacial]\n\nConfirme, por favor.")
    assert "Imagem" not in out
    assert "[" not in out
    assert "Confirme, por favor." in out


def test_drops_image_announcement_line():
    text = (
        "Ótimo! Vou compartilhar os resultados.\n"
        "Aqui está a imagem do local analisado:\n"
        "[Imagem geoespacial]\n"
        "Por favor, confirme se é a sua residência."
    )
    out = sanitize_assistant_text(text)
    assert "imagem" not in out.lower()
    assert "Por favor, confirme se é a sua residência." in out
    assert "resultados" in out


def test_removes_markdown_image():
    out = sanitize_assistant_text("Resposta ![satelite](http://x/y.png) final.")
    assert "![" not in out and "http" not in out
    assert "Resposta" in out and "final." in out


def test_plain_text_unchanged():
    text = "A estimativa preliminar é de 17 a 19 placas, cerca de 9.9 kWp."
    assert sanitize_assistant_text(text) == text
