"""Direction polish: deterministic post-processing of LLM storyboards.

Small local models often pick the right *kind* of visual but leave its data empty (a timeline with no
dates, a map with no places), repeat one camera move, or skip atmosphere entirely. This pass:

* fills visual data from the scene's own narration (years -> timeline, known places -> map, numbers ->
  infographic, quotes -> kinetic lines), using only facts present in the approved text;
* downgrades a procedural visual to an image-based one when there is still nothing to show;
* varies camera moves and adds style-appropriate atmosphere when the model left them flat;
* never changes narration.
"""

from __future__ import annotations

import re

from app.domain.enums import CameraMove, Effect, VisualType
from app.domain.story import Place, SceneDraft, Statistic, StoryboardDraft, TimelineEvent
from app.media.visuals.geo import _gazetteer, _norm

_YEAR = re.compile(r"\b(1[0-9]{3}|20[0-4][0-9])\b")
_NUMBER = re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(%|percent|million|thousand|km|miles|people|settlers|soldiers|years|days|ships)?(?!\w)", re.I)
_WORD_NUMBERS = {"hundred": 100, "thousand": 1000, "million": 1_000_000}
_STOP_LABEL = {"in", "on", "at", "by", "the", "a", "an", "of", "and", "to", "from", "was", "were", "for"}

STYLE_ATMOSPHERE: dict[str, list[tuple[Effect, ...]]] = {
    "dark_mystery": [(Effect.FOG,), (Effect.DUST,), (Effect.FOG, Effect.FLICKER), (Effect.SMOKE,)],
    "vintage_documentary": [(Effect.FILM_GRAIN, Effect.DUST), (Effect.FILM_GRAIN,), (Effect.FLICKER, Effect.FILM_GRAIN)],
    "archival_newspaper": [(Effect.FILM_GRAIN,), (Effect.DUST,)],
    "historical_realism": [(Effect.DUST,), (Effect.LIGHT_RAYS,), (Effect.SMOKE,), ()],
    "cinematic_documentary": [(Effect.LIGHT_RAYS,), (Effect.DUST,), (), (Effect.FOG,)],
    "anime": [(Effect.BOKEH,), (Effect.LIGHT_RAYS,), ()],
    "animation_3d": [(Effect.BOKEH,), (), (Effect.LIGHT_RAYS,)],
    "illustrated": [(Effect.DUST,), (), (Effect.BOKEH,)],
    "photorealistic": [(), (Effect.LIGHT_RAYS,), (Effect.DUST,)],
    "minimalist_motion": [(), ()],
}
IMAGE_CAMERAS = [CameraMove.SLOW_ZOOM_IN, CameraMove.KEN_BURNS, CameraMove.PAN_RIGHT, CameraMove.DRAMATIC_PUSH_IN,
                 CameraMove.TILT_UP, CameraMove.PAN_LEFT, CameraMove.SLOW_ZOOM_OUT]  # fmt: skip


def _label_after(text: str, end: int, words: int = 4) -> str:
    clause = re.split(r"[.!?;,:]", text[end : end + 80], maxsplit=1)[0]
    tail = re.findall(r"[A-Za-z']+", clause)
    picked = [w for w in tail if w.lower() not in _STOP_LABEL][:words]
    return " ".join(picked).capitalize() or "Event"


def extract_events(text: str) -> list[TimelineEvent]:
    events, seen = [], set()
    for m in _YEAR.finditer(text):
        year = m.group(1)
        if year in seen:
            continue
        seen.add(year)
        events.append(TimelineEvent(date=year, label=_label_after(text, m.end())[:80]))
    return events[:5]


def extract_places(text: str) -> list[Place]:
    gaz = _gazetteer()
    norm = _norm(text)
    found: list[tuple[int, str]] = []
    tokens = norm.split()
    for size in (3, 2, 1):
        for i in range(len(tokens) - size + 1):
            phrase = " ".join(tokens[i : i + size])
            if len(phrase) > 3 and phrase in gaz and not any(phrase in f for _, f in found):
                found.append((i, phrase))
    found.sort()
    titled = []
    for _, phrase in found:
        match = re.search(re.escape(phrase), text, re.I)
        titled.append(match.group(0) if match else phrase.title())
    return [Place(name=n[:80]) for n in dict.fromkeys(titled)][:5]


def extract_stats(text: str) -> list[Statistic]:
    stats = []
    for m in _NUMBER.finditer(text):
        raw, unit = m.group(1), (m.group(2) or "")
        if _YEAR.fullmatch(raw):
            continue
        value = float(raw.replace(",", ""))
        pct = unit.lower() in ("%", "percent")
        label = _label_after(text, m.end(), 3) if (not unit or pct) else unit.capitalize()
        stats.append(Statistic(label=label[:60], value=value, unit="%" if pct else ""))
    for word, mult in _WORD_NUMBERS.items():
        m = re.search(rf"\b(one|two|three|four|five|ten|a)?\s*{word}(?: and (\w+))?\s+([a-z]+)", text, re.I)
        if m and not stats:
            stats.append(Statistic(label=m.group(3).capitalize(), value=float(mult), unit=""))
    return stats[:4]


def kinetic_lines(text: str, max_lines: int = 3) -> list[str]:
    """Break narration into short on-screen phrases at natural clause boundaries (never mid-phrase)."""
    clauses = [c.strip(" ,;:—-") for c in re.split(r"[.!?;:,—]+", text) if c.strip(" ,;:—-")]
    lines: list[str] = []
    for clause in clauses:
        words = clause.split()
        while words and len(lines) < max_lines:
            take = len(words) if len(words) <= 6 else min(5, len(words) - 2)
            lines.append(" ".join(words[:take]))
            words = words[take:]
        if len(lines) >= max_lines:
            break
    return lines


def polish_scene(scene: SceneDraft, style: str, index: int, previous_camera: str | None) -> SceneDraft:
    vt = scene.visual_type
    data = scene.visual_data.model_copy()
    text = scene.narration
    updates: dict = {}
    if vt is VisualType.TIMELINE and len(data.events) < 2:
        events = extract_events(text)
        if len(events) >= 2:
            data.events = events
        elif len(events) == 1:
            data.headline, data.dateline = scene.title[:90], events[0].date
            vt = VisualType.NEWSPAPER if style in ("archival_newspaper", "vintage_documentary") else VisualType.CINEMATIC_IMAGE
        else:
            vt = VisualType.CINEMATIC_IMAGE
    elif vt is VisualType.HISTORICAL_MAP and not data.places:
        places = extract_places(text)
        if places:
            data.places, data.draw_route = places, len(places) > 1
        else:
            vt = VisualType.PARALLAX
    elif vt is VisualType.INFOGRAPHIC and not data.stats:
        stats = extract_stats(text)
        if stats:
            data.stats = stats
        else:
            vt = VisualType.KINETIC_TYPOGRAPHY
    elif vt is VisualType.COMPARISON and not (data.left and data.right and (data.left.points or data.right.points)):
        vt = VisualType.CINEMATIC_IMAGE
    if vt is VisualType.NEWSPAPER and not data.headline:
        data.headline = scene.title[:90]
    if vt is VisualType.KINETIC_TYPOGRAPHY and not data.kinetic_lines:
        data.kinetic_lines = kinetic_lines(text)
    updates["visual_type"], updates["visual_data"] = vt, data

    camera = scene.camera_movement
    if vt.needs_ai_image and (camera is CameraMove.STATIC or camera.value == previous_camera):
        camera = IMAGE_CAMERAS[index % len(IMAGE_CAMERAS)]
        if camera.value == previous_camera:
            camera = IMAGE_CAMERAS[(index + 1) % len(IMAGE_CAMERAS)]
    if vt is VisualType.PARALLAX and camera not in (CameraMove.PARALLAX_DRIFT, CameraMove.PAN_LEFT, CameraMove.PAN_RIGHT):
        camera = CameraMove.PARALLAX_DRIFT
    updates["camera_movement"] = camera
    if not scene.effects and vt.needs_ai_image:
        options = STYLE_ATMOSPHERE.get(style, [()])
        updates["effects"] = list(options[index % len(options)])
    return scene.model_copy(update=updates)


def polish_storyboard(board: StoryboardDraft, style: str) -> StoryboardDraft:
    scenes, previous = [], None
    for i, scene in enumerate(board.scenes):
        polished = polish_scene(scene, style, i, previous)
        scenes.append(polished)
        previous = polished.camera_movement.value
    return StoryboardDraft(scenes=scenes)
