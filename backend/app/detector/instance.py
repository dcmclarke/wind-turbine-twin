"""
Singleton detector instance shared across all routes.

A single IcingDetector instance holds the rolling window state
across requests. If FastAPI restarts, the window resets to empty.
For production, persist window state to Redis or database.
Documented trade-off in decisions.md.
"""
from app.detector.icing_detector import IcingDetector

detector = IcingDetector()
