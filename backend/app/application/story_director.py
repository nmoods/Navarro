"""AI Story Director: story (hooks, narration, claims) -> storyboard -> fact check. Pure orchestration over ports
(no database), so it is provider-agnostic and unit-testable with the fixture LLM."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.application import prompts
from app.application.direction import polish_scene, polish_storyboard
from app.application.narrative import split_into_scenes
from app.application.ports import LLMProvider, ResearchProvider, Source
from app.core.errors import ProviderError
from app.domain.enums import ClaimVerdict, HookStyle
from app.domain.story import (
    Claim,
    ClaimCheck,
    SceneDraft,
    SeriesPlan,
    StoryboardDraft,
    StoryboardPlan,
    StoryDraft,
    TopicIdeas,
    scene_count_for_duration,
    words_for_duration,
)

logger = logging.getLogger("narravo.director")
_TITLE_STOP = frozenset("the a an of and in on at to for with from how why what who when where is was".split())


@dataclass
class CreativeContext:
    """Everything that shapes the story beyond the topic (project settings + Story DNA + series bible)."""

    topic: str
    duration: int = 60
    tone: str = "documentary"
    platform: str = "tiktok"
    language: str = "en"
    visual_style: str = "cinematic_documentary"
    dna_notes: str = ""
    continuity: str = ""
    preferred_hook_style: str | None = None
    forced_hook: str | None = None  # Hook Lab: the exact opening line the creator picked


class StoryDirector:
    def __init__(self, llm: LLMProvider, research: ResearchProvider | None = None) -> None:
        self.llm = llm
        self.research = research

    # -- research -----------------------------------------------------------------------------------
    def gather_reference(self, topic: str) -> tuple[str, list[Source]]:
        if not self.research:
            return "", []
        try:
            hits = self.research.search_sources(topic, limit=1)  # one focused article; a second often mixes in another story
            sources = [s for s in (self.research.retrieve_source(h.title) for h in hits[:1]) if s and s.excerpt]
        except Exception as exc:  # research is optional: degrade, never fail the story
            logger.warning("research unavailable: %s", exc)
            return "", []
        text = "\n\n".join(f"[{s.title}] {s.excerpt[:4000]}" for s in sources)
        return text[:4500], sources

    # -- steps ------------------------------------------------------------------------------------------
    def write_story(self, ctx: CreativeContext, reference: str) -> StoryDraft:
        """Angle, three hooks, narration and claims in one LLM call (one pass is ~3x faster than four)."""
        words = words_for_duration(ctx.duration)
        hook_style = ctx.preferred_hook_style or (
            HookStyle.MYSTERIOUS.value if ctx.tone in ("suspenseful", "dramatic") else HookStyle.CURIOSITY.value
        )
        prompt = prompts.story_prompt(ctx.topic, ctx.tone, ctx.language, reference, words, ctx.dna_notes, hook_style,
                                      ctx.forced_hook)  # fmt: skip
        draft = self.llm.complete_json(prompts.DIRECTOR_SYSTEM, prompt, StoryDraft, temperature=0.75)
        actual = len(draft.to_script().full_text.split())
        if not (0.6 * words <= actual <= 1.5 * words):
            logger.info("script length %d far from target %d, asking for a revision", actual, words)
            prompt += f"\n\nYour previous draft had {actual} words. Rewrite it to about {words} words."
            draft = self.llm.complete_json(prompts.DIRECTOR_SYSTEM, prompt, StoryDraft, temperature=0.6)
        if ctx.forced_hook:
            first = draft.hooks[0].model_copy(update={"text": ctx.forced_hook})
            draft = draft.model_copy(update={"hooks": [first, *draft.hooks[1:]]})
        return draft

    def generate_storyboard(self, ctx: CreativeContext, full_text: str) -> StoryboardDraft:
        scenes_text = split_into_scenes(full_text, scene_count_for_duration(ctx.duration))
        plan = self.llm.complete_json(
            prompts.DIRECTOR_SYSTEM,
            prompts.storyboard_prompt(ctx.topic, ctx.visual_style, scenes_text, ctx.dna_notes, ctx.continuity),
            StoryboardPlan,
            temperature=0.7,
        )
        return polish_storyboard(self.attach_narration(plan, scenes_text), ctx.visual_style)

    @staticmethod
    def attach_narration(plan: StoryboardPlan, scenes_text: list[str]) -> StoryboardDraft:
        """The approved script survives verbatim: narration always comes from our split, never from the LLM."""
        scenes = list(plan.scenes)
        if not scenes:
            raise ProviderError("llm", "Storyboard contained no scenes")
        while len(scenes) < len(scenes_text):  # small models sometimes return fewer scenes
            scenes.append(scenes[-1].model_copy(update={"title": f"Scene {len(scenes) + 1}"}))
        fixed = []
        for scene, text in zip(scenes[: len(scenes_text)], scenes_text, strict=True):
            draft = scene.to_draft(text)
            words = set(text.lower().split())
            emphasis = [w for w in draft.emphasis_words if w in words or any(w in t for t in words)][:3]
            fixed.append(draft.model_copy(update={"emphasis_words": emphasis}))
        return StoryboardDraft(scenes=fixed)

    def regenerate_scene(self, ctx: CreativeContext, narration: str, previous: str, following: str, instruction: str,
                         rewrite_narration: bool) -> SceneDraft:  # fmt: skip
        scene = self.llm.complete_json(
            prompts.DIRECTOR_SYSTEM,
            prompts.scene_prompt(ctx.topic, ctx.visual_style, narration, previous, following, instruction, rewrite_narration),
            SceneDraft,
            temperature=0.9,
        )
        if not rewrite_narration:
            scene = scene.model_copy(update={"narration": narration})
        return polish_scene(scene, ctx.visual_style, 0, None)

    def fact_check(self, claims: list[Claim], max_claims: int = 3) -> list[Claim]:
        if not self.research:
            return claims
        cache: dict[str, Source | None] = {}
        checked = []
        for i, claim in enumerate(claims):
            if i >= max_claims:
                checked.append(claim)
                continue
            try:
                hits = self.research.search_sources(claim.text, limit=1)
                if not hits:
                    checked.append(claim.model_copy(update={"verdict": ClaimVerdict.NOT_FOUND}))
                    continue
                title = hits[0].title
                if title not in cache:
                    cache[title] = self.research.retrieve_source(title)
                src = cache[title]
                if not src:
                    checked.append(claim.model_copy(update={"verdict": ClaimVerdict.NOT_FOUND}))
                    continue
                result = self.llm.complete_json(
                    prompts.DIRECTOR_SYSTEM, prompts.claim_prompt(claim.text, src.excerpt, src.title), ClaimCheck, temperature=0.1
                )
                checked.append(claim.model_copy(update={"verdict": result.verdict, "note": result.explanation, "sources": [src.url]}))
            except Exception as exc:  # one failed check must not fail the job
                logger.warning("fact check failed for claim %d: %s", i, exc)
                checked.append(claim)
        return checked

    def plan_series(self, theme: str, count: int, tone: str, existing: list[str]) -> SeriesPlan:
        plan = self.llm.complete_json(prompts.DIRECTOR_SYSTEM, prompts.series_prompt(theme, count, tone, existing),
                                      SeriesPlan, temperature=0.9)  # fmt: skip
        return self.dedupe_episodes(plan, existing)

    @staticmethod
    def _title_tokens(title: str) -> frozenset[str]:
        text = re.sub(r"^\s*(episode|ep|part|chapter)\s*\d+\s*[:.\-–]\s*", "", title.lower())
        return frozenset(w for w in re.findall(r"[a-z0-9']+", text) if w not in _TITLE_STOP)

    @classmethod
    def dedupe_episodes(cls, plan: SeriesPlan, existing: list[str], threshold: float = 0.6) -> SeriesPlan:
        """Drop near-duplicate episodes (word-overlap Jaccard on meaningful title words)."""
        kept, seen = [], [cls._title_tokens(t) for t in existing]
        for ep in plan.episodes:
            tokens = cls._title_tokens(ep.title)
            if tokens and any(len(tokens & s) / max(1, len(tokens | s)) >= threshold for s in seen if s):
                continue
            kept.append(ep)
            seen.append(tokens)
        return plan.model_copy(update={"episodes": kept or plan.episodes[:1]})

    def suggest_topics(self, theme: str, count: int) -> TopicIdeas:
        return self.llm.complete_json(prompts.DIRECTOR_SYSTEM, prompts.ideas_prompt(theme, count), TopicIdeas, temperature=1.0)
