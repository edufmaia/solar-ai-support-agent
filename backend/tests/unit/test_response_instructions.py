from app.llm.context import DEFAULT_RESPONSE_INSTRUCTIONS, build_response_instructions


def test_default_when_no_custom_prompt():
    assert build_response_instructions(None) == DEFAULT_RESPONSE_INSTRUCTIONS
    assert build_response_instructions("   ") == DEFAULT_RESPONSE_INSTRUCTIONS


def test_custom_prompt_overrides_default():
    custom = "Você é a assistente da SolFácil. Seja calorosa."
    assert build_response_instructions(custom) == custom
