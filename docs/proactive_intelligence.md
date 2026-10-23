# Phase 8: Proactive Intelligence & Autonomous Situation Detection

NEXUS does not merely respond when prompted; it continuously evaluates the user's temporal and contextual graph to identify actionable, high-salience situations autonomously.

---

## 1. Core Principles

1. **Contextual Salience**: Evaluates user state across Calendar, Documents (Knowledge Vault), Tasks, Goals, and Dependencies without waiting for an explicit prompt.
2. **Permission First**: The system asks before taking action (`"Would you like me to create a preparation plan?"`). It never alters state or executes external actions without explicit user confirmation.
3. **Multi-Factor Priority Normalization**: Priorities are not arbitrary integers or static tags; they are computed dynamically via 6 normalized factors and bounded to $[0.0, 1.0]$.
4. **Anti-Spam & User Agency**: Users have total control over notification frequency, muted categories, daily recommendation caps, and individual recommendation dismissals.

---

## 2. Situation Detection

The detection engine (`app.services.proactive.detector.ProactiveDetector`) monitors 8 distinct situations:

| # | Situation Category | Detection Logic | Actionable Proposal |
|---|--------------------|-----------------|---------------------|
| 1 | **Preparation Gaps** | Tomorrow's calendar has an interview, Job Description exists in Knowledge Vault, but no active interview preparation task exists. | *"Your interview is tomorrow and you don't currently have an interview preparation task. I found the job description and relevant projects. Would you like me to create a preparation plan?"* |
| 2 | **Conflicting Events** | Overlapping calendar events with positive intersection minutes. | Reschedule or propose an alternate free slot. |
| 3 | **Overdue Tasks** | Active tasks whose `due_date < today`. | Reschedule or mark complete. |
| 4 | **Upcoming Deadlines** | High-impact tasks due today, tomorrow, or within 72 hours. | Reserve dedicated focus blocks. |
| 5 | **Unfinished High-Priority Tasks** | High or Urgent tasks residing in `todo` or `blocked` status. | Decompose complex blockers into manageable subtasks. |
| 6 | **Inactive Goals** | Active goals registering 0% progress with no recent progress logs. | Generate actionable kickoff milestones. |
| 7 | **Interviews** | Interviews detected within the upcoming 7-day window. | Review STAR narratives and job requirements. |
| 8 | **Important Upcoming Events** | Salient meetings, deadlines, demos, or reviews in next 24–48 hours. | View briefing notes and attendee context. |

---

## 3. Multi-Factor Priority Engine

Calculated via `app.services.proactive.priority_engine.PriorityEngine`:

$$\text{Priority} = w_{\text{urgency}} \cdot U + w_{\text{deadline}} \cdot D + w_{\text{goal}} \cdot G + w_{\text{importance}} \cdot I + w_{\text{dependencies}} \cdot Dep + w_{\text{effort}} \cdot E$$

### Weights & Components
- **Urgency ($w = 0.22$)**: Priority tag assessment (`urgent` = 1.0, `high` = 0.8, `medium` = 0.5, `low` = 0.2).
- **Deadline ($w = 0.22$)**: Distance to deadline (Overdue = 1.0, Today = 0.95, Tomorrow = 0.85, $\le$ 3 days = 0.70, $\le$ 7 days = 0.50, distant = 0.30, none = 0.15).
- **Goal Relevance ($w = 0.18$)**: Semantic and keyword alignment with user's active goals.
- **Importance ($w = 0.16$)**: Salience keywords (`interview`, `production`, `launch`, `client`, `security`).
- **Dependencies ($w = 0.12$)**: Unblocking potential (`blocker`, `prerequisite`, `core`, `foundation`).
- **Estimated Effort ($w = 0.10$)**: Quick wins vs. deep-focus scheduling requirements.

The weighted sum is strictly normalized to $[0.0, 1.0]$ and categorized into:
- $\ge 0.80$: `urgent`
- $\ge 0.65$: `high`
- $\ge 0.45$: `medium`
- $< 0.45$: `low`

---

## 4. Anti-Spam & User Safety

The proactive intelligence pipeline enforces strict anti-spam rules through `ProactiveService`:
- **Proactive Master Switch**: Users can toggle proactive suggestions on or off completely (`enabled: false`).
- **Frequency Controls**: Configurable evaluation pace (`immediate`, `hourly`, `daily`).
- **Daily Volume Cap**: Enforces `max_daily_recommendations` (default: 5) to keep dashboards clear.
- **24-Hour Dismissal Memory**: Dismissed recommendations are archived with `status="dismissed"` and `dismissed_at` timestamps, preventing duplicate alerts for 24 hours.
- **Muted Categories**: Users can selectively mute any category (e.g., mute `overdue_task` or `conflicting_events`).

---

## 5. API Reference

### Recommendations
- `GET /recommendations`: Returns all active recommendations for the user. Evaluates detection automatically if cache is empty.
- `POST /recommendations/generate`: Forces immediate proactive situation scan across all subsystems.
- `POST /recommendations/{id}/dismiss`: Dismisses a recommendation and records timestamp.
- `POST /recommendations/{id}/act`: Confirms and executes the recommended action (e.g., launching the Flagship Interview Prep Workflow).

### Preferences
- `GET /recommendations/preferences`: Retrieves proactive preferences and anti-spam settings.
- `PUT /recommendations/preferences`: Updates notification settings, daily limits, frequency, and muted categories.

---

## 6. Dashboard Integration

The dashboard incorporates the **AI Recommendations** component:
- Glassmorphic proactive intelligence banner with live pulse indicator.
- Action cards highlighting:
  - Recommendation message
  - Reason / Context
  - Priority badge & normalized score (e.g., `URGENT (0.95)`)
  - Related goal & deadline tags
  - Interactive **Action Button** (e.g., "Create Plan")
  - **Dismiss Button**
- **Scan Now** button for on-demand evaluation.
- Dedicated **Anti-Spam Preferences Modal** with frequency dropdown, daily limit slider, category muting, and master killswitch.
