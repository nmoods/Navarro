"""Direction polish, narrative splitting and caption alignment (pure functions, no I/O)."""

from __future__ import annotations

from app.application.direction import extract_events, extract_places, extract_stats, kinetic_lines, polish_storyboard
from app.application.narrative import analyse, split_into_scenes
from app.application.ports import TimedWord
from app.domain.story import SceneDraft, StoryboardDraft
from app.infrastructure.audio.whisper import align_to_script


def _scene(**kw) -> SceneDraft:  # type: ignore[no-untyped-def]
    base = {"title": "S", "narration": "Text.", "visual_type": "cinematic_image", "visual_description": "", "image_prompt": "p",
            "camera_movement": "static", "transition": "crossfade", "mood": "dark"}
    return SceneDraft.model_validate(base | kw)


def test_empty_procedural_visuals_are_filled_from_narration_or_downgraded() -> None:
    board = StoryboardDraft(scenes=[
        _scene(visual_type="timeline", narration="In 1587 the colonists landed. By 1590 the island was deserted."),
        _scene(visual_type="historical_map", narration="They sailed from England to Roanoke Island."),
        _scene(visual_type="historical_map", narration="Nobody knows where they went."),
        _scene(visual_type="comparison", narration="Before and after."),
        _scene(visual_type="infographic", narration="Of 115 settlers, none were found."),
    ])  # fmt: skip
    out = polish_storyboard(board, "dark_mystery").scenes
    assert [e.date for e in out[0].visual_data.events] == ["1587", "1590"]
    assert [p.name for p in out[1].visual_data.places] == ["England", "Roanoke Island"] and out[1].visual_data.draw_route
    assert out[2].visual_type.value == "parallax"
    assert out[3].visual_type.value == "cinematic_image"
    assert out[4].visual_data.stats[0].value == 115
    assert all(s.narration == b.narration for s, b in zip(out, board.scenes, strict=True))


def test_image_scenes_get_varied_camera_and_atmosphere() -> None:
    board = StoryboardDraft(scenes=[_scene(narration=f"Line {i}.") for i in range(4)])
    out = polish_storyboard(board, "dark_mystery").scenes
    cams = [s.camera_movement.value for s in out]
    assert "static" not in cams and all(a != b for a, b in zip(cams, cams[1:], strict=False))
    assert any(s.effects for s in out)


def test_extractors() -> None:
    assert kinetic_lines("They returned empty-handed, carrying no bodies, no letters, just silence.") == [
        "They returned empty-handed", "carrying no bodies", "no letters"]  # fmt: skip
    assert extract_events("Nothing happened.") == []
    assert extract_places("A trip to Paris and Rome.")[0].name == "Paris"
    assert extract_stats("About 90% vanished.")[0].unit == "%"


def test_split_into_scenes_preserves_every_word() -> None:
    text = "One two three. Four five six seven. Eight nine. Ten eleven twelve thirteen. Fourteen."
    scenes = split_into_scenes(text, 3)
    assert len(scenes) == 3
    assert " ".join(scenes) == text


def test_pacing_analysis_flags_long_scenes_and_weak_hooks() -> None:
    report = analyse(["word " * 45, "short one here ok fine"], hook="This is a plain opening line")
    assert any("Scene 1 is long" in w for w in report["warnings"])
    assert any("tension marker" in w for w in report["warnings"])


def test_alignment_keeps_script_spelling_and_interpolates_gaps() -> None:
    recognised = [TimedWord("in", 0.0, 0.2), TimedWord("fifteen", 0.3, 0.6), TimedWord("eighty", 0.6, 0.9),
                  TimedWord("seven", 0.9, 1.2), TimedWord("they", 1.4, 1.6), TimedWord("vanished", 1.6, 2.1)]  # fmt: skip
    words = align_to_script("In 1587, they vanished.", recognised, 2.3)
    assert [w.text for w in words] == ["In", "1587,", "they", "vanished."]
    assert words[0].start == 0.0 and words[2].start == 1.4
    assert words[0].end <= words[1].start <= words[2].start
