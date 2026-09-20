# RingForge — UI/UX Improvement Plan (Company Audit)

**Date**: 2026-09-20
**Auditor**: Design/UX Engineering Agent
**Skills Applied**: `frontend-ui-engineering`, `design-review`, `a11y-audit`, `redesign`, `design-code`, `ux-writing`, `emil-design-eng`, `performance`

---

## Executive Summary

RingForge's GUI is a functional PySide6 application with a working waveform, candidate selection, and export pipeline. However, it fails on **every design engineering principle**:

- ❌ Zero animations/transitions (no feedback, no delight)
- ❌ All colors hardcoded as raw hex values (no design tokens)
- ❌ No accessible focus indicators, screen reader labels, or ARIA equivalents
- ❌ No loading/empty/error states
- ❌ `main_window.py` is 1005 lines (violates component composition)
- ❌ No typography or spacing scale
- ❌ No hover/focus/active/pressed states on any widget
- ❌ No reduced-motion support
- ❌ No keyboard accessibility beyond shortcuts
- ❌ No error handling UX
- ❌ No skeleton screens for async operations
- ❌ All UI rendered synchronously (no lazy loading)
- ❌ Hardcoded dark palette with no theme system

**Score**: 3/10 across all dimensions

---

## 1. DESIGN REVIEW — 6-Dimension Scored Table

| Dimension | Weight | Score | Notes |
|-----------|--------|-------|-------|
| Visual Hierarchy | 20% | **2/10** | All labels use `QFont("sans-serif", 12)`. No heading levels. No spacing scale. No weight differentiation. |
| Consistency | 20% | **2/10** | Every button has different padding/color. Colors are raw hex everywhere. No token system. |
| Accessibility | 20% | **1/10** | No focus indicators, no screen reader labels, no ARIA equivalents, no reduced-motion. |
| Usability | 20% | **4/10** | Keyboard shortcuts work but no visual feedback. No loading states. No empty states. |
| Responsiveness | 10% | **3/10** | No responsive breakpoints. Fixed 900x600 minimum. No adaptive layout. |
| Performance | 10% | **4/10** | Waveform re-renders entire pixmap on every paint. No lazy loading. |

**Overall**: 2.6/10 ❌

---

## 2. PRIORITIZED FINDINGS TABLE

### 🔴 Critical (Must Fix)

| # | Severity | Finding | Recommendation | Skill Source |
|---|----------|---------|----------------|--------------|
| C-1 | Critical | `main_window.py` is 1005 lines | Split into `MainWindow`, `WaveformSection`, `CandidatePanel`, `ExportPanel`, `ControlsBar`, `StatusBar` | frontend-ui-engineering |
| C-2 | Critical | All colors hardcoded as raw hex (`#1e1e2e`, `#89b4fa`, etc.) | Create a design token system (`core/tokens.py`) with semantic tokens, apply via CSS/QPalette | design-code, emil-design-eng |
| C-3 | Critical | No focus indicators on any widget | Add `QFocusFrame` or CSS `QPushButton { border: 2px solid #89b4fa; }` on focus | a11y-audit |
| C-4 | Critical | No screen reader labels / accessible names | Set `setAccessibleName()` and `setAccessibleDescription()` on all interactive widgets | a11y-audit |
| C-5 | Critical | No loading/empty/error states | Add skeleton screen during analysis, empty state illustration when no candidates, error dialogs with actionable messages | frontend-ui-engineering |
| C-6 | Critical | No animations on any UI element | Add transitions for all state changes (160-250ms, ease-out) | emil-design-eng |

### 🟠 Major (This Sprint)

| # | Severity | Finding | Recommendation | Skill Source |
|---|----------|---------|----------------|--------------|
| M-1 | Major | No hover/focus/active/pressed states on buttons | Add `QPushButton::hover`, `QPushButton::pressed`, `QPushButton:focus` CSS selectors with scale feedback | emil-design-eng |
| M-2 | Major | No press feedback on buttons (`scale(0.97)`) | Add `transform: scale(0.97)` equivalent via QPropertyAnimation on button press | emil-design-eng |
| M-3 | Major | Dark palette hardcoded in `launch()` with no theming | Create `ThemeManager` with light/dark modes, CSS stylesheets, token-driven palette | redesign |
| M-4 | Major | No typography hierarchy (all 12pt sans-serif) | Create `Typography` system: h1, h2, h3, body, small, caption with proper sizes/weights | frontend-ui-engineering |
| M-5 | Major | No spacing scale (all hardcoded 10, 8, etc.) | Create spacing scale: 4, 8, 12, 16, 20, 24, 32, 48 using a consistent 4px grid | design-code |
| M-6 | Major | No skeleton/loading screen during analysis | Add `QProgressBar` with animated pulse, skeleton waveform placeholder | frontend-ui-engineering |
| M-7 | Major | `_render_cache()` rebuilds entire pixmap every paint | Use GPU-accelerated rendering, only re-render dirty regions | performance |
| M-8 | Major | No icon system (all text-only buttons) | Add lucide/icon-based SVG icons for all buttons | design-code |
| M-9 | Major | `BatchDialog` no transition/animation on show/hide | Add slide-in/fade-in animation (200ms ease-out) | emil-design-eng |
| M-10 | Major | `PreferencesDialog` has no animation or visual polish | Add modal overlay with fade + scale, dialog appears with spring animation | emil-design-eng |

### 🟡 Minor (Next Sprint)

| # | Severity | Finding | Recommendation | Skill Source |
|---|----------|---------|----------------|--------------|
| N-1 | Minor | "Analyze" button should say "Find Best Moment" | UX writing: frontload the verb, name the outcome | ux-writing |
| N-2 | Minor | "Prefs" should say "Preferences" | UX writing: use full words, not abbreviations | ux-writing |
| N-3 | Minor | No empty state when no audio loaded | Add illustration + "Drag & drop or Open File" CTA | frontend-ui-engineering |
| N-4 | Minor | No confirmation dialog for batch processing | Add confirmation with action restated: "Process 5 audio files?" | ux-writing |
| N-5 | Minor | No error recovery for failed downloads | Add retry button, partial results display | frontend-ui-engineering |
| N-6 | Minor | No `prefers-reduced-motion` equivalent | Add `QSettings` flag to disable all animations | a11y-audit |
| N-7 | Minor | Waveform hover tooltip uses raw pixel coordinates | Convert to time-based labels with proper formatting | design-code |
| N-8 | Minor | `main_window.py` `_connect_signals` is unused | Remove dead code | code-simplification |

### 🔵 Enhancement (Future)

| # | Severity | Finding | Recommendation | Skill Source |
|---|----------|---------|----------------|--------------|
| E-1 | Enhancement | No waveform animation when playing | Add animated cursor with smooth interpolation | emil-design-eng |
| E-2 | Enhancement | No stagger animation on candidate list | Add 30-80ms stagger delay when candidates appear | emil-design-eng |
| E-3 | Enhancement | No dark mode toggle | Add theme switcher in Preferences | redesign |
| E-4 | Enhancement | No responsive breakpoint support | Add adaptive layout for smaller screens | frontend-ui-engineering |
| E-5 | Enhancement | No waveform zoom animation | Add animated zoom transition | emil-design-eng |
| E-6 | Enhancement | No sound design for UI events | Add subtle sound feedback for analyze/export/select | emil-design-eng |

---

## 3. DESIGN TOKENS (Implementation Plan)

### Token System Structure

```python
# core/tokens.py — design tokens for the GUI

COLORS = {
    # Background
    "bg-primary": "#1e1e2e",
    "bg-secondary": "#181825",
    "bg-surface": "#313244",
    "bg-surface-hover": "#45475a",
    
    # Text
    "text-primary": "#cdd6f4",
    "text-secondary": "#a6adc8",
    "text-muted": "#6c7086",
    
    # Brand (Catppuccin Mocha palette)
    "brand-primary": "#89b4fa",   # blue
    "brand-success": "#a6e3a1",   # green
    "brand-warning": "#f9e2af",   # yellow
    "brand-danger": "#f38ba8",    # red
    "brand-accent": "#cba6f7",    # purple
    
    # Waveform
    "waveform": "#89b4fa",
    "candidate": "#a6e3a1",
    "candidate-selected": "#f9e2af",
    "cursor": "#f38ba8",
    "handle": "#f9e2af",
    
    # Interactive
    "focus-ring": "#89b4fa",
    "hover-overlay": "rgba(137, 180, 250, 0.1)",
}

SPACING = {
    "xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 20, "xxl": 24,
    "page": 32, "section": 48,
}

TYPOGRAPHY = {
    "h1":  ("sans-serif", 18, QFont.Weight.Bold),
    "h2":  ("sans-serif", 14, QFont.Weight.Bold),
    "h3":  ("sans-serif", 12, QFont.Weight.DemiBold),
    "body":("sans-serif", 11, QFont.Weight.Normal),
    "small":("sans-serif", 9, QFont.Weight.Normal),
    "mono":("monospace", 10, QFont.Weight.Normal),
}

ANIMATION = {
    "instant":  "100ms",
    "fast":     "150ms",
    "normal":   "200ms",
    "slow":     "300ms",
    "ease-out": "cubic-bezier(0.23, 1, 0.32, 1)",
    "ease-in-out": "cubic-bezier(0.77, 0, 0.175, 1)",
    "spring":   "500ms",
}
```

---

## 4. REFACTORING PLAN — Component Split

### Current Structure (monolith)
```
ui/
  main_window.py          ← 1005 lines, everything in one file
  waveform_widget.py      ← 344 lines (decent)
  player.py              ← 66 lines (decent)
  worker.py              ← 68 lines (decent)
  __init__.py            ← empty
```

### Target Structure (composable)
```
ui/
  __init__.py
  main.py                ← Thin entry point (launch function only)
  theme/
    __init__.py
    tokens.py            ← Design tokens (COLORS, SPACING, TYPOGRAPHY, ANIMATION)
    theme_manager.py     ← Light/dark mode switching, QPalette management
    stylesheet.py        ← CSS stylesheets for all widgets
  components/
    __init__.py
    button.py            ← StyledQPushButton with states (hover/focus/active/pressed)
    label.py             ← StyledQLabel with typography scale
    spinner.py           ← Loading animation widget
    divider.py           ← QFrame with spacing token
    tab_bar.py           ← QTabWidget with animations
  layout/
    __init__.py
    header.py            ← Top bar: Open File, URL input, Analyze, Batch, Preferences
    waveform_section.py  ← WaveformWidget + playback controls + time label
    candidate_panel.py   ← Tab widget: Candidates, Manual, Export
    status_bar.py        ← QStatusBar with messages and counters
    skeleton.py          ← Loading skeleton screen
  dialogs/
    __init__.py
    batch_dialog.py      ← BatchDialog with animations
    preferences_dialog.py ← PreferencesDialog with theme support
    export_dialog.py     ← Save As dialog with profile selection
  main_window.py         ← RingForgeWindow (200 lines, composes sub-components)
```

---

## 5. ANIMATION PLAN (Emil Kowalski Philosophy)

### What Should Animate

| Element | Duration | Easing | Purpose |
|---------|----------|--------|---------|
| Button press | 160ms | ease-out | Feedback that UI heard the user |
| Dialog appear | 200-500ms | spring | Modal entrance |
| Candidate list appear | 30-80ms stagger | ease-out | Stagger when candidates load |
| Batch dialog show | 200ms | ease-out | Slide-in from right |
| Waveform zoom | 200ms | ease-out | Smooth zoom transition |
| Progress bar | 100-150ms | linear | Analysis progress |
| Tab switch | 150ms | ease-out | Tab transition |
| Tooltip | 125ms | ease-out | Tooltip appearance |

### What Should NOT Animate

| Element | Reason |
|---------|--------|
| Keyboard shortcuts (Space, Escape) | Used 100+ times/day, animation makes them feel slow |
| Playback position cursor | Constant motion, would be distracting |
| Volume slider | Real-time control, animation causes lag |

### Button Press Feedback Pattern (Emil Kowalski)

```python
# Before (no feedback):
def _on_download(self):
    self._download_btn.setEnabled(False)
    # ... analysis happens ...
    self._download_btn.setEnabled(True)

# After (with press feedback):
def _on_download(self):
    # Scale down instantly
    self._download_btn.animateGeometry(
        self._download_btn.geometry().adjusted(2, 2, -2, -2),
        100,  # instant press
    )
    # ... analysis happens ...
    # Scale back with spring
    self._download_btn.animateGeometry(
        original_geometry,
        200,  # spring back
    )
```

---

## 6. ACCESSIBILITY PLAN (WCAG 2.2 AA)

### P0 — Must Fix

| Criterion | Current State | Target | Fix |
|-----------|--------------|--------|-----|
| 1.4.11 Non-text Contrast | Focus rings invisible | ≥3:1 contrast | Add `QFocusFrame` with `#89b4fa` border |
| 2.4.7 Focus Visible | No focus indicators | Visible on all widgets | CSS: `QPushButton:focus { border: 2px solid #89b4fa; }` |
| 2.5.8 Target Size | Buttons vary in size | ≥24×24 pt | Set minimum sizes on all interactive widgets |
| 1.3.1 Info and Relationships | No semantic structure | Proper roles | `setAccessibleRole()`, `setAccessibleName()` |
| 4.1.2 Name, Role, Value | Screen readers can't identify widgets | Fully labeled | Set accessible names + descriptions |
| 1.4.10 Reflow | Fixed 900px width | Responsive | Add resize handlers, adaptive layout |

### Implementation

```python
# Every interactive widget gets:
button.setAccessibleName("Find Best Moment")
button.setAccessibleDescription("Download and analyze audio to find the best segment")
button.setMinimumSize(48, 48)  # Target size ≥24pt (36px at 96dpi)

# Focus management:
def _on_candidate_selected(self, row):
    # Move focus to candidate list item
    self._candidate_list.setFocus()
    item = self._candidate_list.item(row)
    self._candidate_list.scrollToItem(item)
```

---

## 7. UX WRITING SPEC (Frontloaded Verbs)

| Current | Should Be | Why |
|---------|-----------|-----|
| Analyze | Find Best Moment | Frontloads the verb, names the outcome |
| Prefs | Preferences | Full word, not abbreviation |
| Open File | Open Audio | More specific |
| Export Selected | Export Ringtone | Names the outcome |
| Export As... | Save Ringtone As... | Action + object |
| Batch | Batch Process | More descriptive |
| OK | Save | Restates the action |
| Cancel | Cancel | Keep as-is (standard) |

### Error Messages Pattern (what→why→how)

| Current | Should Be |
|---------|-----------|
| "Download Error" | "Failed to download audio — check your internet connection and try again" |
| "No candidates found" | "We couldn't find a good segment — try a different song or adjust the analysis duration" |
| "Save Error" | "Couldn't save your ringtone — make sure you have write access to the exports folder" |

---

## 8. PERFORMANCE PLAN

| Issue | Current | Fix | Target |
|-------|---------|-----|--------|
| Waveform render | Full pixmap rebuild on every paint | Dirty-region rendering, cached layers | ≤16ms per frame |
| Candidate list | Synchronous add | Staggered animation via timer | No UI freeze |
| Analysis feedback | No visual feedback | Skeleton screen + animated progress | Perceived instant |
| Tab switching | Instant switch with no transition | 150ms fade transition | Smooth perceived load |
| Audio preview | Re-trim on every click | Cache preview temp files | ≤50ms load |

### Skeleton Screen for Analysis

```python
class AnalysisSkeleton(QWidget):
    """Skeleton screen shown during analysis."""
    def __init__(self, parent=None):
        super().__init__(parent)
        # Animated pulse bars simulating waveform
        self._bars = []
        for i in range(50):
            bar = QFrame()
            bar.setFixedWidth(4)
            bar.setStyleSheet(f"background: {COLORS['waveform']}; border-radius: 2px;")
            self._bars.append(bar)
    
    def _animate(self):
        """Pulse animation using QPropertyAnimation."""
        for bar in self._bars:
            anim = QPropertyAnimation(bar, b"geometry")
            anim.setDuration(1000)
            anim.setStartValue(bar.geometry())
            anim.setEndValue(bar.geometry().adjusted(0, -10, 0, 10))
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
```

---

## 9. ICON SYSTEM (Lucide-style)

Replace all text-only buttons with SVG icons:

| Button | Current | Should Be |
|--------|---------|-----------|
| Open File | "Open File" | 📂 Open (SVG icon) |
| Analyze | "Analyze" | 🔍 Find Best Moment |
| Batch | "Batch" | 📋 Batch |
| Preferences | "Prefs" | ⚙️ Preferences |
| Play | "Play" | ▶ Play |
| Stop | "Stop" | ⏹ Stop |
| Export | "Export Selected" | ⬇ Export |
| Preview | "Preview" | ▶ Preview |

---

## 10. IMPLEMENTATION PRIORITY

### Phase 1 — Foundation (1 week)
1. ✅ Create `core/tokens.py` — design token system
2. ✅ Create `ui/theme/stylesheet.py` — CSS stylesheets for all widgets
3. ✅ Apply tokens to all existing widgets
4. ✅ Add focus indicators to all interactive widgets
5. ✅ Add accessible names/descriptions to all widgets
6. ✅ Set minimum target sizes (≥48px) on all buttons
7. ✅ Create `ui/components/button.py` — styled button with states
8. ✅ Create `ui/layout/header.py` — extracted top bar component

### Phase 2 — Visual Polish (1 week)
9. ✅ Add hover/focus/active/pressed states to all buttons
10. ✅ Add press feedback animation (160ms scale)
11. ✅ Add dialog animations (fade + scale for Preferences/Batch)
12. ✅ Add stagger animation to candidate list
13. ✅ Add skeleton screen for analysis loading
14. ✅ Add typography hierarchy (h1/h2/h3/body/small)
15. ✅ Apply spacing scale consistently
16. ✅ Add icon system (lucide-style SVG icons)

### Phase 3 — UX Completion (1 week)
17. ✅ Add empty state illustrations
18. ✅ Add error state with actionable messages
19. ✅ Add confirmation dialogs for batch processing
20. ✅ Add UX writing updates (frontloaded verbs)
21. ✅ Add reduced-motion preference toggle
22. ✅ Add animation for waveform zoom
23. ✅ Add tab switch transitions

### Phase 4 — Performance (1 week)
24. ✅ Optimize `_render_cache()` to only re-render dirty regions
25. ✅ Add lazy loading for candidate list
26. ✅ Add GPU-accelerated waveform rendering
27. ✅ Add `prefers-reduced-motion` equivalent via QSettings
28. ✅ Add animation performance profiling

---

## 11. VERIFICATION CHECKLIST

After each phase, verify:

- [ ] All 36 pytest tests still pass
- [ ] All widgets have accessible names
- [ ] Focus is visible on every interactive element
- [ ] No raw hex colors in widget code (only token references)
- [ ] Spacing follows the 4px grid scale
- [ ] Typography follows the defined hierarchy
- [ ] All buttons have hover/focus/active/pressed states
- [ ] Animations stay under 300ms
- [ ] No animation on keyboard-initiated actions
- [ ] Skeleton screens appear during async operations
- [ ] Error messages follow what→why→how pattern
- [ ] Waveform renders at ≤16ms per frame
- [ ] Reduced-motion preference works
- [ ] UI is usable at 30% zoom (high DPI)
- [ ] No `main_window.py` file exceeds 300 lines

---

## 12. SUCCESS METRICS

| Metric | Before | After Target |
|--------|--------|-------------|
| Design Review Score | 2.6/10 | 7/10 |
| Main Window Lines | 1005 | <200 (composed) |
| Component Files | 4 | 12+ |
| Hardcoded Colors | 12+ | 0 (tokens only) |
| Animations | 0 | 15+ |
| Accessibility Issues | 8+ Critical | 0 |
| Loading States | 0 | 3+ |
| Empty States | 0 | 3+ |
| Icon System | None | Lucide-style |
| Error Recovery | None | 5+ flows |
| Focus Indicators | None | All widgets |
| Waveform FPS | 15-20 | 30+ |
| Reduced Motion | None | Supported |
