from studio import brand, fonts, mtex, speech, voice


def test_spoken_symbols():
    s = speech.spoken(r"sin r = 1/η and √2 ≠ 1.5, θ = 30°, \frac{a}{b}")
    assert "eta" in s and "root" in s and "is not" in s and "degrees" in s and "a over b" in s
    assert "\\" not in s and "η" not in s


def test_caption_chunks_sum_to_one():
    ch = voice.caption_chunks("Three cars. Same start, same finish. Which one wins?", 3)
    assert abs(sum(f for _, f in ch) - 1) < 1e-9
    assert all(len(c.split()) <= 3 for c, _ in ch)


def test_math_renders_parts():
    eq = mtex.M(r"CD", r"=\dfrac{\ell}{\sqrt{\eta^2-1}}")
    assert len(eq) == 2 and eq.width > eq.height > 0


def test_font_covers_devanagari_and_greek():
    for text in ["प्रकाश क्या है?", "sin r = 1/η", "SHORTEST ≠ FASTEST"]:
        name = fonts.font_file_for(text, "heading")
        assert fonts.covers(name, text), (text, name)
    f = fonts.pil("heading", 40, "प्रकाश")
    assert f.getbbox("प्रकाश")[2] > 0


def test_brand_semantic_colors(tmp_path):
    b = brand.load(tmp_path, {"channel_name": "Test"})
    assert b.channel_name == "Test" and brand.color("accent").startswith("#")


def test_brand_json_overrides(tmp_path):
    (tmp_path / "brand.json").write_text('{"colors": {"accent": "#123456"}, "speed": 1.1}', encoding="utf-8")
    b = brand.load(tmp_path, {"channel_name": "X"})
    assert brand.color("accent") == "#123456" and b.speed == 1.1


def test_fake_tts_duration(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDIO_FAKE_TTS", "1")
    monkeypatch.setenv("STUDIO_DATA", str(tmp_path))
    path, dur = voice.tts("one two three four", "am_michael", 1.0)
    assert abs(dur - 4 * 0.35) < 0.05 and path.exists()
