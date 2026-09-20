"""
Unified scoring engine for RingForge.

Combines signals from all analyzers (heatmap, energy, repetition, beat,
novelty) into a single weighted score per candidate window.

Uses SignalContext to avoid redundant audio loading.

Produces the top-5 best segments with human-readable labels explaining
why each was chosen.
"""

import numpy as np

from analyzer._context import SignalContext
from core.config import get_weights, load as load_config
from core.logging import get_logger

log = get_logger()


def compute_scores(audio_path: str,
                   duration: float | None = None,
                   heatmap_markers: list[dict] | None = None,
                   min_start: float = 0.0,
                   max_end: float | None = None,
                   context: SignalContext | None = None) -> list[dict]:
    """
    Run all analyzers, score all candidate windows, and return the top
    candidates sorted by score.

    Args:
        audio_path: Path to the cached WAV file
        duration: Desired segment duration (uses config default if None)
        heatmap_markers: Heatmap data from analyzer.heatmap.fetch_heatmap()
        min_start: Earliest allowed start time
        max_end: Latest allowed end time
        context: Optional pre-loaded SignalContext. If None, one is created.

    Returns:
        List of candidate dicts sorted by final_score descending, each with:
            - start: float
            - end: float
            - final_score: float (0-100)
            - signals: dict of individual signal scores
            - labels: list of reason labels
    """
    cfg = load_config()

    if duration is None:
        duration = cfg.get("default_duration", 30.0)

    # Create or reuse shared signal context — loads audio exactly once
    if context is None:
        context = SignalContext(audio_path)

    energy, energy_tpf, sr = context.get_energy_profile()
    onset_env, beat_times, beat_tpf, _ = context.get_beat_profile()
    rep_profile, rep_tpf, _ = context.get_repetition_profile()
    total_duration = context.get_duration()

    if max_end is None:
        max_end = total_duration

    # ---- Run all analyzers ----

    # 1. Heatmap scoring (if available)
    heatmap_scores = {}
    if heatmap_markers:
        from analyzer.heatmap import get_peak_segment
        heatmap_available = True
        # Pre-compute heatmap score for every possible 1-second position
        window_candidates = cfg.get("sliding_window", {}).get(
            "candidates", [20, 25, 30, 35, 40]
        )
        for w in window_candidates:
            best = get_peak_segment(heatmap_markers, duration=w,
                                    min_start=min_start, max_end=max_end)
            if best:
                heatmap_scores[w] = {
                    "start": best["start"],
                    "end": best["end"],
                    "score": best["avg_intensity"] * 100.0,
                }
    else:
        heatmap_available = False

    weights = get_weights(heatmap_available)
    window_candidates = cfg.get("sliding_window", {}).get(
        "candidates", [20, 25, 30, 35, 40]
    )

    # Pre-compute signal arrays once for O(1) window scoring
    energy_max = float(energy.max()) if len(energy) > 0 else 0
    onset_max = float(onset_env.max()) if len(onset_env) > 0 else 0
    rep_max = float(rep_profile.max()) if len(rep_profile) > 0 else 0

    # ---- Score all candidate windows ----

    candidates = []
    seen_windows = set()  # avoid near-duplicate windows

    for w in window_candidates:
        w_duration = float(w)
        # If heatmap provided and we have a heatmap peak for this duration,
        # search around it. Otherwise, search the whole audio.
        if heatmap_available and w_duration in heatmap_scores:
            peak_center = (heatmap_scores[w_duration]["start"]
                           + heatmap_scores[w_duration]["end"]) / 2
            start_range = max(min_start, peak_center - search_radius)
            end_range = min(max_end, peak_center + search_radius)
        else:
            start_range = min_start
            end_range = max_end - w_duration

        # Step through candidate start times (1-second steps)
        step = 1.0
        t = start_range
        while t <= end_range:
            seg_start = t
            seg_end = min(t + w_duration, max_end)
            if seg_end - seg_start < 5.0:  # skip too-short segments
                t += step
                continue

            # Deduplicate by rounding to nearest 0.5 sec
            window_key = (round(seg_start * 2) / 2, round(seg_end * 2) / 2)
            if window_key in seen_windows:
                t += step
                continue
            seen_windows.add(window_key)

            # Compute individual scores using pre-computed arrays
            sig = _compute_segment_scores(
                seg_start, seg_end,
                energy, energy_tpf, len(energy),
                rep_profile, rep_tpf,
                onset_env, beat_times, beat_tpf,
                heatmap_markers,
                total_duration,
            )

            # Weighted final score
            final_score = (
                weights.get("replay", 0) * sig.get("replay", 0)
                + weights.get("repetition", 0) * sig.get("repetition", 0)
                + weights.get("energy", 0) * sig.get("energy", 0)
                + weights.get("beat", 0) * sig.get("beat", 0)
                + weights.get("novelty", 0) * sig.get("novelty", 0)
            )

            # Build labels explaining why this segment scored well
            labels = _generate_labels(sig, weights, heatmap_available)

            candidates.append({
                "start": seg_start,
                "end": seg_end,
                "final_score": round(final_score, 1),
                "signals": sig,
                "labels": labels,
            })

            t += step

    if not candidates:
        return []

    # Sort by final_score descending and take top 10-ish
    candidates.sort(key=lambda c: c["final_score"], reverse=True)

    # Pick top 5 unique-ish segments (ensure minimum separation)
    top5 = []
    for c in candidates:
        if len(top5) >= 5:
            break
        # Check this candidate is at least 5s away from already selected ones
        too_close = False
        for selected in top5:
            if abs(c["start"] - selected["start"]) < 5.0:
                too_close = True
                break
        if not too_close:
            top5.append(c)

    # Assign human-friendly rank names
    rank_names = [
        "Most Replayed",
        "Best Chorus",
        "Highest Energy",
        "Best Ringtone Flow",
        "Wildcard",
    ]
    for i, c in enumerate(top5):
        c["rank"] = i + 1
        c["rank_name"] = rank_names[i] if i < len(rank_names) else f"Pick #{i + 1}"

    return top5


def _compute_segment_scores(start, end,
                            energy, energy_tpf, energy_total_frames,
                            rep_profile, rep_tpf,
                            onset_env, beat_times, beat_tpf,
                            heatmap_markers, total_duration) -> dict:
    """
    Compute individual analyzer scores (0-100) for a single segment.
    All arrays come from SignalContext — no redundant loads.
    """
    sig = {"replay": 0.0, "repetition": 0.0, "energy": 0.0,
           "beat": 0.0, "novelty": 0.0}

    # ---- Heatmap score ----
    if heatmap_markers:
        markers_in_seg = [m for m in heatmap_markers if start <= m["time"] <= end]
        if markers_in_seg:
            avg_intensity = np.mean([m["intensity"] for m in markers_in_seg])
            sig["replay"] = avg_intensity * 100.0

    # ---- Energy score ----
    s_frame = int(start / energy_tpf)
    e_frame = int(end / energy_tpf)
    s_frame = max(0, min(s_frame, energy_total_frames - 1))
    e_frame = max(s_frame + 1, min(e_frame, energy_total_frames))
    if e_frame > s_frame:
        seg_energy = float(np.mean(energy[s_frame:e_frame]))
        if energy_total_frames > 0:
            global_max = float(energy.max()) if energy.max() > 0 else 1.0
            sig["energy"] = min(seg_energy / global_max * 100.0, 100.0)
        else:
            sig["energy"] = 50.0

    # ---- Repetition score ----
    s_frame_r = int(start / rep_tpf)
    e_frame_r = int(end / rep_tpf)
    s_frame_r = max(0, min(s_frame_r, len(rep_profile) - 1))
    e_frame_r = max(s_frame_r + 1, min(e_frame_r, len(rep_profile)))
    if e_frame_r > s_frame_r:
        seg_rep = float(np.mean(rep_profile[s_frame_r:e_frame_r]))
        sig["repetition"] = min(seg_rep * 100.0, 100.0)

    # ---- Beat score ----
    s_frame_b = int(start / beat_tpf)
    e_frame_b = int(end / beat_tpf)
    s_frame_b = max(0, min(s_frame_b, len(onset_env) - 1))
    e_frame_b = max(s_frame_b + 1, min(e_frame_b, len(onset_env)))
    if e_frame_b > s_frame_b:
        seg_beat = float(np.mean(onset_env[s_frame_b:e_frame_b])) * 100.0
        # Beat density bonus
        beat_count = sum(1 for bt in beat_times if start <= bt <= end)
        density = beat_count / (end - start)
        density_score = min(density * 20, 30.0)
        sig["beat"] = min(seg_beat * 0.3 + density_score, 100.0)

    # ---- Novelty score (std of onset envelope) ----
    s_frame_n = int(start / beat_tpf)
    e_frame_n = int(end / beat_tpf)
    s_frame_n = max(0, min(s_frame_n, len(onset_env) - 1))
    e_frame_n = max(s_frame_n + 1, min(e_frame_n, len(onset_env)))
    if e_frame_n > s_frame_n:
        seg_novelty = float(np.std(onset_env[s_frame_n:e_frame_n])) * 200.0
        sig["novelty"] = min(seg_novelty, 100.0)

    return sig


def _generate_labels(signals: dict, weights: dict, heatmap_available: bool) -> list[str]:
    """Generate human-readable labels explaining why a segment scored well."""
    labels = []
    sorted_sigs = sorted(signals.items(), key=lambda x: x[1], reverse=True)

    for name, score in sorted_sigs[:3]:
        if score >= 70:
            if name == "replay":
                labels.append("Most Replayed")
            elif name == "repetition":
                labels.append("Best Chorus")
            elif name == "energy":
                labels.append("High Energy")
            elif name == "beat":
                labels.append("Strong Beat")
            elif name == "novelty":
                labels.append("Dynamic")

    if not labels:
        labels.append("Balanced")

    return labels


def find_nearest_beat(beat_times: list[float], target: float, max_drift: float = 1.0) -> float:
    """Snap a time to the nearest beat onset (for smart start)."""
    if not beat_times:
        return target
    nearest = min(beat_times, key=lambda b: abs(b - target))
    if abs(nearest - target) <= max_drift:
        return nearest
    return target


def find_phrase_end(beat_times: list[float], target: float,
                     phrase_length: int = 8, max_drift: float = 3.0) -> float:
    """Snap an end time to the nearest phrase boundary."""
    if not beat_times or len(beat_times) < phrase_length:
        return target

    boundaries = [beat_times[i] for i in range(phrase_length - 1, len(beat_times), phrase_length)]
    if not boundaries:
        return target

    nearest = min(boundaries, key=lambda b: abs(b - target))
    if abs(nearest - target) <= max_drift:
        return nearest
    return target
