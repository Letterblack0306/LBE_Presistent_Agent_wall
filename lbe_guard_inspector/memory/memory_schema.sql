PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS workspace_memory (
    memory_id TEXT PRIMARY KEY,
    project_workspace_id TEXT NOT NULL,
    canonical_workspace_root TEXT NOT NULL,
    task_id TEXT,
    rule_id TEXT,
    memory_type TEXT NOT NULL CHECK (memory_type IN (
        'workspace_fact',
        'task_constraint',
        'decision',
        'failure_pattern',
        'validation_result',
        'checkpoint',
        'user_preference',
        'historical_observation'
    )),
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    value_json TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_path TEXT,
    source_hash TEXT,
    source_commit TEXT,
    source_message_id TEXT,
    authority INTEGER NOT NULL DEFAULT 0,
    validation_status TEXT NOT NULL CHECK (validation_status IN (
        'verified',
        'unverified',
        'stale',
        'contradicted',
        'superseded'
    )),
    validation_method TEXT,
    validated_at TEXT,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    superseded_by TEXT,
    FOREIGN KEY (superseded_by) REFERENCES workspace_memory(memory_id)
);

CREATE INDEX IF NOT EXISTS idx_workspace_memory_project
    ON workspace_memory(project_workspace_id, validation_status);
CREATE INDEX IF NOT EXISTS idx_workspace_memory_task
    ON workspace_memory(project_workspace_id, task_id, validation_status);
CREATE INDEX IF NOT EXISTS idx_workspace_memory_rule
    ON workspace_memory(project_workspace_id, rule_id, validation_status);
CREATE INDEX IF NOT EXISTS idx_workspace_memory_subject
    ON workspace_memory(project_workspace_id, subject, predicate);
CREATE INDEX IF NOT EXISTS idx_workspace_memory_source
    ON workspace_memory(source_path, source_hash);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_memory_identity
    ON workspace_memory(
        project_workspace_id,
        COALESCE(task_id, ''),
        COALESCE(rule_id, ''),
        memory_type,
        subject,
        predicate,
        source_type,
        COALESCE(source_path, ''),
        COALESCE(source_message_id, '')
    )
    WHERE validation_status NOT IN ('superseded');

CREATE TABLE IF NOT EXISTS memory_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    project_workspace_id TEXT NOT NULL,
    canonical_workspace_root TEXT NOT NULL,
    source_prefix_hash TEXT NOT NULL,
    source_message_count INTEGER NOT NULL CHECK (source_message_count >= 0),
    source_last_message_key TEXT,
    branch TEXT,
    head TEXT,
    verified_memory_ids_json TEXT NOT NULL,
    active_constraints_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_checkpoints_session
    ON memory_checkpoints(session_id, created_at DESC);
