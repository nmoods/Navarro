"""Persists Story Director output (script versions, storyboards, scenes) for a project."""

from __future__ import annotations

import random
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.application.narrative import analyse
from app.application.story_director import CreativeContext, StoryDirector
from app.domain.enums import JobStatus, ProjectStatus
from app.domain.story import SceneDraft
from app.infrastructure.database.models import (
    ContentSeries,
    Project,
    Scene,
    ScriptVersion,
    SeriesEpisode,
    Storyboard,
    StoryDnaProfile,
)
from app.workers.context import JobContext


def creative_context(session: Session, project: Project, hook_style: str | None = None) -> CreativeContext:
    s = project.settings
    dna_notes, continuity = "", ""
    if project.story_dna_id and (dna := session.get(StoryDnaProfile, project.story_dna_id)):
        dna_notes = (
            f"CREATOR STORY DNA '{dna.name}': {dna.description}\nVisual identity: {dna.style_prompt}\n"
            f"Palette: {', '.join(dna.color_palette)}. Preferred camera moves: "
            f"{', '.join(dna.animation_preferences.get('camera', [])) or 'any'}."
        )
    if project.series_id and (series := session.get(ContentSeries, project.series_id)):
        bible = series.bible or {}
        chars = "; ".join(f"{c['name']}: {c['visual_description']}" for c in bible.get("recurring_characters", []))
        episode = session.scalar(select(SeriesEpisode).where(SeriesEpisode.project_id == project.id))
        continuity = (
            f"SERIES BIBLE for '{series.title}': {bible.get('logline', '')}\nVisual style: {bible.get('visual_style_notes', '')}\n"
            f"Recurring characters (reuse exact descriptions): {chars or 'none'}\n"
            f"Recurring locations: {', '.join(bible.get('recurring_locations', [])) or 'none'}\n"
            + (f"This is episode {episode.position + 1}: {episode.premise}. Continuity: {episode.continuity_note}" if episode else "")
        )
    return CreativeContext(
        topic=project.topic, duration=s.duration_seconds, tone=s.story_tone, platform=s.platform, language=s.language,
        visual_style=s.visual_style, dna_notes=dna_notes, continuity=continuity, preferred_hook_style=hook_style,
    )  # fmt: skip


def current_storyboard(session: Session, project_id: uuid.UUID) -> Storyboard | None:
    return session.scalar(
        select(Storyboard).where(Storyboard.project_id == project_id, Storyboard.is_current.is_(True)).order_by(Storyboard.version.desc())
    )


def latest_script(session: Session, project_id: uuid.UUID) -> ScriptVersion | None:
    return session.scalar(select(ScriptVersion).where(ScriptVersion.project_id == project_id).order_by(ScriptVersion.version.desc()))


def scene_from_draft(draft: SceneDraft, *, storyboard_id: uuid.UUID, project_id: uuid.UUID, position: int,
                     default_palette: list[str]) -> Scene:  # fmt: skip
    first_transition = "cut" if position == 0 else draft.transition.value
    return Scene(
        storyboard_id=storyboard_id, project_id=project_id, position=position, title=draft.title, narration=draft.narration,
        visual_type=draft.visual_type.value, visual_description=draft.visual_description, image_prompt=draft.image_prompt,
        characters=draft.characters, camera_movement=draft.camera_movement.value, effects=[e.value for e in draft.effects],
        transition=first_transition, emphasis_words=draft.emphasis_words, sound_effects=[s.value for s in draft.sound_effects],
        music_cue=draft.music_cue, mood=draft.mood, color_palette=draft.color_palette or default_palette,
        visual_data=draft.visual_data.model_dump(exclude_none=True), image_seed=random.randint(1, 2**31 - 1),  # noqa: S311
    )  # fmt: skip


def save_storyboard(session: Session, project: Project, script: ScriptVersion, scenes: list[SceneDraft],
                    default_palette: list[str]) -> Storyboard:  # fmt: skip
    session.execute(update(Storyboard).where(Storyboard.project_id == project.id).values(is_current=False))
    version = (session.scalar(select(func.max(Storyboard.version)).where(Storyboard.project_id == project.id)) or 0) + 1
    board = Storyboard(project_id=project.id, script_id=script.id, version=version, is_current=True,
                       analysis=analyse([s.narration for s in scenes], script.content.get("hook", "")))  # fmt: skip
    session.add(board)
    session.flush()
    for i, draft in enumerate(scenes):
        session.add(scene_from_draft(draft, storyboard_id=board.id, project_id=project.id, position=i, default_palette=default_palette))
    session.flush()
    return board


def project_palette(session: Session, project: Project) -> list[str]:
    if project.story_dna_id and (dna := session.get(StoryDnaProfile, project.story_dna_id)) and dna.color_palette:
        return list(dna.color_palette)[:3]
    return []


def generate_story(session: Session, director: StoryDirector, project: Project, ctx: JobContext,
                   *, hook_index: int | None = None, hook_style: str | None = None, fact_check: bool = True) -> Storyboard:  # fmt: skip
    """Full Story Director run with progress reporting. Commits after each step so work is never lost."""
    project.status = ProjectStatus.GENERATING_STORY.value
    session.commit()
    cc = creative_context(session, project, hook_style)
    research_ok = False
    if project.settings.fact_check_enabled and director.research:
        health = director.research.health()
        research_ok = health.available
        if not research_ok:
            ctx.log("warning", f"Fact checking unavailable: {health.detail}")
    ctx.stage(JobStatus.SCRIPT_GENERATION, 3, "Researching the subject" if research_ok else "Skipping research (offline)")
    reference, sources = director.gather_reference(cc.topic) if research_ok else ("", [])
    ctx.stage(JobStatus.SCRIPT_GENERATION, 8, "Story Director is analysing the topic")
    brief = director.generate_brief(cc, reference)
    ctx.stage(JobStatus.SCRIPT_GENERATION, 18, "Hook Lab: writing alternative hooks")
    hooks = director.generate_hooks(cc, brief)
    chosen = hook_index if hook_index is not None and 0 <= hook_index < len(hooks) else director.pick_hook(hooks, cc)
    ctx.stage(JobStatus.SCRIPT_GENERATION, 28, "Writing the narration")
    script = director.generate_script(cc, brief, hooks[chosen].text)
    claims = script.claims or brief.key_facts
    if fact_check and research_ok:
        ctx.stage(JobStatus.SCRIPT_GENERATION, 40, "Fact checker: verifying claims against sources")
        claims = director.fact_check(claims)
    version = (session.scalar(select(func.max(ScriptVersion.version)).where(ScriptVersion.project_id == project.id)) or 0) + 1
    row = ScriptVersion(
        project_id=project.id, version=version, title=script.title, brief=brief.model_dump(mode="json") | {
            "sources": [{"title": s.title, "url": s.url} for s in sources]},
        hooks=[h.model_dump(mode="json") for h in hooks], selected_hook_index=chosen,
        content=script.model_dump(mode="json", exclude={"claims"}), full_text=script.full_text,
        claims=[c.model_dump(mode="json") for c in claims], model=getattr(director.llm, "model", None),
    )  # fmt: skip
    session.add(row)
    project.title = script.title[:120]
    session.commit()
    ctx.stage(JobStatus.STORYBOARD_GENERATION, 50, "Storyboard: directing scenes and choosing visuals")
    board_draft = director.generate_storyboard(cc, script)
    board = save_storyboard(session, project, row, list(board_draft.scenes), project_palette(session, project))
    project.status = ProjectStatus.STORYBOARD_READY.value
    session.commit()
    return board
