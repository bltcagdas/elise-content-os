import pytest

from app.models import ContentPlan, ScenePrompt
from app.schemas import CaptionPackage
from app.services.caption import CaptionService
from app.services.telegram import TelegramService


def test_caption_guardrails_reject_bad_caption():
    with pytest.raises(ValueError):
        CaptionPackage(
            content_type="story",
            image_brief="valid image brief long enough",
            caption="I love this vibe!",
            caption_formula="formula_1",
            hashtags=["#a", "#b", "#c"],
            publishing_note="valid note",
        )
    with pytest.raises(ValueError):
        CaptionPackage(
            content_type="story",
            image_brief="valid image brief long enough",
            caption="Daniel Wellington on the desk",
            caption_formula="formula_1",
            hashtags=["#a", "#b", "#c"],
            publishing_note="valid note",
        )
    with pytest.raises(ValueError):
        CaptionPackage(
            content_type="story",
            image_brief="valid image brief long enough",
            caption="quiet light #dubai",
            caption_formula="formula_1",
            hashtags=["#a", "#b", "#c"],
            publishing_note="valid note",
        )


def test_dry_run_image_brief_injects_required_elise_dna():
    scene = ScenePrompt(
        scene_id="p01",
        filename="p01.jpg",
        group="A_closeup",
        shot="close-up",
        prompt="Dubai apartment window light.",
        kohya_caption="EliseVerneV1 close-up",
        source="test",
    )
    package = CaptionService()._dry_run_package(scene, "morning", None, "danielwellington_classic_cornwall", "Adidas Samba OG")

    assert "Elise DNA" in package.image_brief
    assert "Freckle rule" in package.image_brief
    assert "right-corner micro-smirk" in package.image_brief
    assert "dark chestnut straight hair" in package.image_brief
    assert "Watch:" in package.image_brief
    assert "Shoes:" in package.image_brief
    assert "hyperrealistic natural light" in package.image_brief


def test_telegram_message_contains_visual_qc_checklist():
    plan = ContentPlan(
        id="plan_test",
        status="pending",
        trigger_time="morning",
        content_type="story",
        scene_id="p01",
        scene_group="A_closeup",
        excluded_scene_ids=[],
        image_brief="brief",
        caption="quiet light before the day starts.",
        caption_formula="formula_1",
        hashtags=["#quietluxury", "#dubailife", "#visualdiary"],
        publishing_note="note",
    )
    text = TelegramService()._message_text(plan)

    assert "VISUAL QC CHECKLIST" in text
    assert "face consistency" in text
    assert "correct watch/shoes" in text
    assert "correct scene distance freckle rule" in text
