
CREATE TABLE rrc_events (id SERIAL PRIMARY KEY, county TEXT, event_type TEXT, value INT, operator TEXT, period TEXT, source_url TEXT NOT NULL, evidence TEXT, scraped_at TIMESTAMP);
CREATE TABLE sec_events (id SERIAL PRIMARY KEY, operator TEXT, target TEXT, net_acres INT, boepd INT, locations INT, close_date TEXT, source_url TEXT NOT NULL);
CREATE TABLE select_public_footprint (id SERIAL PRIMARY KEY, facility_name TEXT, address TEXT, lat DOUBLE, lon DOUBLE, type TEXT, source_url TEXT NOT NULL);
CREATE TABLE argos_opportunities (id TEXT PRIMARY KEY, created_at TIMESTAMP, status TEXT, why_now TEXT, commercial_signal TEXT, why_select TEXT, next_action TEXT, evidence TEXT[]);
CREATE TABLE select_private_feedback (id SERIAL PRIMARY KEY, case_id TEXT, type TEXT, value TEXT, facility TEXT, location TEXT, county TEXT, received_at TIMESTAMP, effect TEXT);
