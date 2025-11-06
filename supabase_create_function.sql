-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    username TEXT,
    message TEXT NOT NULL,
    response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create RPC function to create the table
CREATE OR REPLACE FUNCTION create_conversations_table()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Ensure the table exists
    CREATE TABLE IF NOT EXISTS conversations (
        id BIGSERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        username TEXT,
        message TEXT NOT NULL,
        response TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
END;
$$;
