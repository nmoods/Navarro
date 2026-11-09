"""AI Story Director: brief -> hooks -> script -> storyboard -> fact check. Pure orchestration over ports
(no database), so it is provider-agnostic and unit-testable with the fixture LLM."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.application import prompts
from app.application.narrative import split_into_scenes
from app.application.ports import LLMProvider, ResearchProvider, Source
from app.core.errors import ProviderError
from app.domain.enums import ClaimVerdict, HookStyle
from app.domain.story import (
    Claim,
    ClaimCheck,
    Hook,
    HookSet,
    SceneDraft,
    Script,
    SeriesPlan,
    StoryboardDraft,
    StoryBrief,
    TopicIdeas,
    scene_count_for_duration,
    words_for_duration,
)

logger = logging.getLogger("reelforge.director")
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


@dataclass
class StoryResult:
    brief: StoryBrief
    hooks: list[Hook]
    selected_hook: int
    script: Script
    storyboard: StoryboardDraft
    sources: list[Source] = field(default_factory=list)


class StoryDirector:
    def __init__(self, llm: LLMProvider, research: ResearchProvider | None = None) -> None:
        self.llm = llm
        self.research = research

    # -- research -----------------------------------------------------------------------------------
    def gather_reference(self, topic: str) -> tuple[str, list[Source]]:
        if not self.research:
            return "", []
        try:
            hits = self.research.search_sources(topic, limit=2)
            sources = [s for s in (self.research.retrieve_source(h.title) for h in hits[:2]) if s and s.excerpt]
        except Exception as exc:  # research is optional: degrade, never fail the story
            logger.warning("research unavailable: %s", exc)
            return "", []
        text = "\n\n".join(f"[{s.title}] {s.excerpt[:2500]}" for s in sources)
        return text[:4500], sources

    # -- steps ------------------------------------------------------------------------------------------
    def generate_brief(self, ctx: CreativeContext, reference: str) -> StoryBrief:
        return self.llm.complete_json(
            prompts.DIRECTOR_SYSTEM,
            prompts.brief_prompt(ctx.topic, ctx.tone, ctx.platform, ctx.language, reference),
            StoryBrief,
            temperature=0.4,
        )

    def generate_hooks(self, ctx: CreativeContext, brief: StoryBrief) -> list[Hook]:
        result = self.llm.complete_json(
            prompts.DIRECTOR_SYSTEM, prompts.hooks_prompt(ctx.topic, brief.model_dump_json()), HookSet, temperature=0.9
        )
        return result.hooks

    @staticmethod
    def pick_hook(hooks: list[Hook], ctx: CreativeContext) -> int:
        preferred = ctx.preferred_hook_style or (
            HookStyle.MYSTERIOUS if ctx.tone in ("suspenseful", "dramatic") else HookStyle.CURIOSITY
        )
        for i, hook in enumerate(hooks):
            if hook.style == preferred:
                return i
        return 0

    def generate_script(self, ctx: CreativeContext, brief: StoryBrief, hook: str) -> Script:
        words = words_for_duration(ctx.duration)
        prompt = prompts.script_prompt(ctx.topic, brief.model_dump_json(), hook, words, ctx.tone, ctx.language, ctx.dna_notes)
        script = self.llm.complete_json(prompts.DIRECTOR_SYSTEM, prompt, Script, temperature=0.75)
        actual = len(script.full_text.split())
        if not (0.6 * words <= actual <= 1.5 * words):
            logger.info("script length %d far from target %d, asking for a revision", actual, words)
            prompt += f"\n\nYour previous draft had {actual} words. Rewrite it to about {words} words."
            script = self.llm.complete_json(prompts.DIRECTOR_SYSTEM, prompt, Script, temperature=0.6)
        script.hook = hook or script.hook
        return script

    def generate_storyboard(self, ctx: CreativeContext, script: Script) -> StoryboardDraft:
        scenes_text = split_into_scenes(script.full_text, scene_count_for_duration(ctx.duration))
        draft = self.llm.complete_json(
            prompts.DIRECTOR_SYSTEM,
            prompts.storyboard_prompt(ctx.topic, ctx.visual_style, scenes_text, ctx.dna_notes, ctx.continuity),
            StoryboardDraft,
            temperature=0.7,
        )
        return self.enforce_narration(draft, scenes_text)

    @staticmethod
    def enforce_narration(draft: StoryboardDraft, scenes_text: list[str]) -> StoryboardDraft:
        """Guarantee the approved script survives verbatim: narration always comes from our split."""
        scenes = list(draft.scenes)
        while len(scenes) < len(scenes_text):  # small models sometimes return fewer scenes
            template = scenes[-1] if scenes else None
            if template is None:
                raise ProviderError("llm", "Storyboard contained no scenes")
            scenes.append(template.model_copy(update={"title": f"Scene {len(scenes) + 1}"}))
        scenes = scenes[: len(scenes_text)]
        fixed = []
        for scene, text in zip(scenes, scenes_text, strict=True):
            words = set(text.lower().split())
            emphasis = [w for w in scene.emphasis_words if w in words or any(w in t for t in words)][:3]
            fixed.append(scene.model_copy(update={"narration": text, "emphasis_words": emphasis}))
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
        return scene

    def fact_check(self, claims: list[Claim], max_claims: int = 6) -> list[Claim]:
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
