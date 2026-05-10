import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings


@dataclass(frozen=True)
class KnowledgeBundle:
    character_state: dict[str, Any]
    monthly_tracker_text: str
    brand_voice: str


class KnowledgeLoader:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def load(self) -> KnowledgeBundle:
        return KnowledgeBundle(
            character_state=json.loads(self._read_first(self._character_state_candidates())),
            monthly_tracker_text=self._read_first(self._monthly_tracker_candidates()),
            brand_voice=self._read_first(self._brand_voice_candidates()),
        )

    def load_monthly_checklist(self) -> tuple[str, list[dict[str, Any]]]:
        text = self._read_first(self._monthly_tracker_candidates())
        month = self._extract_month(text)
        checklist = self._extract_checklist(text)
        return month, checklist

    def load_scene_records(self) -> list[dict[str, Any]]:
        scenes: dict[str, dict[str, Any]] = {}
        rich_json = self._first_existing(self._scene_json_candidates())
        if rich_json:
            data = json.loads(rich_json.read_text(encoding="utf-8"))
            for item in data.get("scenes", []):
                scene_id = item.get("id") or item.get("scene_id")
                if not scene_id:
                    continue
                scenes[scene_id] = {
                    "scene_id": scene_id,
                    "filename": item.get("filename") or f"{scene_id}.jpg",
                    "group": item.get("group") or "A_closeup",
                    "shot": item.get("shot") or "unknown",
                    "prompt": item.get("prompt") or item.get("image_brief") or item.get("kohya_caption") or "",
                    "kohya_caption": item.get("kohya_caption") or item.get("caption") or "",
                    "source": str(rich_json),
                }

        txt_root = self._first_existing(self._scene_txt_root_candidates())
        if txt_root:
            for path in sorted(txt_root.rglob("*.txt")):
                scene_id = self._scene_id_from_path(path)
                if not scene_id:
                    continue
                caption = path.read_text(encoding="utf-8").strip()
                existing = scenes.get(scene_id)
                if existing:
                    if not existing.get("kohya_caption"):
                        existing["kohya_caption"] = caption
                    continue
                scenes[scene_id] = {
                    "scene_id": scene_id,
                    "filename": path.with_suffix(".jpg").name,
                    "group": self._group_from_category(path.parent.name),
                    "shot": self._shot_from_category(path.parent.name),
                    "prompt": caption,
                    "kohya_caption": caption,
                    "source": str(path),
                }

        return [scenes[key] for key in sorted(scenes.keys(), key=self._scene_sort_key)]

    def _character_state_candidates(self) -> list[Path]:
        return [
            self.settings.app_root / "data" / "seed" / "character_state.json",
            self.settings.workspace_root / "character_state.json",
        ]

    def _monthly_tracker_candidates(self) -> list[Path]:
        return [
            self.settings.app_root / "data" / "seed" / "monthly_tracker.md",
            self.settings.workspace_root / "monthly_tracker.md",
        ]

    def _brand_voice_candidates(self) -> list[Path]:
        return [
            self.settings.app_root / "data" / "seed" / "brand_voice.md",
            self.settings.workspace_root / "knowledge" / "brand_voice.md",
            self.settings.workspace_root / "Agent-dosyaları" / "knowledge" / "BRAND.md",
        ]

    def _scene_json_candidates(self) -> list[Path]:
        return [
            self.settings.app_root / "data" / "seed" / "scene_prompts.json",
            self.settings.workspace_root / "elise_dataset" / "10_EliseVerneV1" / "elise_verne_prompts.json",
        ]

    def _scene_txt_root_candidates(self) -> list[Path]:
        return [
            self.settings.app_root / "data" / "seed" / "dataset",
            self.settings.workspace_root / "EliseVerneV1" / "dataset",
        ]

    def _read_first(self, paths: list[Path]) -> str:
        path = self._first_existing(paths)
        if not path:
            joined = ", ".join(str(p) for p in paths)
            raise FileNotFoundError(f"None of these knowledge paths exist: {joined}")
        return path.read_text(encoding="utf-8")

    def _first_existing(self, paths: list[Path]) -> Path | None:
        for path in paths:
            if path.exists():
                return path
        return None

    def _extract_month(self, text: str) -> str:
        for block in self._json_blocks(text):
            if isinstance(block, dict) and "month" in block:
                return str(block["month"])
        raise ValueError("Could not find month metadata in monthly tracker.")

    def _extract_checklist(self, text: str) -> list[dict[str, Any]]:
        for block in self._json_blocks(text):
            if isinstance(block, dict) and "monthly_checklist" in block:
                return list(block["monthly_checklist"])
        raise ValueError("Could not find monthly_checklist in monthly tracker.")

    def _json_blocks(self, text: str) -> list[Any]:
        blocks: list[Any] = []
        for match in re.finditer(r"```json\s*(.*?)```", text, re.DOTALL | re.IGNORECASE):
            try:
                blocks.append(json.loads(match.group(1)))
            except json.JSONDecodeError:
                continue
        return blocks

    def _scene_id_from_path(self, path: Path) -> str | None:
        match = re.match(r"^(p\d+)", path.stem)
        return match.group(1) if match else None

    def _group_from_category(self, category: str) -> str:
        return {
            "face": "A_closeup",
            "waist": "B_waist_up",
            "fullbody": "C_full_body",
            "legs": "C_full_body",
            "decolletage": "B_waist_up",
            "detail": "D_detail",
        }.get(category.lower(), "B_waist_up")

    def _shot_from_category(self, category: str) -> str:
        return {
            "face": "close-up",
            "waist": "waist-up",
            "fullbody": "full-body",
            "legs": "full-body",
            "decolletage": "waist-up",
            "detail": "detail",
        }.get(category.lower(), "unknown")

    def _scene_sort_key(self, scene_id: str) -> tuple[int, str]:
        match = re.match(r"p(\d+)", scene_id)
        return (int(match.group(1)), scene_id) if match else (9999, scene_id)

