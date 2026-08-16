-- AI Exam Tutor — SQLite schema (MVP v1.0)
-- Mirrors §3.2 of spec.md. Loaded by DBManager on first connection.
-- Designed to be idempotent: every CREATE uses IF NOT EXISTS.

-- -----------------------------------------------------------------------------
-- app_config: flat key/value store for runtime configuration.
-- Holds: API keys, active provider, base URLs, model names, theme preference,
-- last opened PDF path, etc. Replaces .json / .ini config files per CLAUDE.md §4.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- -----------------------------------------------------------------------------
-- attempts: one row per student exam attempt.
-- subject = 'inf03' in v1.0; other subjects added in v1.1+.
-- score_json stores per-rubric scores (Content/Coherence/...) as JSON.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    subject      TEXT NOT NULL,
    exam_pdf     TEXT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    score_json   TEXT
);

-- Index for the (deferred) attempt-history sidebar — cheap to add now.
CREATE INDEX IF NOT EXISTS idx_attempts_subject_started
    ON attempts (subject, started_at DESC);

-- -----------------------------------------------------------------------------
-- messages: full chat transcript with the AI Tutor.
-- role ∈ {'user', 'assistant', 'system'}.
-- ON DELETE CASCADE: dropping an attempt wipes its chat history.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id  INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_attempt_created
    ON messages (attempt_id, created_at);

-- -----------------------------------------------------------------------------
-- drafts: workspace auto-save target. PK = (attempt_id, file_name) lets us
-- store one row per editor tab (e.g. 'query.sql', 'index.php', 'index.html').
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drafts (
    attempt_id   INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    file_name    TEXT NOT NULL,
    content      TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (attempt_id, file_name)
);