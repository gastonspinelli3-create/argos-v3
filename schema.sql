
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, plan TEXT, tier_name TEXT, status TEXT, live_until TIMESTAMPTZ, access_until TIMESTAMPTZ, founding_license BOOLEAN, token_hash TEXT UNIQUE, kms_key_id TEXT, price_paid_usd INT, cases_allowed INT, basins_allowed INT, features JSONB);
CREATE TABLE IF NOT EXISTS tenant_basins (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE, basin_id TEXT, basin_name TEXT, UNIQUE(tenant_id, basin_id));
INSERT INTO tenants (id, plan, tier_name, status, live_until, access_until, founding_license, token_hash, kms_key_id, price_paid_usd, cases_allowed, basins_allowed, features) VALUES ('argos_ent_pilot_90','pilot_90','Starter','active',NOW()+INTERVAL '90 days',NOW()+INTERVAL '90 days',false,'7be066312bd91c7faa402bfac63ddea16de0fab589b53aba564e79b9c9b82411','kms_90',90000,5,1,'{}'::jsonb) ON CONFLICT (id) DO UPDATE SET token_hash=EXCLUDED.token_hash;
INSERT INTO tenant_basins (tenant_id, basin_id, basin_name) VALUES ('argos_ent_pilot_90','midland','Midland Basin') ON CONFLICT (tenant_id, basin_id) DO NOTHING;
