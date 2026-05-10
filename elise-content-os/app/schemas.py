from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


TriggerTime = Literal["morning", "afternoon", "evening"]
PlanStatus = Literal["pending", "published", "skipped", "regenerate_requested", "failed"]
CallbackAction = Literal["published", "skipped", "regenerate"]


class CaptionPackage(BaseModel):
    content_type: str = Field(default="story")
    image_brief: str = Field(min_length=20)
    caption: str = Field(min_length=1, max_length=500)
    caption_formula: str = Field(min_length=3)
    hashtags: list[str] = Field(default_factory=list, min_length=3, max_length=5)
    publishing_note: str = Field(min_length=5)
    monthly_checklist_fulfilled: Optional[str] = None
    watch_used: Optional[str] = None
    shoes_used: Optional[str] = None

    @field_validator("caption")
    @classmethod
    def validate_caption(cls, value: str) -> str:
        lines = [line for line in value.splitlines() if line.strip()]
        if len(lines) > 3:
            raise ValueError("Caption must be at most 3 lines.")
        if value.lstrip().startswith("I "):
            raise ValueError("Caption must not start with 'I'.")
        if "!" in value:
            raise ValueError("Caption must not contain exclamation marks.")
        if "#" in value:
            raise ValueError("Caption must not contain hashtags.")
        forbidden = {"obsessed", "insane", "literally", "girlie", "bestie", "slay", "queen"}
        lower = value.lower()
        for word in forbidden:
            if word in lower:
                raise ValueError(f"Caption contains forbidden word: {word}")
        brand_terms = {
            "daniel wellington",
            "tissot",
            "seiko",
            "casio",
            "komono",
            "adidas",
            "celine",
            "bottega",
            "the row",
            "mango",
            "volkswagen",
        }
        for term in brand_terms:
            if term in lower:
                raise ValueError(f"Caption contains visible brand name: {term}")
        return value


class TriggerResult(BaseModel):
    status: str
    reason: Optional[str] = None
    plan_id: Optional[str] = None
    scene_id: Optional[str] = None
    sent_to_telegram: bool = False


class TelegramCallbackResult(BaseModel):
    status: str
    plan_id: str
    action: str
    new_plan_id: Optional[str] = None
