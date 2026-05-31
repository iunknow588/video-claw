from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any

from app.core.config import settings


@dataclass(slots=True)
class MaterialReferenceCandidate:
    candidate_id: str
    search_term: str
    title: str
    provider: str
    fit_score: float
    duration_hint: int
    aspect_ratio: str
    cache_key: str
    cache_path: str
    source_url: str
    preview_url: str | None = None
    license_hint: str = "external-source-pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "search_term": self.search_term,
            "title": self.title,
            "provider": self.provider,
            "fit_score": self.fit_score,
            "duration_hint": self.duration_hint,
            "aspect_ratio": self.aspect_ratio,
            "cache_key": self.cache_key,
            "cache_path": self.cache_path,
            "source_url": self.source_url,
            "preview_url": self.preview_url,
            "license_hint": self.license_hint,
        }


class MaterialReferenceService:
    """Lightweight material-planning service inspired by stock-video search workflows."""

    def __init__(self) -> None:
        self.cache_root = Path(settings.MEDIA_ROOT) / "material_cache"

    def plan(
        self,
        *,
        search_terms: list[str] | None = None,
        scenes: list[dict[str, Any]] | None = None,
        platform: str | None = None,
        target_duration: int | None = None,
        aspect_ratio: str = "9:16",
        limit_per_term: int = 2,
        material_pool: list[dict[str, Any]] | None = None,
        provider: str = "reference_stub",
    ) -> dict[str, Any]:
        normalized_terms = self._normalize_terms(search_terms=search_terms, scenes=scenes)
        candidates = self._build_candidates(
            normalized_terms=normalized_terms,
            target_duration=target_duration or 15,
            aspect_ratio=aspect_ratio,
            limit_per_term=max(1, limit_per_term),
            material_pool=material_pool or [],
            provider=provider,
        )
        scene_material_map = self._map_scenes_to_candidates(scenes or [], candidates)
        return {
            "platform": platform,
            "search_terms": normalized_terms,
            "material_candidates": [item.to_dict() for item in candidates],
            "scene_material_map": scene_material_map,
            "cache_root": str(self.cache_root),
        }

    def _normalize_terms(
        self,
        *,
        search_terms: list[str] | None,
        scenes: list[dict[str, Any]] | None,
    ) -> list[str]:
        terms: list[str] = []
        for raw in search_terms or []:
            value = str(raw).strip()
            if value:
                terms.append(value)

        for scene in scenes or []:
            visuals = str(scene.get("visuals") or "").strip()
            text = str(scene.get("text") or "").strip()
            for field in (visuals, text):
                if field:
                    for part in field.replace("，", ",").split(","):
                        value = part.strip()
                        if value:
                            terms.append(value)

        deduped: list[str] = []
        seen: set[str] = set()
        for term in terms:
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(term)
        return deduped[:12]

    def _build_candidates(
        self,
        *,
        normalized_terms: list[str],
        target_duration: int,
        aspect_ratio: str,
        limit_per_term: int,
        material_pool: list[dict[str, Any]],
        provider: str,
    ) -> list[MaterialReferenceCandidate]:
        if material_pool:
            return self._rank_pool_candidates(
                normalized_terms=normalized_terms,
                target_duration=target_duration,
                aspect_ratio=aspect_ratio,
                material_pool=material_pool,
                provider=provider,
            )

        candidates: list[MaterialReferenceCandidate] = []
        for term in normalized_terms:
            for index in range(limit_per_term):
                cache_key = sha1(f"{term}:{index}:{aspect_ratio}".encode("utf-8")).hexdigest()[:16]
                cache_path = self.cache_root / provider / f"{cache_key}.mp4"
                candidates.append(
                    MaterialReferenceCandidate(
                        candidate_id=f"{provider}-{cache_key}",
                        search_term=term,
                        title=f"{term} reference shot {index + 1}",
                        provider=provider,
                        fit_score=round(max(0.35, 0.88 - index * 0.08), 4),
                        duration_hint=target_duration,
                        aspect_ratio=aspect_ratio,
                        cache_key=cache_key,
                        cache_path=str(cache_path),
                        source_url=f"material://{provider}/{cache_key}",
                    )
                )
        return candidates

    def _rank_pool_candidates(
        self,
        *,
        normalized_terms: list[str],
        target_duration: int,
        aspect_ratio: str,
        material_pool: list[dict[str, Any]],
        provider: str,
    ) -> list[MaterialReferenceCandidate]:
        ranked: list[MaterialReferenceCandidate] = []
        for index, item in enumerate(material_pool):
            keywords = [str(value).strip().lower() for value in item.get("keywords", []) if str(value).strip()]
            overlap = sum(1 for term in normalized_terms if term.lower() in keywords)
            duration_hint = int(item.get("duration_hint") or target_duration)
            duration_penalty = abs(duration_hint - target_duration) / max(target_duration, 1)
            fit_score = max(0.2, min(0.98, 0.45 + overlap * 0.18 - duration_penalty * 0.1))
            source_url = str(item.get("source_url") or item.get("url") or f"material://{provider}/{index}")
            cache_key = sha1(source_url.encode("utf-8")).hexdigest()[:16]
            cache_path = self.cache_root / provider / f"{cache_key}.mp4"
            ranked.append(
                MaterialReferenceCandidate(
                    candidate_id=str(item.get("candidate_id") or f"{provider}-{cache_key}"),
                    search_term=str(item.get("search_term") or (normalized_terms[0] if normalized_terms else "reference")),
                    title=str(item.get("title") or f"Reference material {index + 1}"),
                    provider=str(item.get("provider") or provider),
                    fit_score=round(fit_score, 4),
                    duration_hint=duration_hint,
                    aspect_ratio=str(item.get("aspect_ratio") or aspect_ratio),
                    cache_key=cache_key,
                    cache_path=str(cache_path),
                    source_url=source_url,
                    preview_url=item.get("preview_url"),
                    license_hint=str(item.get("license_hint") or "external-source-pending"),
                )
            )
        ranked.sort(key=lambda item: item.fit_score, reverse=True)
        return ranked[: max(1, len(normalized_terms) * 2)]

    def _map_scenes_to_candidates(
        self,
        scenes: list[dict[str, Any]],
        candidates: list[MaterialReferenceCandidate],
    ) -> list[dict[str, Any]]:
        scene_map: list[dict[str, Any]] = []
        for index, scene in enumerate(scenes):
            visuals = str(scene.get("visuals") or "").lower()
            text = str(scene.get("text") or "").lower()
            best = None
            for candidate in candidates:
                term = candidate.search_term.lower()
                if term and (term in visuals or term in text):
                    best = candidate
                    break
            if best is None and index < len(candidates):
                best = candidates[index]
            scene_map.append(
                {
                    "scene_index": index,
                    "timing": scene.get("timing"),
                    "search_hint": scene.get("visuals") or scene.get("text") or "",
                    "candidate_id": best.candidate_id if best else None,
                    "cache_path": best.cache_path if best else None,
                }
            )
        return scene_map
