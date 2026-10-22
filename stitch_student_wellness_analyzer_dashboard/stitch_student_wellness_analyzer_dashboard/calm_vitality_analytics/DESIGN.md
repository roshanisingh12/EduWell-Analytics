---
name: Calm Vitality Analytics
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3d4947'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6d7a77'
  outline-variant: '#bcc9c6'
  surface-tint: '#006a61'
  primary: '#00685f'
  on-primary: '#ffffff'
  primary-container: '#008378'
  on-primary-container: '#f4fffc'
  inverse-primary: '#6bd8cb'
  secondary: '#006398'
  on-secondary: '#ffffff'
  secondary-container: '#5bb8fe'
  on-secondary-container: '#00476e'
  tertiary: '#545c72'
  on-tertiary: '#ffffff'
  tertiary-container: '#6c748b'
  on-tertiary-container: '#fefcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#89f5e7'
  primary-fixed-dim: '#6bd8cb'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#005049'
  secondary-fixed: '#cce5ff'
  secondary-fixed-dim: '#93ccff'
  on-secondary-fixed: '#001d31'
  on-secondary-fixed-variant: '#004b73'
  tertiary-fixed: '#dae2fd'
  tertiary-fixed-dim: '#bec6e0'
  on-tertiary-fixed: '#131b2e'
  on-tertiary-fixed-variant: '#3f465c'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 3rem
    fontWeight: '600'
    lineHeight: 3.5rem
    letterSpacing: -0.025em
  headline-xl:
    fontFamily: Inter
    fontSize: 2.25rem
    fontWeight: '600'
    lineHeight: 2.75rem
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 1.75rem
    fontWeight: '600'
    lineHeight: 2.25rem
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 1.25rem
    fontWeight: '500'
    lineHeight: 1.75rem
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: '400'
    lineHeight: 1.75rem
  body-md:
    fontFamily: Inter
    fontSize: 0.9375rem
    fontWeight: '400'
    lineHeight: 1.5rem
  body-sm:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.25rem
  stat-numeric:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: '600'
    lineHeight: 2.25rem
    letterSpacing: -0.02em
  label-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '500'
    lineHeight: 1.25rem
  label-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '600'
    lineHeight: 1rem
    letterSpacing: 0.025em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-sm: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
---

## Brand & Style

This design system establishes an empathetic, non-clinical wellness analytics environment built specifically for students, university advisors, and wellness coordinators. Rather than clinical coldness or alarmist dashboards, the interface projects calm clarity, emotional safety, and scientific reassurance. 

The aesthetic is Modern Minimalist infused with subtle Soft Glass and Tonal Layering:
- **Atmosphere:** Uncluttered, breathing, and optimistic. Metrics are displayed to foster healthy habit discovery rather than panic or surveillance fatigue.
- **Tone of Voice in Visuals:** Structured, respectful, and supportive. Critical alert states are softened through warm, organic semantic tints to eliminate acute anxiety triggers while retaining high informational fidelity.
- **Visual Rhythm:** Balanced data densities with generous negative space, allowing complex multi-variable correlations (sleep, academic workload, physical activity, and stress) to be comprehended effortlessly.

## Colors

The color system anchors on a balancing spectrum of deep sea teals and sky-toned slates, offset by crisp porcelain neutrals and high-clarity semantic wellness states:

- **Primary (`#0D9488`):** Deep oceanic teal represents equilibrium, rejuvenation, and deliberate balance. Used for primary interactive triggers, active navigation items, and primary trend lines.
- **Secondary (`#0284C7`):** Clear slate blue denotes cognitive clarity, focus, and hydration/sleep metrics. Used for secondary comparison metrics and subtle categorical data vectors.
- **Tertiary (`#0F172A`):** Obsidian slate anchors visual hierarchy, high-contrast typography, and definitive statistical markers.
- **Background & Card Surfaces:** The canvas remains firmly `#F8FAFC`, avoiding sterile pure-white blinding backgrounds. Pure `#FFFFFF` is reserved strictly for elevated containers and interactive cards to create immediate spatial division.
- **Semantic Stress Scale:**
  - *Low Stress (`#10B981` / `#ECFDF5`):* Emerald green communicates restoration and safe equilibrium.
  - *Moderate Stress (`#F59E0B` / `#FFFBEB`):* Warm amber signals emerging fatigue or elevated cognitive load needing mindful attention.
  - *High Stress (`#EF4444` / `#FEF2F2`):* Soft coral-rose acts as an empathetic warning marker rather than a punitive error state.

## Typography

The typography relies entirely on a precision-calibrated Inter font stack, leveraging tabular figures (`font-variant-numeric: tabular-nums`) across statistical views to prevent horizontal visual jitter in fluctuating data feeds.

- **Numerics & Analytics:** Key performance indicators and index scores employ `stat-numeric` with medium-to-semibold weights and tight negative tracking to deliver clear analytical readability.
- **Headings:** Headlines prefer medium and semibold weights over heavy bolding, maintaining a calm, approachable presence across large analytical displays.
- **Labels & Micro-text:** Data points, table column heads, and category labels utilize `label-sm` with slight uppercase letter-spacing to distinguish structural navigation from dynamic student observations.

## Layout & Spacing

The dashboard employs a 12-column responsive fluid grid structured around dedicated analytical zones (Global Filters, Primary Metric Ribbons, Deep Analytic Charts, and Contextual Resource Feeds).

- **Grid Geometry:**
  - **Desktop (≥ 1280px):** 12 columns with `1.5rem` (`24px`) gutters and `2rem` (`32px`) margins. Sidebar controls dock at a fixed width of `260px`, with the analytic canvas expanding fluidly.
  - **Tablet (768px – 1279px):** 8 columns with `1rem` (`16px`) gutters and `1.5rem` (`24px`) margins. Data cards collapse from 4-column structures into 2x2 grids.
  - **Mobile (< 768px):** 4 columns with `1rem` gutters and `1rem` outer canvas padding. Metric tiles stack sequentially to preserve touch target safety and legibility.
- **Internal Card Rhythm:** Component padding scales predictably: compact widgets utilize `space-md` (`16px`), standard analytics panels utilize `space-lg` (`24px`), and broad overview summary tiles utilize `space-xl` (`32px`).

## Elevation & Depth

Visual hierarchy operates via a low-elevation architecture pairing soft, colored-ambient drop shadows with boundary-defining micro-borders (`1px solid #E2E8F0`).

- **Base Layer (Level 0):** Canvas background (`#F8FAFC`). No elevation.
- **Card Surfaces (Level 1):** `#FFFFFF` surfaces sit slightly above the canvas with a soft teal-tinted ambient drop shadow:
  - `box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.02);`
- **Interactive / Hover Surfaces (Level 2):** Cards or actionable modules subtly lift upon focus or cursor hover:
  - `box-shadow: 0 4px 6px -1px rgba(13, 148, 136, 0.06), 0 2px 4px -2px rgba(15, 23, 42, 0.04);`
  - Subtle `transform: translateY(-1px)` transition with standard ease.
- **Tooltips & Floating Overlays (Level 3):** Modal sheets, informational floating badges, and rich tooltips employ deep non-obtrusive diffusion:
  - `box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04);`

## Shapes

The interface embraces a balanced curvature model that conveys organic wellness without forfeiting dashboard precision.

- **Primary Metric Cards:** Structured with `rounded-xl` (`1rem` / `16px`) to ensure an approachable, touch-friendly, and calm perimeter.
- **Hero Containers & Major Panes:** Anchored with `rounded-2xl` (`1.5rem` / `24px`) to distinctly group related data ecosystems.
- **Interactive Triggers & Inputs:** Standardized at `rounded-md` (`0.5rem` / `8px`) for buttons, form selectors, and table containers.
- **Info Pills & Chips:** Styled in full pill-shape (`rounded-full` / `9999px`) to immediately denote non-actionable status metadata and friendly educational tooltips.

## Components

### Buttons
- **Primary:** Solid `#0D9488` background with `#FFFFFF` text. Medium weight, `rounded-md`, padded with `0.5rem 1rem`. Focus ring: `2px` offset with `#0D9488`.
- **Secondary / Ghost:** Transparent background with `#E2E8F0` border and `#0F172A` text. Hover state switches background to `#F1F5F9`.
- **Destructive / High Alert:** Subtle tinted `#FEF2F2` background with `#991B1B` text; borders shift to `#FECACA`.

### Chips & Semantic Status Badges
- Display wellness and stress states using soft-tint surfaces paired with darker text for optimal contrast:
  - **Low Stress Chip:** `#ECFDF5` background, `#065F46` label, small 6px dot indicator in solid `#10B981`.
  - **Moderate Stress Chip:** `#FFFBEB` background, `#92400E` label, small 6px dot indicator in solid `#F59E0B`.
  - **High Stress Chip:** `#FEF2F2` background, `#991B1B` label, small 6px dot indicator in solid `#EF4444`.
- Shape: Full pill (`rounded-full`), padded with `0.25rem 0.75rem`.

### Statistical Tables
- Clear headers in `label-sm` with uppercase letter spacing, colored `#64748B`.
- Thin row dividers using `1px solid #F1F5F9`.
- Hover state on rows applies a quiet tint of `#F8FAFC`.
- Numerical columns right-align and use `font-variant-numeric: tabular-nums`.

### Form Controls & Inputs
- Text inputs and dropdowns feature a `#FFFFFF` fill, `#E2E8F0` border, and `rounded-md` corners.
- Active and focus states transition to a subtle teal ring: `border-color: #0D9488` with a `0 0 0 3px rgba(13, 148, 136, 0.15)` outer glow.
- Checkboxes and radios display custom `#0D9488` fills when selected.

### Analytics Cards & Educational Info Pills
- Cards feature a `#FFFFFF` surface, `1px solid #E2E8F0` border, and `rounded-xl` corners.
- Header bars host the primary metric, trend arrow, and an unobtrusive info pill trigger (`?` or `ℹ`).
- Educational tooltips render in `#0F172A` with `#F8FAFC` text, `rounded-lg` corners, explaining analytical terms in human-centric, encouraging language.