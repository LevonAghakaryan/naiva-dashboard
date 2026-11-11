-- Creatorly — MySQL 8 schema (v1.2)
-- v1.1: + audience_online_hours, + ai_usage, + ai_messages.blocks
-- v1.2: account_daily_stats + follows/unfollows/engagement columns, + account_period_stats,
--       post_stats + reposts/follows (db/migrations/2026-11-11_instagram_v2.sql)
-- utf8mb4 for Armenian text and emoji in DMs/captions

SET NAMES utf8mb4;
CREATE DATABASE IF NOT EXISTS creatorly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE creatorly;

-- ========== 1. Users & Instagram accounts ==========

CREATE TABLE users (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  name          VARCHAR(120) NOT NULL,
  plan          ENUM('free','pro','business') NOT NULL DEFAULT 'free',
  timezone      VARCHAR(64) NOT NULL DEFAULT 'Asia/Yerevan',
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE ig_accounts (
  id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id          BIGINT UNSIGNED NOT NULL,
  ig_user_id       VARCHAR(64) NOT NULL UNIQUE,
  username         VARCHAR(64) NOT NULL,
  profile_pic_url  VARCHAR(1024),
  access_token     TEXT NOT NULL,            -- store encrypted (app-level)
  token_expires_at DATETIME,
  followers_count  INT UNSIGNED NOT NULL DEFAULT 0,
  media_count      INT UNSIGNED NOT NULL DEFAULT 0,
  last_synced_at   DATETIME,
  connected_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_ig_user (user_id)
) ENGINE=InnoDB;

-- ========== 2. Instagram analytics ==========
-- Instagram keeps account metrics only ~90 days, so we store a daily snapshot.

CREATE TABLE account_daily_stats (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ig_account_id BIGINT UNSIGNED NOT NULL,
  day           DATE NOT NULL,
  followers     INT UNSIGNED NOT NULL DEFAULT 0,   -- level, end of day
  new_follows   INT UNSIGNED NOT NULL DEFAULT 0,   -- flows for the day ↓
  unfollows     INT UNSIGNED NOT NULL DEFAULT 0,
  reach         INT UNSIGNED NOT NULL DEFAULT 0,   -- unique accounts that day
  non_follower_reach INT UNSIGNED NOT NULL DEFAULT 0,
  views         INT UNSIGNED NOT NULL DEFAULT 0,
  accounts_engaged INT UNSIGNED NOT NULL DEFAULT 0, -- unique accounts that day
  interactions  INT UNSIGNED NOT NULL DEFAULT 0,
  likes         INT UNSIGNED NOT NULL DEFAULT 0,
  comments      INT UNSIGNED NOT NULL DEFAULT 0,
  saves         INT UNSIGNED NOT NULL DEFAULT 0,
  shares        INT UNSIGNED NOT NULL DEFAULT 0,
  reposts       INT UNSIGNED NOT NULL DEFAULT 0,
  profile_views INT UNSIGNED NOT NULL DEFAULT 0,
  link_taps     INT UNSIGNED NOT NULL DEFAULT 0,
  FOREIGN KEY (ig_account_id) REFERENCES ig_accounts(id) ON DELETE CASCADE,
  UNIQUE KEY uq_account_day (ig_account_id, day)
) ENGINE=InnoDB;

-- Reach / accounts engaged are unique accounts: a period total can't be summed from days,
-- so it is stored per period exactly as the API returns it (fallback: daily sum).
CREATE TABLE account_period_stats (
  id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ig_account_id      BIGINT UNSIGNED NOT NULL,
  end_day            DATE NOT NULL,              -- last day of the period
  days               TINYINT UNSIGNED NOT NULL,  -- 7 / 30 / 90
  reach              INT UNSIGNED NOT NULL DEFAULT 0,
  non_follower_reach INT UNSIGNED NOT NULL DEFAULT 0,
  accounts_engaged   INT UNSIGNED NOT NULL DEFAULT 0,
  FOREIGN KEY (ig_account_id) REFERENCES ig_accounts(id) ON DELETE CASCADE,
  UNIQUE KEY uq_account_period (ig_account_id, end_day, days)
) ENGINE=InnoDB;

CREATE TABLE posts (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ig_account_id BIGINT UNSIGNED NOT NULL,
  ig_media_id   VARCHAR(64) NOT NULL UNIQUE,
  type          ENUM('post','carousel','reels','story') NOT NULL,
  caption       TEXT,
  permalink     VARCHAR(1024),
  thumbnail_url VARCHAR(1024),
  posted_at     DATETIME NOT NULL,
  FOREIGN KEY (ig_account_id) REFERENCES ig_accounts(id) ON DELETE CASCADE,
  INDEX idx_posts_account_time (ig_account_id, posted_at)
) ENGINE=InnoDB;

-- Snapshots over time (stories must be captured within 24h)
CREATE TABLE post_stats (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  post_id     BIGINT UNSIGNED NOT NULL,
  captured_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  views       INT UNSIGNED NOT NULL DEFAULT 0,
  reach       INT UNSIGNED NOT NULL DEFAULT 0,
  likes       INT UNSIGNED NOT NULL DEFAULT 0,
  comments    INT UNSIGNED NOT NULL DEFAULT 0,
  saves       INT UNSIGNED NOT NULL DEFAULT 0,
  shares      INT UNSIGNED NOT NULL DEFAULT 0,
  reposts     INT UNSIGNED NOT NULL DEFAULT 0,
  follows     INT UNSIGNED NOT NULL DEFAULT 0,
  FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
  INDEX idx_post_stats (post_id, captured_at)
) ENGINE=InnoDB;

CREATE TABLE audience_stats (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ig_account_id BIGINT UNSIGNED NOT NULL,
  day           DATE NOT NULL,
  breakdown     ENUM('age','gender','city','country') NOT NULL,
  label         VARCHAR(100) NOT NULL,     -- '25-34', 'F', 'Yerevan'
  value         INT UNSIGNED NOT NULL,
  FOREIGN KEY (ig_account_id) REFERENCES ig_accounts(id) ON DELETE CASCADE,
  UNIQUE KEY uq_audience (ig_account_id, day, breakdown, label)
) ENGINE=InnoDB;

-- "When is the audience online" heatmap: weekday x hour
CREATE TABLE audience_online_hours (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ig_account_id BIGINT UNSIGNED NOT NULL,
  day           TINYINT UNSIGNED NOT NULL,   -- 0 = Monday … 6 = Sunday
  hour          TINYINT UNSIGNED NOT NULL,   -- 0 … 23 (account timezone)
  value         INT UNSIGNED NOT NULL DEFAULT 0,  -- online followers
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (ig_account_id) REFERENCES ig_accounts(id) ON DELETE CASCADE,
  UNIQUE KEY uq_online_hour (ig_account_id, day, hour),
  CHECK (day <= 6),
  CHECK (hour <= 23)
) ENGINE=InnoDB;

-- ========== 3. Inbox & bots ==========

CREATE TABLE contacts (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ig_account_id BIGINT UNSIGNED NOT NULL,
  ig_scoped_id  VARCHAR(64) NOT NULL,       -- Instagram-scoped user id
  username      VARCHAR(64),
  name          VARCHAR(120),
  type          ENUM('person','brand') NOT NULL DEFAULT 'person',
  notes         TEXT,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (ig_account_id) REFERENCES ig_accounts(id) ON DELETE CASCADE,
  UNIQUE KEY uq_contact (ig_account_id, ig_scoped_id)
) ENGINE=InnoDB;

CREATE TABLE conversations (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ig_account_id     BIGINT UNSIGNED NOT NULL,
  contact_id        BIGINT UNSIGNED NOT NULL,
  ig_thread_id      VARCHAR(128),
  category          ENUM('collab','question','feedback','other') NOT NULL DEFAULT 'other',
  status            ENUM('open','waiting','closed') NOT NULL DEFAULT 'open',
  is_important      BOOLEAN NOT NULL DEFAULT FALSE,
  unread_count      INT UNSIGNED NOT NULL DEFAULT 0,
  last_message_at   DATETIME,
  window_expires_at DATETIME,               -- 24h messaging window
  FOREIGN KEY (ig_account_id) REFERENCES ig_accounts(id) ON DELETE CASCADE,
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
  INDEX idx_conv_list (ig_account_id, status, last_message_at)
) ENGINE=InnoDB;

CREATE TABLE messages (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  conversation_id BIGINT UNSIGNED NOT NULL,
  ig_message_id   VARCHAR(128) UNIQUE,
  direction       ENUM('in','out') NOT NULL,
  sender          ENUM('contact','user','bot','ai') NOT NULL,
  body            TEXT,
  attachment_url  VARCHAR(1024),
  sent_at         DATETIME NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
  INDEX idx_msg_conv (conversation_id, sent_at)
) ENGINE=InnoDB;

CREATE TABLE bot_rules (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ig_account_id BIGINT UNSIGNED NOT NULL,
  name          VARCHAR(120) NOT NULL,
  trigger_type  ENUM('comment_keyword','dm_keyword','story_reply','ai_fallback') NOT NULL,
  keywords      JSON,                       -- ["գին","price"]
  scope         ENUM('all','reels','posts','stories','dm') NOT NULL DEFAULT 'all',
  action_type   ENUM('send_dm','reply','send_link','handoff') NOT NULL,
  response_text TEXT,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  runs_count    INT UNSIGNED NOT NULL DEFAULT 0,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (ig_account_id) REFERENCES ig_accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE bot_runs (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  rule_id         BIGINT UNSIGNED NOT NULL,
  conversation_id BIGINT UNSIGNED,
  status          ENUM('sent','queued','failed','skipped_window') NOT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (rule_id) REFERENCES bot_rules(id) ON DELETE CASCADE,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
  INDEX idx_runs_time (rule_id, created_at)   -- also used for the 200/hour limit
) ENGINE=InnoDB;

-- ========== 4. Finance ==========

CREATE TABLE categories (
  id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED,                   -- NULL = default category for everyone
  name    VARCHAR(80) NOT NULL,
  type    ENUM('income','expense') NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE deals (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id      BIGINT UNSIGNED NOT NULL,
  contact_id   BIGINT UNSIGNED,
  brand_name   VARCHAR(120) NOT NULL,
  deliverables VARCHAR(255),                 -- '2 Reels + 3 stories'
  amount       DECIMAL(14,2) NOT NULL DEFAULT 0,
  currency     CHAR(3) NOT NULL DEFAULT 'AMD',
  stage        ENUM('negotiation','contract','in_progress','paid','lost') NOT NULL DEFAULT 'negotiation',
  due_date     DATE,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
  INDEX idx_deals_stage (user_id, stage)
) ENGINE=InnoDB;

CREATE TABLE transactions (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     BIGINT UNSIGNED NOT NULL,
  deal_id     BIGINT UNSIGNED,
  category_id BIGINT UNSIGNED,
  type        ENUM('income','expense') NOT NULL,
  amount      DECIMAL(14,2) NOT NULL,
  currency    CHAR(3) NOT NULL DEFAULT 'AMD',
  description VARCHAR(255),
  status      ENUM('paid','pending') NOT NULL DEFAULT 'paid',
  source      ENUM('manual','csv','receipt_scan') NOT NULL DEFAULT 'manual',
  receipt_url VARCHAR(1024),
  occurred_at DATE NOT NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE SET NULL,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
  INDEX idx_tx_user_date (user_id, occurred_at)
) ENGINE=InnoDB;

-- ========== 5. Competitors (public data only) ==========

CREATE TABLE competitors (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id    BIGINT UNSIGNED NOT NULL,
  username   VARCHAR(64) NOT NULL,
  ig_user_id VARCHAR(64),
  name       VARCHAR(120),
  added_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uq_competitor (user_id, username)
) ENGINE=InnoDB;

CREATE TABLE competitor_daily_stats (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  competitor_id BIGINT UNSIGNED NOT NULL,
  day           DATE NOT NULL,
  followers     INT UNSIGNED NOT NULL,
  media_count   INT UNSIGNED NOT NULL,
  FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE CASCADE,
  UNIQUE KEY uq_comp_day (competitor_id, day)
) ENGINE=InnoDB;

CREATE TABLE competitor_posts (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  competitor_id BIGINT UNSIGNED NOT NULL,
  ig_media_id   VARCHAR(64) NOT NULL UNIQUE,
  type          ENUM('post','carousel','reels') NOT NULL,
  caption       TEXT,
  permalink     VARCHAR(1024),
  likes         INT UNSIGNED NOT NULL DEFAULT 0,
  comments      INT UNSIGNED NOT NULL DEFAULT 0,
  posted_at     DATETIME NOT NULL,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE CASCADE,
  INDEX idx_comp_posts (competitor_id, posted_at)
) ENGINE=InnoDB;

-- ========== 6. AI assistant ==========

CREATE TABLE ai_chats (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id    BIGINT UNSIGNED NOT NULL,
  title      VARCHAR(200),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE ai_messages (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  chat_id    BIGINT UNSIGNED NOT NULL,
  role       ENUM('user','assistant') NOT NULL,
  content    MEDIUMTEXT NOT NULL,           -- plain text (also used as context for the model)
  blocks     JSON,                          -- structured reply: KPI cards, lists, action buttons
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (chat_id) REFERENCES ai_chats(id) ON DELETE CASCADE,
  INDEX idx_ai_msg (chat_id, created_at)
) ENGINE=InnoDB;

-- Daily AI summaries shown on Overview / Finance / Competitors pages
CREATE TABLE ai_insights (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id    BIGINT UNSIGNED NOT NULL,
  section    ENUM('overview','analytics','finance','competitors','inbox') NOT NULL,
  body       TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_insights (user_id, section, created_at)
) ENGINE=InnoDB;

-- Every Claude API call: cost tracking and per-plan limits
CREATE TABLE ai_usage (
  id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id            BIGINT UNSIGNED NOT NULL,
  feature            ENUM('dm_classify','dm_reply','bot_fallback','receipt_scan','assistant','daily_summary') NOT NULL,
  model              VARCHAR(64) NOT NULL,      -- 'claude-haiku-5-5', 'claude-sonnet-5-5'
  input_tokens       INT UNSIGNED NOT NULL DEFAULT 0,
  output_tokens      INT UNSIGNED NOT NULL DEFAULT 0,
  cache_read_tokens  INT UNSIGNED NOT NULL DEFAULT 0,
  cache_write_tokens INT UNSIGNED NOT NULL DEFAULT 0,
  is_batch           BOOLEAN NOT NULL DEFAULT FALSE,
  cost_usd           DECIMAL(12,6) NOT NULL DEFAULT 0,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_ai_usage (user_id, created_at)
) ENGINE=InnoDB;

-- Default categories
INSERT INTO categories (user_id, name, type) VALUES
 (NULL,'Համագործակցություն','income'),(NULL,'Գովազդ','income'),(NULL,'Affiliate','income'),(NULL,'Այլ եկամուտ','income'),
 (NULL,'Տեխնիկա','expense'),(NULL,'Աշխատավարձ','expense'),(NULL,'Ծրագրեր','expense'),(NULL,'Տրանսպորտ','expense'),(NULL,'Այլ ծախս','expense');
