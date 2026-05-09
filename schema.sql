-- =============================================================
--  Card Arbitrage Bot — Supabase Schema
--  Supabase SQL Editor에서 한 번 실행하세요.
-- =============================================================

-- 1. PriceCharting 가격 캐시
CREATE TABLE IF NOT EXISTS pokemon_prices (
    product_id    TEXT PRIMARY KEY,
    product_name  TEXT NOT NULL,
    console_name  TEXT,
    psa_10_price  DECIMAL(10, 2),   -- USD
    cgc_10_price  DECIMAL(10, 2),   -- USD
    release_date  DATE,
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 기존 테이블에 컬럼 추가 (이미 생성된 경우)
ALTER TABLE pokemon_prices ADD COLUMN IF NOT EXISTS release_date DATE;

-- 2010년 이후 카드 조회 인덱스
CREATE INDEX IF NOT EXISTS idx_pokemon_prices_release
    ON pokemon_prices (release_date);

-- 이름 검색 인덱스 (ILIKE 쿼리 최적화)
CREATE INDEX IF NOT EXISTS idx_pokemon_prices_name
    ON pokemon_prices (product_name);

CREATE INDEX IF NOT EXISTS idx_pokemon_prices_console
    ON pokemon_prices (console_name);

-- 2. 아비트리지 발견 이력 (히스토리 추적)
CREATE TABLE IF NOT EXISTS arbitrage_log (
    id              BIGSERIAL PRIMARY KEY,
    ebay_item_id    TEXT,
    ebay_title      TEXT,
    ebay_price_usd  DECIMAL(10, 2),
    listing_type    TEXT,              -- 'auction' | 'buy_now'
    psa_10_price_usd DECIMAL(10, 2),
    best_tier       TEXT,              -- '벨류 플러스' | '벨류 맥스' | '레귤러'
    best_roi        DECIMAL(5, 1),
    is_estimated    BOOLEAN DEFAULT FALSE,
    ebay_url        TEXT,
    found_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_arbitrage_log_found_at
    ON arbitrage_log (found_at DESC);

-- =============================================================
--  RLS (Row Level Security) — 봇 전용 테이블이므로 비활성화
-- =============================================================
ALTER TABLE pokemon_prices  DISABLE ROW LEVEL SECURITY;
ALTER TABLE arbitrage_log   DISABLE ROW LEVEL SECURITY;

-- =============================================================
--  anon 권한 부여 (sb_publishable_ key 사용 시 필수)
-- =============================================================
GRANT SELECT, INSERT, UPDATE ON public.pokemon_prices TO anon;
GRANT SELECT, INSERT, UPDATE ON public.arbitrage_log  TO anon;
GRANT USAGE, SELECT ON SEQUENCE public.arbitrage_log_id_seq TO anon;
