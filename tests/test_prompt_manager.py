from api.utils.prompt_manager import get_nlm_prompt


def test_get_nlm_prompt_accepts_long_custom_prompt():
    custom_prompt = (
        "你現在是一位「資深財經分析師」。請幫我精準分析這部影片，並以繁體中文條列出以下 4 個重點：\n"
        "1. 核心結論與預測：用 3 句話總結當前局勢，以及講者對未來走向的預測。\n"
        "2. 台美股焦點標的：明確列出提及的「台股」與「美股」代號或公司名，並附上講者的看法。"
    )

    prompt = get_nlm_prompt(custom_prompt)

    assert custom_prompt in prompt
    assert "重要規範" in prompt


def test_get_nlm_prompt_loads_file_key():
    prompt = get_nlm_prompt("finance")

    assert "資深財經分析師" in prompt
    assert "重要規範" in prompt
