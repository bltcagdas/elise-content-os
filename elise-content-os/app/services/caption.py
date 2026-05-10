import json
import logging
import time
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.models import ScenePrompt, utc_now
from app.schemas import CaptionPackage, TriggerTime
from app.services.knowledge import KnowledgeLoader

logger = logging.getLogger(__name__)


class CaptionGenerationError(RuntimeError):
    pass


class CaptionService:
    def __init__(self, settings: Settings | None = None, loader: KnowledgeLoader | None = None) -> None:
        self.settings = settings or get_settings()
        self.loader = loader or KnowledgeLoader(self.settings)

    def generate(
        self,
        *,
        scene: ScenePrompt,
        trigger_time: TriggerTime,
        monthly_focus: str | None,
        recent_captions: list[str],
        dry_run: bool = False,
    ) -> CaptionPackage:
        knowledge = self.loader.load()
        watch = self._current_watch(knowledge.character_state)
        shoes = self._select_shoes(knowledge.character_state, scene.prompt)

        if dry_run:
            return self._dry_run_package(scene, trigger_time, monthly_focus, watch, shoes)

        client = OpenAI(api_key=self.settings.require_openai_key(), timeout=30)
        system_prompt = self._system_prompt(knowledge.brand_voice)
        user_prompt = self._user_prompt(
            scene=scene,
            trigger_time=trigger_time,
            monthly_focus=monthly_focus,
            recent_captions=recent_captions,
            character_state=knowledge.character_state,
            monthly_tracker_text=knowledge.monthly_tracker_text,
            watch=watch,
            shoes=shoes,
        )

        last_error: Exception | None = None
        for model in self._model_chain():
            for attempt in range(1, 4):
                try:
                    response = client.responses.create(
                        model=model,
                        input=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        text={
                            "format": {
                                "type": "json_schema",
                                "name": "caption_package",
                                "strict": True,
                                "schema": self._caption_json_schema(),
                            }
                        },
                    )
                    payload = json.loads(response.output_text)
                    package = CaptionPackage.model_validate(payload)
                    return self._with_required_image_brief_context(package, scene, watch, shoes)
                except Exception as exc:
                    last_error = exc
                    error_type = self._classify_error(exc)
                    logger.warning(
                        "openai_generation_failed",
                        extra={
                            "error_type": error_type,
                            "model": model,
                            "attempt": attempt,
                            "scene_id": scene.scene_id,
                            "status": "retrying",
                        },
                    )
                    if error_type == "model_unavailable":
                        break
                    time.sleep(min(2 ** (attempt - 1), 8))

        raise CaptionGenerationError(f"Caption generation failed after retries: {last_error}")

    def smoke_test(self) -> CaptionPackage:
        scene = ScenePrompt(
            scene_id="smoke",
            filename="smoke.jpg",
            group="A_closeup",
            shot="close-up",
            prompt="Dubai apartment morning window light, white ceramic cup, quiet expression.",
            kohya_caption="EliseVerneV1, close up portrait, freckles, Dubai window light",
            source="smoke-test",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.generate(
            scene=scene,
            trigger_time="morning",
            monthly_focus=None,
            recent_captions=[],
            dry_run=False,
        )

    def _caption_json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "content_type",
                "image_brief",
                "caption",
                "caption_formula",
                "hashtags",
                "publishing_note",
                "monthly_checklist_fulfilled",
                "watch_used",
                "shoes_used",
            ],
            "properties": {
                "content_type": {"type": "string", "enum": ["story", "feed_post", "reel", "carousel"]},
                "image_brief": {"type": "string"},
                "caption": {"type": "string"},
                "caption_formula": {"type": "string"},
                "hashtags": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 5,
                    "items": {"type": "string"},
                },
                "publishing_note": {"type": "string"},
                "monthly_checklist_fulfilled": {"type": ["string", "null"]},
                "watch_used": {"type": ["string", "null"]},
                "shoes_used": {"type": ["string", "null"]},
            },
        }

    def _dry_run_package(
        self,
        scene: ScenePrompt,
        trigger_time: TriggerTime,
        monthly_focus: str | None,
        watch: str | None,
        shoes: str | None,
    ) -> CaptionPackage:
        package = CaptionPackage(
            content_type="story",
            image_brief=(
                f"DRY RUN: Create scene {scene.scene_id} for a {trigger_time} story. "
                f"Use this scene prompt: {scene.prompt}. Render watch: {watch or 'current watch'}. "
                f"Render shoes when visible: {shoes or 'context-appropriate shoes'}."
            ),
            caption="quiet light before the day starts.",
            caption_formula="formula_1",
            hashtags=["#quietluxury", "#dubailife", "#visualdiary"],
            publishing_note=f"Dry-run plan for {trigger_time}; focus={monthly_focus or 'rotation'}.",
            monthly_checklist_fulfilled=monthly_focus,
            watch_used=watch,
            shoes_used=shoes,
        )
        return self._with_required_image_brief_context(package, scene, watch, shoes)

    def _model_chain(self) -> list[str]:
        models = [self.settings.openai_model]
        fallback = self.settings.openai_fallback_model
        if fallback and fallback not in models:
            models.append(fallback)
        return models

    def _classify_error(self, exc: Exception) -> str:
        if isinstance(exc, ValidationError) or isinstance(exc, json.JSONDecodeError):
            return "invalid_schema"
        if isinstance(exc, RateLimitError):
            return "rate_limit"
        if isinstance(exc, APITimeoutError):
            return "timeout"
        if isinstance(exc, APIConnectionError):
            return "connection_error"
        if isinstance(exc, APIStatusError):
            if exc.status_code in {404, 410}:
                return "model_unavailable"
            if exc.status_code in {429}:
                return "rate_limit"
            if exc.status_code >= 500:
                return "server_error"
            return "api_status_error"
        return exc.__class__.__name__

    def _with_required_image_brief_context(
        self,
        package: CaptionPackage,
        scene: ScenePrompt,
        watch: str | None,
        shoes: str | None,
    ) -> CaptionPackage:
        required = self._required_image_brief_context(scene, watch, shoes)
        if required.lower() in package.image_brief.lower():
            return package
        return package.model_copy(update={"image_brief": f"{required}\n\nScene brief:\n{package.image_brief}"})

    def _required_image_brief_context(self, scene: ScenePrompt, watch: str | None, shoes: str | None) -> str:
        distance = {
            "A_closeup": "CLOSE-UP: 8-12 freckles on nose bridge and 15-20 faint freckles across upper cheeks must be visible.",
            "B_waist_up": "MEDIUM: freckles subtly present on nose bridge, less prominent.",
            "C_full_body": "WIDE: freckles softly blended and imperceptible; do not render individual freckles.",
            "D_detail": "DETAIL: apply freckles only if face is visible; otherwise prioritize object realism.",
        }.get(scene.group, "Use scene-appropriate freckle distance behavior.")
        return (
            "Elise DNA: 26-year-old Northern European woman, 178cm lean ectomorph build, "
            "dark chestnut straight hair just below shoulders, light hazel green-grey eyes, "
            "soft oval face with subtly structured jaw, straight European nose with slight asymmetric tip, "
            "natural NC25 light-medium skin texture, default right-corner micro-smirk. "
            f"Freckle rule: {distance} "
            f"Watch: {watch or 'current watch from character state'} on left wrist when visible. "
            f"Shoes: {shoes or 'context-appropriate shoes'} when visible. "
            "Photo style: hyperrealistic natural light editorial fashion, quiet luxury, slight film grain, never over-smoothed AI skin."
        )

    def _system_prompt(self, brand_voice: str) -> str:
        return (
            "You are the planning and caption assistant for Elise Verne, a Dubai-based AI influencer. "
            "Return only valid JSON matching the provided schema. Preserve the brand voice rules exactly.\n\n"
            f"BRAND VOICE:\n{brand_voice}"
        )

    def _user_prompt(
        self,
        *,
        scene: ScenePrompt,
        trigger_time: TriggerTime,
        monthly_focus: str | None,
        recent_captions: list[str],
        character_state: dict[str, Any],
        monthly_tracker_text: str,
        watch: str | None,
        shoes: str | None,
    ) -> str:
        character_brief = {
            "identity": character_state.get("identity", {}),
            "location": character_state.get("location", {}),
            "physical": character_state.get("physical", {}),
            "image_generation": character_state.get("image_generation", {}),
            "character_memory": character_state.get("character_memory", {}),
        }
        return json.dumps(
            {
                "task": "Produce one human-in-the-loop Instagram content package.",
                "trigger_time": trigger_time,
                "scene": {
                    "scene_id": scene.scene_id,
                    "group": scene.group,
                    "shot": scene.shot,
                    "prompt": scene.prompt,
                    "kohya_caption": scene.kohya_caption,
                },
                "character_state": character_brief,
                "current_watch": watch,
                "selected_shoes": shoes,
                "monthly_focus": monthly_focus,
                "monthly_tracker_excerpt": monthly_tracker_text[:4000],
                "recent_captions_to_avoid": recent_captions[-10:],
                "hard_rules": [
                    "Caption is 1-3 lines.",
                    "Caption never starts with I.",
                    "No exclamation marks.",
                    "No forbidden words from brand voice.",
                    "Hashtags are 3-5 items and not inside the caption.",
                    "Image brief must mention the current watch and context-appropriate shoes.",
                    "Image brief must include the correct freckle distance behavior for the shot.",
                ],
            },
            ensure_ascii=False,
        )

    def _current_watch(self, character_state: dict[str, Any]) -> str | None:
        return character_state.get("watches", {}).get("current_wrist")

    def _select_shoes(self, character_state: dict[str, Any], scene_prompt: str) -> str | None:
        shoes = character_state.get("wardrobe", {}).get("shoes_current_month", {}).get("rotation", [])
        if not shoes:
            return None
        prompt = scene_prompt.lower()
        for item in shoes:
            context = str(item.get("context", "")).lower()
            label = str(item.get("item", ""))
            if any(token in prompt or token in context for token in ["gym", "travel", "office", "evening", "coffee", "home"]):
                if any(token in prompt for token in context.split()):
                    return label
        if "gym" in prompt:
            return self._shoe_by_context(shoes, "gym") or shoes[0].get("item")
        if "dinner" in prompt or "evening" in prompt:
            return self._shoe_by_context(shoes, "evening") or shoes[0].get("item")
        if "home" in prompt or "kitchen" in prompt:
            return self._shoe_by_context(shoes, "home") or shoes[0].get("item")
        return shoes[0].get("item")

    def _shoe_by_context(self, shoes: list[dict[str, Any]], token: str) -> str | None:
        for shoe in shoes:
            if token in str(shoe.get("context", "")).lower():
                return shoe.get("item")
        return None
