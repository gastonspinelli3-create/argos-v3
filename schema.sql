-- ARGOS V3.0 FINAL - Fuente de verdad DB
-- Implementa pipeline completo auditado: PUBLIC INTELLIGENCE -> SIGNAL -> INFERENCE -> HYPOTHESIS -> UNKNOWN -> PRIVATE -> RECALCULATION -> COMMERCIAL OPPORTUNITY
-- No asume, verifica cada fix

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tenants con auth real: tenant_id != secret, token_hash almacenado
CREATE TABLE tenants (
    id TEXT PRIMARY KEY, -- ej: argos_ent_pilot_270
    internal_ref TEXT,
    google_sub_hash TEXT,
    plan TEXT NOT NULL CHECK (plan IN ('pilot_90','pilot_180','pilot_270','trial_7')),
    tier_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','expired','suspended','founding_historical_only','pending_payment')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    live_until TIMESTAMPTZ NOT NULL, -- 90 dias para todos: fin feeds vivos
    access_until TIMESTAMPTZ NOT NULL, -- Starter/Pro = live_until, Founding = live_until + 12 meses
    founding_license BOOLEAN NOT NULL DEFAULT false,
    token_hash TEXT NOT NULL UNIQUE, -- SHA256 del token aleatorio, no tenant_id
    kms_key_id TEXT NOT NULL,
    price_paid_usd INT NOT NULL CHECK (price_paid_usd IN (0,90000,180000,270000)),
    cases_allowed INT NOT NULL CHECK (cases_allowed IN (2,5,10,15)),
    basins_allowed INT NOT NULL,
    features JSONB NOT NULL,
    payment_status TEXT DEFAULT 'paid',
    internal_notes TEXT
);
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tenants FOR ALL USING (id = current_setting('app.current_tenant', true)::TEXT);

CREATE TABLE tenant_basins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    basin_id TEXT NOT NULL CHECK (basin_id IN ('midland','delaware','eagle_ford')),
    basin_name TEXT NOT NULL,
    activated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tenant_id, basin_id)
);
ALTER TABLE tenant_basins ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tenant_basins FOR ALL USING (tenant_id = current_setting('app.current_tenant', true)::TEXT);

-- Evidence con URL especifica, accessed_at, snapshot_hash, http_status
CREATE TABLE evidence_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type TEXT NOT NULL CHECK (source_type IN ('RRC','SEC_EDGAR','DRILLINGEDGE','REXTAG','MINERALRIGHTS','EIA','FRACFOCUS','ENERGYNOW','OTHER')),
    url TEXT NOT NULL,
    url_specific BOOLEAN NOT NULL DEFAULT true, -- false si es https://sec.gov generica
    title TEXT,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    http_status INT,
    content_hash TEXT, -- SHA256 del contenido para snapshot
    snapshot_hash TEXT, -- hash del snapshot/documento
    is_primary BOOLEAN NOT NULL DEFAULT false, -- true si es doc primario RRC/SEC
    is_secondary BOOLEAN NOT NULL DEFAULT false, -- true si es foro/blog/agregador
    notes TEXT
);

-- Opportunities con separacion epistemologica estricta
CREATE TABLE opportunities (
    id TEXT PRIMARY KEY,
    basin_id TEXT NOT NULL CHECK (basin_id IN ('midland','delaware','eagle_ford')),
    basin_name TEXT NOT NULL,
    tier_required TEXT NOT NULL CHECK (tier_required IN ('pilot_90','pilot_180','pilot_270')),
    tier_min_price INT NOT NULL,
    county TEXT NOT NULL,
    operator TEXT NOT NULL,
    -- Capas obligatorias
    facts JSONB NOT NULL, -- [{fact_id, type: HECHO, description, evidence_id, observed_at, is_secondary, secondary_attribution}]
    inferences JSONB NOT NULL, -- [{inference_id, type: INFERENCIA, description, formula, inputs: [fact_id], methodology, status: VALIDADA|NO_VALIDADA|ESCENARIO, scenario_wor: [2,4,6]}]
    hypothesis TEXT NOT NULL,
    unknown_data JSONB NOT NULL, -- ["WOR real", "water production real", "SWD capacity", ...]
    opportunity_statement TEXT NOT NULL, -- OPORTUNIDAD DE INVESTIGACION, no "Vender recycling"
    what_collected JSONB NOT NULL,
    how_connected TEXT NOT NULL,
    what_you_had_not_seen TEXT NOT NULL,
    verification_notes TEXT NOT NULL,
    temporal_claim TEXT NOT NULL, -- "Anunciado Aug 2026, cierre previsto Sep 2026 segun EnergyNow, sujeto a condiciones, requiere confirmacion SEC 8-K"
    temporal_evidence_id UUID REFERENCES evidence_sources(id),
    bwpd_projected JSONB, -- {type: INFERENCIA|ESCENARIO, methodology, depends_on_private: true, status: NO_VALIDADA}
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','PARTIALLY_VERIFIED','NEEDS_REVIEW','DISPUTED')),
    public_evidence_count INT NOT NULL DEFAULT 0,
    decision TEXT NOT NULL CHECK (decision IN ('MANTENER','REFORMULAR','DESCARTAR')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Private uploads con MIME, size, validation real
CREATE TABLE user_private_uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    basin_id TEXT CHECK (basin_id IN ('midland','delaware','eagle_ford')),
    opportunity_id TEXT REFERENCES opportunities(id),
    upload_type TEXT NOT NULL CHECK (upload_type IN ('pipeline_map','costs_per_bbl','production_volumes','water_volumes','contracts','custom')),
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INT NOT NULL CHECK (size_bytes <= 50*1024*1024), -- 50MB max
    data_encrypted TEXT NOT NULL,
    parsed_summary JSONB, -- {variables_detected: ["cost_per_bbl_trucking", "wor_real"], linking: [...]}
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE user_private_uploads ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON user_private_uploads FOR ALL USING (tenant_id = current_setting('app.current_tenant', true)::TEXT);

-- Recalculation REAL, no hardcodeado
CREATE TABLE opportunity_recalculations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    opportunity_id TEXT NOT NULL REFERENCES opportunities(id),
    private_upload_ids UUID[] NOT NULL,
    -- Resultado real de procesamiento
    verification_status TEXT NOT NULL CHECK (verification_status IN ('ENHANCED','CALCULABLE_WITH_PRIVATE_DATA','STILL_MISSING_DATA')),
    public_evidence INT NOT NULL, -- count real de facts con evidence_id
    private_evidence INT NOT NULL, -- count real de variables detectadas en uploads
    remaining_unknowns INT NOT NULL, -- unknown_data - private_evidence
    calculation_status TEXT NOT NULL CHECK (calculation_status IN ('CALCULABLE_WITH_PRIVATE_DATA','ESTIMATED','NOT_CALCULABLE')),
    result JSONB NOT NULL, -- {excess_bpd, delta_per_day, methodology, trace: [{fact_id, private_var}]}
    algorithm_version TEXT NOT NULL DEFAULT 'v3.0',
    request_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE opportunity_recalculations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON opportunity_recalculations FOR ALL USING (tenant_id = current_setting('app.current_tenant', true)::TEXT);

-- Audit log completo para empresa
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id TEXT NOT NULL,
    user_id TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action TEXT NOT NULL CHECK (action IN ('authenticate','list_basins','list_opportunities','view_opportunity','upload_private','recalculate','upgrade','deactivate')),
    opportunity_id TEXT,
    upload_id UUID,
    result TEXT,
    algorithm_version TEXT,
    request_id TEXT NOT NULL,
    ip TEXT,
    rls_context_set BOOLEAN NOT NULL DEFAULT false
);

-- Tenant models con RLS
CREATE TABLE tenant_models (
    tenant_id TEXT PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    learnings_count INT DEFAULT 0,
    private_uploads_count INT DEFAULT 0,
    networks_connected TEXT[] DEFAULT ARRAY['RRC','SEC_EDGAR','DRILLINGEDGE','REXTAG','MINERALRIGHTS','EIA'],
    model_version TEXT DEFAULT 'v3.0'
);
ALTER TABLE tenant_models ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tenant_models FOR ALL USING (tenant_id = current_setting('app.current_tenant', true)::TEXT);

-- Seed con token_hash (SHA256 de token aleatorio) y founding logic correcta
-- Tokens de ejemplo: en prod generar con secrets.token_urlsafe(32)
INSERT INTO tenants (id, internal_ref, google_sub_hash, plan, tier_name, status, live_until, access_until, founding_license, token_hash, kms_key_id, price_paid_usd, cases_allowed, basins_allowed, features) VALUES
('argos_ent_pilot_90', 'CONTRACT-90', 'hash_90', 'pilot_90', 'Starter - 1 Basin', 'active', NOW() + INTERVAL '90 days', NOW() + INTERVAL '90 days', false, encode(digest('tok_starter_90_' || gen_random_uuid()::text, 'sha256'), 'hex'), 'kms-90', 90000, 5, 1, '{"tier":"starter","renewal":30000,"entitlement":"5 casos"}'),
('argos_ent_pilot_180', 'CONTRACT-180', 'hash_180', 'pilot_180', 'Professional - 2 Basins', 'active', NOW() + INTERVAL '90 days', NOW() + INTERVAL '90 days', false, encode(digest('tok_pro_180_' || gen_random_uuid()::text, 'sha256'), 'hex'), 'kms-180', 180000, 10, 2, '{"tier":"professional","renewal":60000}'),
('argos_ent_pilot_270', 'CONTRACT-270', 'hash_270', 'pilot_270', 'Founding Enterprise - FULL', 'active', NOW() + INTERVAL '90 days', NOW() + INTERVAL '365 days', true, encode(digest('tok_founding_270_' || gen_random_uuid()::text, 'sha256'), 'hex'), 'kms-270', 270000, 15, 3, '{"tier":"founding","license":"acceso perpetuo a corpus generado hasta access_until, feeds live posteriores opcionales $15k/mes","renewal_optional":15000}'),
('argos_ent_trial_01', 'TRIAL-001', 'hash_trial', 'trial_7', 'Trial', 'active', NOW() + INTERVAL '7 days', NOW() + INTERVAL '7 days', false, encode(digest('tok_trial_' || gen_random_uuid()::text, 'sha256'), 'hex'), 'kms-trial', 0, 2, 1, '{"tier":"trial"}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO tenant_basins (tenant_id, basin_id, basin_name) VALUES
('argos_ent_pilot_90', 'midland', 'Midland Basin'),
('argos_ent_pilot_180', 'midland', 'Midland Basin'),
('argos_ent_pilot_180', 'delaware', 'Delaware Basin'),
('argos_ent_pilot_270', 'midland', 'Midland Basin'),
('argos_ent_pilot_270', 'delaware', 'Delaware Basin'),
('argos_ent_pilot_270', 'eagle_ford', 'Eagle Ford Basin'),
('argos_ent_trial_01', 'midland', 'Midland Basin')
ON CONFLICT (tenant_id, basin_id) DO NOTHING;

-- Evidence real para FireBird con snapshot_hash
INSERT INTO evidence_sources (id, source_type, url, url_specific, is_primary, is_secondary, title, http_status, content_hash, notes) VALUES
('00000000-0000-0000-0000-000000000001', 'ENERGYNOW', 'https://energynow.com/2026/08/continental-resources-significantly-expands-permian-basin-position-with-acquisition-of-firebird-energy-ii/', true, false, true, 'Continental announces Firebird 54k acres', 200, 'sha256:placeholder_firebird_announcement', 'Fuente secundaria PR que cita acuerdo, no SEC 8-K primario'),
('00000000-0000-0000-0000-000000000002', 'REXTAG', 'https://rextag.com/blogs/blog/new-territories-new-opportunities-continental-s-acreage-addition-in-midland', true, false, true, '87 leases Oxy subsidiary -> Continental', 200, 'sha256:placeholder_rextag_87', 'Fuente secundaria que atribuye a registros RRC, no doc RRC primario'),
('00000000-0000-0000-0000-000000000003', 'DRILLINGEDGE', 'https://www.drillingedge.com/texas/ector-county', true, true, false, 'Continental production Ector County May 2026', 200, 'sha256:placeholder_drillingedge_ector', 'Snapshot necesario para 259 wells + 1,654,267 bbls oil'),
('00000000-0000-0000-0000-000000000004', 'RRC', 'https://www.rrc.texas.gov/oil-and-gas/applications-and-permits/injection-disposal/northern-culberson-reeves-seismic-response-area/', true, true, false, 'Northern Culberson-Reeves Seismic Response Area - 20k/30k bpd shallow disposal', 200, 'sha256:placeholder_rrc_20k30k', 'HECHO REGULATORIO CONTEXTUAL: aplica a Northern Culberson-Reeves, no universal Permian, no Upton/Midland directamente sin doc especifico')
ON CONFLICT (id) DO NOTHING;

-- CASE_001 FireBird REFORMULADO con estándar definitivo (ejemplo defendible)
INSERT INTO opportunities (id, basin_id, basin_name, tier_required, tier_min_price, county, operator, facts, inferences, hypothesis, unknown_data, opportunity_statement, what_collected, how_connected, what_you_had_not_seen, verification_notes, temporal_claim, temporal_evidence_id, bwpd_projected, verification_status, public_evidence_count, decision) VALUES
('CASE_001_MIDLAND_FIREBIRD_54K', 'midland', 'Midland Basin', 'pilot_90', 90000, 'Upton', 'Continental Resources',
'[
  {"fact_id":"f1","type":"HECHO","description":"Continental acordo adquirir FireBird: ~54k net acres, ~147k resource acres, ~32k boepd actuales, 307 development locations","evidence_id":"00000000-0000-0000-0000-000000000001","observed_at":"2026-08-20","is_secondary":true,"secondary_attribution":"EnergyNow PR, no SEC 8-K primario"},
  {"fact_id":"f2","type":"HECHO","description":"87 leases de subsidiaria Oxy transferidos a Continental Nov 2023 con 76k bbls + 123M cf first 3 months segun Rextag","evidence_id":"00000000-0000-0000-0000-000000000002","observed_at":"2023-11-01","is_secondary":true,"secondary_attribution":"Rextag reporta, atribuye a registros RRC, no doc RRC primario"},
  {"fact_id":"f3","type":"HECHO","description":"DrillingEdge registra 259 wells Continental en Ector County y ~1.6M bbls oil produccion May 2026","evidence_id":"00000000-0000-0000-0000-000000000003","observed_at":"2026-05-01","is_secondary":false},
  {"fact_id":"f4","type":"HECHO REGULATORIO CONTEXTUAL","description":"RRC establece limites 20k bpd y hasta 30k bpd con monitoreo sismico para shallow disposal wells dentro de Northern Culberson-Reeves Seismic Response Area, 4.5-9.08km de sismo >=M3.5","evidence_id":"00000000-0000-0000-0000-000000000004","observed_at":"2024-01-01","is_secondary":false}
]',
'[
  {"inference_id":"i1","type":"INFERENCIA","description":"WOR 4:1 x 32k boepd = 128k bwpd","formula":"bwpd = boepd * WOR","inputs":["f1"],"methodology":"WOR asumido industria Midland, no publicado por SEC/EnergyNow","status":"NO_VALIDADA","scenario_wor":[2,4,6],"result":128000,"unit":"bwpd","notes":"No usar como volumen real. 32k boepd es produccion actual activo, 307 locations es inventario desarrollo - no multiplicar directamente"},
  {"inference_id":"i2","type":"INFERENCIA","description":"30k bpd limit aplicado a Upton FireBird","formula":"bottleneck if projected > limit","inputs":["f1","f4"],"methodology":"Extiende limite Northern Culberson-Reeves a Upton sin doc especifico Upton","status":"NO_VALIDADA","result":30000,"unit":"bpd","notes":"f4 aplica a Northern Culberson-Reeves, no demuestra limite Upton/Midland. Requiere doc regulatorio especifico activo/zona"},
  {"inference_id":"i3","type":"INFERENCIA ECONOMICA","description":"$64k/dia ahorro recycling vs trucking","formula":"(trucking $1 - recycling $0.50) * bwpd","inputs":["i1"],"methodology":"$/bbl supuestos ARGOS, no de fuente","status":"NO_VALIDADA","result":64000,"unit":"$/dia","notes":"Depende de volumen real agua, costo actual, alternativa, capacidad, distancia, quien paga, incremental"}
]',
'La expansion de acreage + inventario desarrollo + presencia operativa existente podria generar presion sobre water handling si capacidad existente no crece al mismo ritmo. Requiere validacion con datos privados y doc regulatorio especifico.',
'["WOR real FireBird assets","produccion agua real 259 wells Ector","capacidad SWD North Upton 31.556451,-102.169482","utilizacion actual SWD","capacidad recycling Select","capacidad gathering","trucking requerido","costo actual $/bbl Upton","contratos existentes","infraestructura disponible","doc regulatorio especifico Upton/Midland aplicable"]',
'OPORTUNIDAD DE INVESTIGACION: Validar con Select Water / Continental si existe restriccion real de water handling asociada al desarrollo del activo FireBird. Si existe, determinar si cuello de botella corresponde a disposal, recycling, gathering, trucking, treatment, capacity o regulacion especifica. No afirmar bottleneck hasta validacion.',
'[{"evidence_id":"00000000-0000-0000-0000-000000000001","what":"Anuncio FireBird 54k acres, 147k resource, 32k boepd, 307 loc"},{"evidence_id":"00000000-0000-0000-0000-000000000002","what":"87 leases Oxy->Continental Nov 2023"},{"evidence_id":"00000000-0000-0000-0000-000000000003","what":"259 wells Ector 1.6M bbls May 2026"}]',
'Cruce f1+f2+f3 indica consolidacion Midland. Estimacion i1+i2 sugiere posible bottleneck si limites se confirman con doc RRC especifico Upton y WOR real. Pensamiento: mercado ve oil, ARGOS ve potencial presion agua si inferencias se validan.',
'Mercado vio adquisicion como acreage oil. Oportunidad no vista seria presion water handling si inferencias i1/i2 validadas con datos privados y doc especifico. Hoy no afirmable como bottleneck confirmado.',
'Verificar: f1 necesita SEC 8-K primario para cierre. f2 necesita RRC doc primario 87 leases, no solo Rextag secundario. f3 necesita snapshot hash DrillingEdge. f4 no aplica directamente a Upton sin doc especifico. 307 locations son inventario, 32k boepd es produccion actual - no multiplicar. WOR y $/dia son INFERENCIA_NO_VALIDADA.',
'Anunciado Aug 20 2026 segun EnergyNow, cierre previsto Sep 2026 segun fuente, sujeto a condiciones habituales, requiere confirmacion SEC 8-K cierre - fuente agosto no prueba cierre exacto',
'00000000-0000-0000-0000-000000000001',
'{"type":"INFERENCIA","status":"NO_VALIDADA","methodology":"WOR 4:1 asumido, escenario no volumen observado","depends_on_private":true,"scenarios":{"wor_2":64000,"wor_4":128000,"wor_6":192000}}',
'PARTIALLY_VERIFIED',
3,
'REFORMULAR'
)
ON CONFLICT (id) DO NOTHING;


-- V3 CORRECCION: FORCE RLS x5 - evita bypass por owner
ALTER TABLE tenants FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_basins FORCE ROW LEVEL SECURITY;
ALTER TABLE user_private_uploads FORCE ROW LEVEL SECURITY;
ALTER TABLE opportunity_recalculations FORCE ROW LEVEL SECURITY;
ALTER TABLE tenant_models FORCE ROW LEVEL SECURITY;

