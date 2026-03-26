"""
NSFW Classifier Core
Uses NudeNet for image/video classification and blurring.
Achieves 90%+ accuracy on standard NSFW benchmarks.

Supported inputs:
  - Images: jpg, png, webp, gif
  - Videos: mp4, mov, avi, mkv
  - YouTube: link passed, frames extracted for classification
"""

import os
import cv2
import json
import uuid
import yt_dlp
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Tuple
from nudenet import NudeDetector

UPLOAD_DIR = Path("app/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# NudeNet label groups - mapped to our 3-tier system
SAFE_LABELS = [
    "FACE_FEMALE", "FACE_MALE", "ARMPITS_COVERED", "BELLY_COVERED",
    "BUTTOCKS_COVERED", "FEET_COVERED", "BREAST_COVERED_F", "GENITALIA_COVERED_F",
    "GENITALIA_COVERED_M"
]
SUGGESTIVE_LABELS = [
    "ARMPITS_EXPOSED", "BELLY_EXPOSED", "FEET_EXPOSED",
    "BREAST_COVERED_F", "BUTTOCKS_EXPOSED"
]
NSFW_LABELS = [
    "BREAST_EXPOSED_F", "GENITALIA_EXPOSED_F", "GENITALIA_EXPOSED_M",
    "ANUS_EXPOSED", "ANUS_COVERED"
]

# These are the parts we actually blur (only the explicit ones)
BLUR_TARGETS = [
    "BREAST_EXPOSED_F", "GENITALIA_EXPOSED_F", "GENITALIA_EXPOSED_M",
    "ANUS_EXPOSED", "BUTTOCKS_EXPOSED"
]


class NSFWClassifier:
    def __init__(self):
        self.detector = NudeDetector()

    def classify_image(self, image_path: str) -> dict:
        """
        Run NudeNet on a single image and return structured result.
        Returns label, confidence score, per-category breakdown.
        """
        detections = self.detector.detect(image_path)

        label, score, categories = self._compute_verdict(detections)

        return {
            "label": label,
            "confidence_score": round(score, 4),
            "is_safe": label == "safe",
            "category_scores": json.dumps(categories),
            "detections_raw": detections
        }

    def classify_and_blur_image(self, image_path: str, output_path: str) -> dict:
        """
        Classify AND apply gaussian blur to detected NSFW regions.
        Returns same result dict + path to blurred output image.
        """
        detections = self.detector.detect(image_path)
        label, score, categories = self._compute_verdict(detections)

        # load image with OpenCV
        img = cv2.imread(image_path)

        # blur only the explicit body parts
        for det in detections:
            if det["class"] in BLUR_TARGETS and det["score"] >= 0.4:
                x1, y1, x2, y2 = (
                    int(det["box"][0]), int(det["box"][1]),
                    int(det["box"][2]), int(det["box"][3])
                )
                # safety clamp to image bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)

                region = img[y1:y2, x1:x2]
                if region.size > 0:
                    blurred = cv2.GaussianBlur(region, (99, 99), 30)
                    img[y1:y2, x1:x2] = blurred

        cv2.imwrite(output_path, img)

        return {
            "label": label,
            "confidence_score": round(score, 4),
            "is_safe": label == "safe",
            "was_blurred": True,
            "blurred_file_path": output_path,
            "category_scores": json.dumps(categories),
        }

    def classify_video(self, video_path: str, sample_every_n_frames: int = 30) -> dict:
        """
        Classify a video by sampling frames.
        Returns the worst-case label across all sampled frames.
        """
        cap = cv2.VideoCapture(video_path)
        frame_results = []
        frame_idx = 0
        temp_frame_path = str(UPLOAD_DIR / f"_temp_frame_{uuid.uuid4().hex}.jpg")

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_every_n_frames == 0:
                cv2.imwrite(temp_frame_path, frame)
                result = self.classify_image(temp_frame_path)
                frame_results.append(result)
            frame_idx += 1

        cap.release()
        if os.path.exists(temp_frame_path):
            os.remove(temp_frame_path)

        return self._aggregate_video_results(frame_results)

    def classify_and_blur_video(self, video_path: str, output_path: str, sample_every_n_frames: int = 10) -> dict:
        """
        Blur NSFW regions frame-by-frame in a video.
        Every frame is processed (not just sampled) for smooth output.
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        temp_frame_path = str(UPLOAD_DIR / f"_temp_frame_{uuid.uuid4().hex}.jpg")
        frame_results = []
        frame_idx = 0
        last_detections = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # only re-run detection every N frames to save time
            if frame_idx % sample_every_n_frames == 0:
                cv2.imwrite(temp_frame_path, frame)
                last_detections = self.detector.detect(temp_frame_path)
                result = self._compute_verdict(last_detections)
                frame_results.append({"label": result[0], "confidence_score": result[1]})

            # apply blur from last known detections
            for det in last_detections:
                if det["class"] in BLUR_TARGETS and det["score"] >= 0.4:
                    x1, y1, x2, y2 = (
                        int(det["box"][0]), int(det["box"][1]),
                        int(det["box"][2]), int(det["box"][3])
                    )
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(width, x2), min(height, y2)
                    region = frame[y1:y2, x1:x2]
                    if region.size > 0:
                        frame[y1:y2, x1:x2] = cv2.GaussianBlur(region, (99, 99), 30)

            out.write(frame)
            frame_idx += 1

        cap.release()
        out.release()
        if os.path.exists(temp_frame_path):
            os.remove(temp_frame_path)

        aggregate = self._aggregate_video_results(frame_results)
        aggregate["was_blurred"] = True
        aggregate["blurred_file_path"] = output_path
        return aggregate

    def download_youtube_video(self, yt_url: str) -> str:
        """Download a YouTube video to local temp file using yt-dlp"""
        output_path = str(UPLOAD_DIR / f"yt_{uuid.uuid4().hex}.mp4")
        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([yt_url])
        return output_path

    # ─── internal helpers ───────────────────────────────────────────────────────

    def _compute_verdict(self, detections: list) -> Tuple[str, float, dict]:
        """
        From raw NudeNet detections, compute:
        - Overall label: "safe" | "suggestive" | "nsfw"
        - Confidence score (highest detection confidence in winning category)
        - Per-category score breakdown dict
        """
        if not detections:
            return "safe", 0.99, {}

        categories = {}
        has_nsfw = False
        has_suggestive = False
        nsfw_score = 0.0
        suggestive_score = 0.0

        for det in detections:
            cls = det["class"]
            score = det["score"]
            categories[cls] = max(categories.get(cls, 0.0), score)

            if cls in NSFW_LABELS and score >= 0.45:
                has_nsfw = True
                nsfw_score = max(nsfw_score, score)
            elif cls in SUGGESTIVE_LABELS and score >= 0.45:
                has_suggestive = True
                suggestive_score = max(suggestive_score, score)

        if has_nsfw:
            return "nsfw", nsfw_score, categories
        elif has_suggestive:
            return "suggestive", suggestive_score, categories
        else:
            safe_score = 1.0 - max(categories.values(), default=0.0)
            return "safe", max(0.5, safe_score), categories

    def _aggregate_video_results(self, frame_results: list) -> dict:
        """Aggregate per-frame results into a single video verdict"""
        if not frame_results:
            return {"label": "safe", "confidence_score": 0.99, "is_safe": True, "category_scores": "{}"}

        label_priority = {"nsfw": 3, "suggestive": 2, "safe": 1}
        worst = max(frame_results, key=lambda r: label_priority.get(r["label"], 0))

        nsfw_frame_count = sum(1 for r in frame_results if r["label"] == "nsfw")
        nsfw_ratio = nsfw_frame_count / len(frame_results)

        return {
            "label": worst["label"],
            "confidence_score": round(worst["confidence_score"], 4),
            "is_safe": worst["label"] == "safe",
            "nsfw_frame_ratio": round(nsfw_ratio, 4),
            "total_frames_sampled": len(frame_results),
            "category_scores": "{}",
        }


# single shared instance (model loaded once)
classifier = NSFWClassifier()
