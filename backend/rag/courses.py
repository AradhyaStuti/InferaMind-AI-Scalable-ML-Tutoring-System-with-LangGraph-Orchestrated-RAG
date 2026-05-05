"""Course registry — loads data/courses.json once at import time."""

import json
import os

from backend.config import DATA_DIR

COURSES_PATH = os.path.join(DATA_DIR, "courses.json")

with open(COURSES_PATH, "r", encoding="utf-8") as f:
    _registry = json.load(f)

DEFAULT_COURSE_ID: str = _registry["default_course"]
COURSES: dict[str, dict] = _registry["courses"]


def get_course(course_id: str) -> dict | None:
    return COURSES.get(course_id)
