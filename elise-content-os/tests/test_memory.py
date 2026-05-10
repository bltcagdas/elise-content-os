from conftest import FIXED_LOCAL_DATE
from app.models import ContentPlan, DailyCounter, ScenePrompt, utc_now
from app.services.memory import MemoryService


def add_scene(session, scene_id: str) -> None:
    session.add(
        ScenePrompt(
            scene_id=scene_id,
            filename=f"{scene_id}.jpg",
            group="A_closeup",
            shot="close-up",
            prompt=f"{scene_id} coffee scene",
            kohya_caption=f"{scene_id} caption",
            source="test",
        )
    )


def add_pending_plan(session, scene_id: str = "p01") -> ContentPlan:
    plan = ContentPlan(
        id="plan_test",
        status="pending",
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
        monthly_checklist_fulfilled=None,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(plan)
    session.flush()
    return plan


def test_published_callback_is_idempotent(session):
    add_scene(session, "p01")
    plan = add_pending_plan(session)

    service = MemoryService(session)
    first = service.handle_callback(
        action="published",
        plan_id=plan.id,
        callback_event_id="callback-1",
        payload={"source": "test"},
        dry_run=True,
        send_telegram=False,
    )
    second = service.handle_callback(
        action="published",
        plan_id=plan.id,
        callback_event_id="callback-1",
        payload={"source": "test"},
        dry_run=True,
        send_telegram=False,
    )

    counter = session.get(DailyCounter, FIXED_LOCAL_DATE)
    assert first.status == "published"
    assert second.status == "duplicate"
    assert counter is not None
    assert counter.story_count == 1


def test_regenerate_persists_excluded_scene_and_creates_child_plan(session):
    add_scene(session, "p01")
    add_scene(session, "p02")
    add_scene(session, "p03")
    plan = add_pending_plan(session, "p01")

    result = MemoryService(session).handle_callback(
        action="regenerate",
        plan_id=plan.id,
        callback_event_id="callback-2",
        payload={"source": "test"},
        dry_run=True,
        send_telegram=False,
    )

    session.refresh(plan)
    child = session.get(ContentPlan, result.new_plan_id)
    assert plan.status == "regenerate_requested"
    assert plan.excluded_scene_ids == ["p01"]
    assert child is not None
    assert child.parent_plan_id == plan.id
    assert child.scene_id == "p02"
    assert child.excluded_scene_ids == ["p01"]

    second = MemoryService(session).handle_callback(
        action="regenerate",
        plan_id=child.id,
        callback_event_id="callback-3",
        payload={"source": "test"},
        dry_run=True,
        send_telegram=False,
    )
    grandchild = session.get(ContentPlan, second.new_plan_id)
    assert grandchild is not None
    assert grandchild.parent_plan_id == child.id
    assert grandchild.scene_id == "p03"
    assert grandchild.excluded_scene_ids == ["p01", "p02"]
