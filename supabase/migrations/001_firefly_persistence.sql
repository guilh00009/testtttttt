-- FIREFLY consciousness persistence (survives HF Space 24h resets)
-- Run in Supabase SQL editor or: supabase db push

CREATE TABLE IF NOT EXISTS firefly_memories (
    id BIGSERIAL PRIMARY KEY,
    agent_id TEXT NOT NULL DEFAULT 'firefly',
    content TEXT NOT NULL,
    memory_type TEXT NOT NULL DEFAULT 'thought',
    mood TEXT DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_firefly_memories_agent_created
    ON firefly_memories (agent_id, created_at DESC);

CREATE TABLE IF NOT EXISTS firefly_stats (
    id TEXT PRIMARY KEY DEFAULT 'firefly',
    lifetime_thoughts INT NOT NULL DEFAULT 0,
    chats_accepted INT NOT NULL DEFAULT 0,
    chats_rejected INT NOT NULL DEFAULT 0,
    first_awake TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO firefly_stats (id) VALUES ('firefly') ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS firefly_thought_log (
    id BIGSERIAL PRIMARY KEY,
    agent_id TEXT NOT NULL DEFAULT 'firefly',
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    kind TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_firefly_thought_log_agent
    ON firefly_thought_log (agent_id, logged_at DESC);

-- RLS: service role key (HF Space secret) bypasses RLS.
-- Anon key needs explicit policies if used client-side.
ALTER TABLE firefly_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE firefly_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE firefly_thought_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_all_memories" ON firefly_memories
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "service_all_stats" ON firefly_stats
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "service_all_thought_log" ON firefly_thought_log
    FOR ALL USING (true) WITH CHECK (true);
