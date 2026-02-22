-- Run this in the Supabase SQL Editor
CREATE TABLE IF NOT EXISTS customers (
    phone TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    last_payment_amount TEXT,
    last_payment_date TEXT,
    event_type TEXT,
    venue TEXT,
    event_date TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Realtime for this table (optional but good for syncing)
ALTER PUBLICATION supabase_realtime ADD TABLE customers;
