-- Questions table
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_questions_slug ON questions(slug);
CREATE INDEX idx_questions_text_search ON questions USING GIN (to_tsvector('english', text));

-- Answer versions (append-only)
CREATE TABLE answer_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id),
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'preliminary'
        CHECK (status IN ('preliminary', 'debating', 'consensus_reached', 'sealed', 'contested')),
    preliminary_answer TEXT,
    final_answer TEXT,
    confidence FLOAT,
    sealed_at TIMESTAMPTZ,
    seal_hash TEXT,
    previous_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(question_id, version)
);

CREATE INDEX idx_answer_versions_question ON answer_versions(question_id);
CREATE INDEX idx_answer_versions_status ON answer_versions(status);

-- Source responses (evidence from adapters)
CREATE TABLE source_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    answer_version_id UUID NOT NULL REFERENCES answer_versions(id),
    source_name TEXT NOT NULL,
    raw_response TEXT NOT NULL,
    claims JSONB NOT NULL DEFAULT '[]',
    confidence FLOAT,
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_source_responses_answer ON source_responses(answer_version_id);

-- Debate rounds
CREATE TABLE debate_rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    answer_version_id UUID NOT NULL REFERENCES answer_versions(id),
    round_number INTEGER NOT NULL,
    phase TEXT NOT NULL
        CHECK (phase IN ('evidence_gathering', 'initial_positions', 'counterarguments', 'synthesis', 'convergence_check')),
    positions JSONB NOT NULL DEFAULT '[]',
    arguments JSONB NOT NULL DEFAULT '[]',
    synthesis JSONB,
    convergence_score FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(answer_version_id, round_number)
);

CREATE INDEX idx_debate_rounds_answer ON debate_rounds(answer_version_id);

-- Row-level security: sealed answer_versions cannot be updated
ALTER TABLE answer_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read answer versions"
    ON answer_versions FOR SELECT
    USING (true);

CREATE POLICY "Only non-sealed can be updated"
    ON answer_versions FOR UPDATE
    USING (status != 'sealed');

CREATE POLICY "Insert always allowed"
    ON answer_versions FOR INSERT
    WITH CHECK (true);
