import pytest

from conftest import FIXED_LOCAL_DATE
from app.models import ContentPlan, DailyCounter, ScenePrompt, utc_now
from app.services.planner import PlannerService, PlannerSkip


def add_scene(session, scene_id: str, group: str = "A_closeup") -> ScenePrompt:
    scene = ScenePrompt(
        scene_id=scene_id,
        filename=f"{scene_id}.jpg",
        group=group,
        shot="close-up",
        prompt=f"{scene_id} coffee window scene",
        kohya_caption=f"{scene_id} caption",
        source="test",
    )
    session.add(scene)
    session.flush()
    return scene


def add_plan(session, scene_id: str, status: str = "pending") -> ContentPlan:
    plan = ContentPlan(
        id=f"plan_{scene_id}_{status}",
        status=status,
        trigger_time="morning",
        content_type="story",
        scene_id=scene_id,
        scene_group="A_closeup",
        excluded_scene_ids=[],
        image_brief="brief",
        caption="quiet light before the day starts.",
        caption_formula="formula_1",
        hashtags=["#quietluxury", "#dubailife", "#visualdiary"],
        publishing_note="note",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(plan)
    session.flush()
    return plan


def test_story_limit_skips_planning(session):
    add_scene(session, "p01")
    session.add(DailyCounter(local_date=FIXED_LOCAL_DATE, timezone="Asia/Dubai", story_count=4))
    session.flush()

    with pytest.raises(PlannerSkip):
        PlannerService(session).create_plan("morning", dry_run=True)


def test_recent_published_scene_is_not_reused(session):
    add_scene(session, "p01")
    add_scene(session, "p02")
    add_plan(session, "p01", status="published")

    plan = PlannerService(session).create_plan("morning", dry_run=True)

    assert plan.scene_id == "p02"


def test_explicit_excluded_scene_is_never_selected(session):
    add_scene(session, "p01")
    add_scene(session, "p02")

    plan = PlannerService(session).create_plan("morning", excluded_scene_ids=["p01"], dry_run=True)

    assert plan.scene_id == "p02"
    assert plan.excluded_scene_ids == ["p01"]
