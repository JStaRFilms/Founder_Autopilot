CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tracker_configs (
    project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    config_json TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_cursors (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('git', 'cos', 'filesystem', 'manual')),
    cursor_value TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, source)
);

CREATE TABLE IF NOT EXISTS raw_events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('git', 'cos', 'filesystem', 'manual')),
    observed_at TEXT NOT NULL,
    cursor_value TEXT,
    checksum TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_events_source_checksum
    ON raw_events(project_id, source, checksum);

CREATE INDEX IF NOT EXISTS idx_raw_events_project_observed_at
    ON raw_events(project_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS activity_events (
    id TEXT PRIMARY KEY,
    raw_event_id TEXT REFERENCES raw_events(id) ON DELETE SET NULL,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('git', 'cos', 'filesystem', 'manual')),
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL CHECK (actor = 'founder'),
    signal_type TEXT NOT NULL CHECK (
        signal_type IN ('code', 'writing', 'planning', 'research', 'ops', 'unknown')
    ),
    summary TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_activity_events_project_timestamp
    ON activity_events(project_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS invalid_events (
    id TEXT PRIMARY KEY,
    raw_event_id TEXT REFERENCES raw_events(id) ON DELETE SET NULL,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('git', 'cos', 'filesystem', 'manual')),
    source_event_id TEXT,
    error_reason TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_invalid_events_project_created_at
    ON invalid_events(project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS project_signals (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    focus_minutes INTEGER NOT NULL,
    drift_minutes INTEGER NOT NULL,
    context_switch_count INTEGER NOT NULL,
    confidence REAL NOT NULL,
    derived_from_event_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_project_signals_project_window
    ON project_signals(project_id, window_start DESC, window_end DESC);

CREATE TABLE IF NOT EXISTS focus_scores (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    score_date TEXT NOT NULL,
    score INTEGER NOT NULL,
    trend TEXT NOT NULL CHECK (trend IN ('up', 'flat', 'down')),
    contributing_signals_json TEXT NOT NULL,
    computed_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_focus_scores_project_date
    ON focus_scores(project_id, score_date);

CREATE TABLE IF NOT EXISTS nudges (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('focus', 'break', 'prioritize', 'review')),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    reason TEXT NOT NULL,
    target_channels_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'delivered', 'dismissed', 'snoozed'))
);

CREATE INDEX IF NOT EXISTS idx_nudges_project_status_created
    ON nudges(project_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS cycle_reports (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    average_focus_score REAL NOT NULL,
    top_wins_json TEXT NOT NULL,
    drift_patterns_json TEXT NOT NULL,
    recommended_actions_json TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cycle_reports_project_period
    ON cycle_reports(project_id, period_start, period_end);
