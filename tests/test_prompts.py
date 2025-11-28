from video_pipeline import prompts


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeModels:
    def __init__(self, response_text: str):
        self._response_text = response_text

    def generate_content(self, model, contents):
        return _FakeResponse(self._response_text)


class _FakeClient:
    def __init__(self, response_text: str):
        self.models = _FakeModels(response_text)


def test_extract_json_parses_code_fence():
    body = """```json
{
  "global_style": "test style",
  "frames": [
    {"id": "A", "prompt": "frame A", "change_from_previous": null},
    {"id": "B", "prompt": "frame B", "change_from_previous": "move"}
  ]
}
```"""
    result = prompts._extract_json(body)
    assert result["global_style"] == "test style"
    assert len(result["frames"]) == 2


def test_generate_frame_prompts_uses_fake_client():
    response_text = """{
        "global_style": "consistent",
        "frames": [
            {"id": "A", "prompt": "frame A", "change_from_previous": null},
            {"id": "B", "prompt": "frame B", "change_from_previous": "move"}
        ]
    }"""
    client = _FakeClient(response_text)
    result = prompts.generate_frame_prompts("theme", 2, client=client)
    assert result["global_style"] == "consistent"
    assert len(result["frames"]) == 2
