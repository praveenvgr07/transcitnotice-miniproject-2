-- ============================================================
--  TransitNotice – MySQL Database Schema
--  Timezone: Asia/Kolkata (all app-side display)
--  Engine: InnoDB, Charset: utf8mb4
-- ============================================================

CREATE DATABASE IF NOT EXISTS transitnotice
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE transitnotice;

-- ── 1. users ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(120)  NOT NULL,
    email           VARCHAR(180)  NOT NULL UNIQUE,
    mobile          VARCHAR(15)   NOT NULL UNIQUE,
    password_hash   VARCHAR(255)  NOT NULL,
    role            ENUM('user','admin') NOT NULL DEFAULT 'user',
    is_email_verified  TINYINT(1) NOT NULL DEFAULT 0,
    is_mobile_verified TINYINT(1) NOT NULL DEFAULT 0,
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login      DATETIME     NULL,
    INDEX idx_users_email  (email),
    INDEX idx_users_mobile (mobile),
    INDEX idx_users_role   (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 2. user_verifications ────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_verifications (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED NOT NULL,
    token_type  ENUM('email_verify','mobile_otp','password_reset') NOT NULL,
    token       VARCHAR(128) NOT NULL,
    is_used     TINYINT(1)   NOT NULL DEFAULT 0,
    expires_at  DATETIME     NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_uv_user_type (user_id, token_type),
    INDEX idx_uv_token     (token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 3. transport_sources ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS transport_sources (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    provider        ENUM('MTC','TNSTC','SETC','CMRL') NOT NULL,
    source_name     VARCHAR(120) NOT NULL,
    source_url      VARCHAR(500) NOT NULL,
    source_type     ENUM('api','gtfs','website','static') NOT NULL DEFAULT 'website',
    is_enabled      TINYINT(1)  NOT NULL DEFAULT 0,
    is_authorized   TINYINT(1)  NOT NULL DEFAULT 0,
    auth_note       TEXT        NULL COMMENT 'Terms / ToS compliance note',
    last_fetched_at DATETIME    NULL,
    last_success_at DATETIME    NULL,
    fetch_status    ENUM('pending','success','failed','disabled') NOT NULL DEFAULT 'pending',
    created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ts_provider (provider),
    INDEX idx_ts_enabled  (is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 4. routes ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS routes (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_id       INT UNSIGNED NOT NULL,
    provider        ENUM('MTC','TNSTC','SETC','CMRL') NOT NULL,
    route_number    VARCHAR(30)  NOT NULL,
    route_name      VARCHAR(255) NOT NULL,
    origin          VARCHAR(180) NOT NULL,
    destination     VARCHAR(180) NOT NULL,
    service_type    VARCHAR(60)  NULL COMMENT 'Ordinary/Express/AC/Metro etc.',
    direction       ENUM('up','down','loop') NOT NULL DEFAULT 'up',
    distance_km     DECIMAL(8,2) NULL,
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    source_record_id VARCHAR(64) NULL COMMENT 'Provider own ID / GTFS route_id',
    raw_source_url  VARCHAR(500) NULL,
    fetched_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES transport_sources(id),
    UNIQUE KEY uq_route_provider_number (provider, route_number, direction),
    INDEX idx_routes_origin      (origin(60)),
    INDEX idx_routes_destination (destination(60)),
    INDEX idx_routes_provider    (provider),
    INDEX idx_routes_active      (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 5. stops ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stops (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    route_id        INT UNSIGNED NOT NULL,
    stop_sequence   INT UNSIGNED NOT NULL,
    stop_name       VARCHAR(180) NOT NULL,
    stop_code       VARCHAR(30)  NULL,
    latitude        DECIMAL(9,6) NULL,
    longitude       DECIMAL(9,6) NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE,
    INDEX idx_stops_route    (route_id),
    INDEX idx_stops_name     (stop_name(60))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 6. schedules ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schedules (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    route_id        INT UNSIGNED NOT NULL,
    trip_number     VARCHAR(30)  NULL,
    departure_time  TIME         NOT NULL,
    arrival_time    TIME         NULL,
    days_of_week    VARCHAR(20)  NOT NULL DEFAULT '1234567'
                                  COMMENT '1=Mon … 7=Sun, e.g. 12345=Weekdays',
    effective_from  DATE         NULL,
    effective_until DATE         NULL,
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    frequency_mins  INT          NULL COMMENT 'Metro headway in minutes',
    source_record_id VARCHAR(64) NULL,
    fetched_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE,
    INDEX idx_sched_route     (route_id),
    INDEX idx_sched_departure (departure_time),
    INDEX idx_sched_active    (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 7. announcements ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS announcements (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_id       INT UNSIGNED NULL,
    provider        ENUM('MTC','TNSTC','SETC','CMRL') NOT NULL,
    title           VARCHAR(300) NOT NULL,
    body            TEXT         NOT NULL,
    announcement_type ENUM('cancellation','diversion','delay','schedule_change',
                            'new_service','general') NOT NULL DEFAULT 'general',
    is_verified     TINYINT(1)   NOT NULL DEFAULT 0,
    severity        ENUM('info','warning','critical') NOT NULL DEFAULT 'info',
    effective_from  DATETIME     NULL,
    effective_until DATETIME     NULL,
    source_url      VARCHAR(500) NULL,
    published_at    DATETIME     NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES transport_sources(id),
    INDEX idx_ann_provider  (provider),
    INDEX idx_ann_type      (announcement_type),
    INDEX idx_ann_severity  (severity),
    INDEX idx_ann_effective (effective_from, effective_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 8. schedule_change_history ───────────────────────────────
CREATE TABLE IF NOT EXISTS schedule_change_history (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    route_id        INT UNSIGNED NOT NULL,
    schedule_id     INT UNSIGNED NULL,
    change_type     ENUM('departure_change','arrival_change','cancellation',
                         'diversion','stop_change','new_schedule','service_resumption') NOT NULL,
    old_value       TEXT         NULL,
    new_value       TEXT         NULL,
    change_reason   VARCHAR(300) NULL,
    is_confirmed    TINYINT(1)   NOT NULL DEFAULT 0,
    detected_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_from  DATETIME     NULL,
    effective_until DATETIME     NULL,
    announcement_id INT UNSIGNED NULL,
    FOREIGN KEY (route_id)        REFERENCES routes(id),
    FOREIGN KEY (schedule_id)     REFERENCES schedules(id),
    FOREIGN KEY (announcement_id) REFERENCES announcements(id),
    INDEX idx_sch_route    (route_id),
    INDEX idx_sch_type     (change_type),
    INDEX idx_sch_detected (detected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 9. bookings ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bookings (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             INT UNSIGNED NOT NULL,
    route_id            INT UNSIGNED NOT NULL,
    schedule_id         INT UNSIGNED NULL,
    booking_reference   VARCHAR(24)  NOT NULL UNIQUE,
    journey_date        DATE         NOT NULL,
    origin_stop         VARCHAR(180) NOT NULL,
    destination_stop    VARCHAR(180) NOT NULL,
    passenger_count     TINYINT UNSIGNED NOT NULL DEFAULT 1,
    total_fare          DECIMAL(10,2) NULL,
    currency            CHAR(3)      NOT NULL DEFAULT 'INR',
    booking_status      ENUM('pending','confirmed','cancelled',
                             'refund_requested','refunded') NOT NULL DEFAULT 'pending',
    payment_status      ENUM('pending','paid','failed','refunded') NOT NULL DEFAULT 'pending',
    payment_ref         VARCHAR(128) NULL,
    provider_booking_ref VARCHAR(128) NULL COMMENT 'Official provider booking ID',
    booking_channel     ENUM('platform','redirect') NOT NULL DEFAULT 'redirect',
    cancellation_reason TEXT         NULL,
    cancelled_at        DATETIME     NULL,
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)    REFERENCES users(id),
    FOREIGN KEY (route_id)   REFERENCES routes(id),
    FOREIGN KEY (schedule_id) REFERENCES schedules(id),
    INDEX idx_book_user    (user_id),
    INDEX idx_book_ref     (booking_reference),
    INDEX idx_book_date    (journey_date),
    INDEX idx_book_status  (booking_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 10. booking_passengers ───────────────────────────────────
CREATE TABLE IF NOT EXISTS booking_passengers (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    booking_id  INT UNSIGNED NOT NULL,
    name        VARCHAR(120) NOT NULL,
    age         TINYINT UNSIGNED NULL,
    gender      ENUM('male','female','other','unspecified') NOT NULL DEFAULT 'unspecified',
    id_type     VARCHAR(30)  NULL COMMENT 'Aadhaar/PAN/Passport',
    id_number   VARCHAR(30)  NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    INDEX idx_bp_booking (booking_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 11. notification_preferences ─────────────────────────────
CREATE TABLE IF NOT EXISTS notification_preferences (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL UNIQUE,
    email_enabled   TINYINT(1)  NOT NULL DEFAULT 1,
    sms_enabled     TINYINT(1)  NOT NULL DEFAULT 1,
    booking_alerts  TINYINT(1)  NOT NULL DEFAULT 1,
    schedule_alerts TINYINT(1)  NOT NULL DEFAULT 1,
    promo_alerts    TINYINT(1)  NOT NULL DEFAULT 0,
    updated_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 12. notifications ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    booking_id      INT UNSIGNED NULL,
    change_id       INT UNSIGNED NULL,
    notification_type ENUM('booking_confirm','booking_cancel','schedule_change',
                            'delay','cancellation','general') NOT NULL,
    title           VARCHAR(300) NOT NULL,
    message         TEXT         NOT NULL,
    is_read         TINYINT(1)   NOT NULL DEFAULT 0,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)    REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE SET NULL,
    FOREIGN KEY (change_id)  REFERENCES schedule_change_history(id) ON DELETE SET NULL,
    INDEX idx_notif_user    (user_id),
    INDEX idx_notif_read    (is_read),
    INDEX idx_notif_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 13. notification_delivery_logs ───────────────────────────
CREATE TABLE IF NOT EXISTS notification_delivery_logs (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    notification_id INT UNSIGNED NOT NULL,
    channel         ENUM('email','sms') NOT NULL,
    recipient       VARCHAR(200) NOT NULL,
    status          ENUM('queued','sent','delivered','failed','bounced') NOT NULL DEFAULT 'queued',
    provider_ref    VARCHAR(128) NULL,
    error_message   TEXT         NULL,
    attempt_count   TINYINT UNSIGNED NOT NULL DEFAULT 0,
    last_attempt_at DATETIME     NULL,
    delivered_at    DATETIME     NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notification_id) REFERENCES notifications(id) ON DELETE CASCADE,
    INDEX idx_ndl_notification (notification_id),
    INDEX idx_ndl_status       (status),
    INDEX idx_ndl_channel      (channel)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 14. scraper_logs ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scraper_logs (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_id       INT UNSIGNED NULL,
    provider        ENUM('MTC','TNSTC','SETC','CMRL') NOT NULL,
    job_name        VARCHAR(80)  NOT NULL,
    status          ENUM('started','success','partial','failed') NOT NULL DEFAULT 'started',
    records_fetched INT          NOT NULL DEFAULT 0,
    records_inserted INT         NOT NULL DEFAULT 0,
    records_updated INT          NOT NULL DEFAULT 0,
    changes_detected INT         NOT NULL DEFAULT 0,
    error_message   TEXT         NULL,
    duration_ms     INT          NULL,
    started_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME     NULL,
    FOREIGN KEY (source_id) REFERENCES transport_sources(id),
    INDEX idx_sl_provider  (provider),
    INDEX idx_sl_status    (status),
    INDEX idx_sl_started   (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 15. saved_routes ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS saved_routes (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED NOT NULL,
    route_id    INT UNSIGNED NULL,
    label       VARCHAR(80)  NULL COMMENT 'User-given nickname',
    origin      VARCHAR(180) NOT NULL,
    destination VARCHAR(180) NOT NULL,
    provider    ENUM('MTC','TNSTC','SETC','CMRL') NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)  REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE SET NULL,
    UNIQUE KEY uq_saved_user_route (user_id, route_id),
    INDEX idx_sr_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Seed: transport_sources ───────────────────────────────────
-- Authorization status is false by default until confirmed.
INSERT INTO transport_sources
  (provider, source_name, source_url, source_type, is_enabled, is_authorized, auth_note)
VALUES
  ('MTC',   'MTC Chennai Official Website',
   'https://mtcbus.tn.gov.in',
   'website', 0, 0,
   'Pending authorization review – robots.txt and ToS must be verified before enabling.'),

  ('TNSTC', 'TNSTC Official Website',
   'https://www.tnstc.in',
   'website', 0, 0,
   'Pending authorization review – robots.txt and ToS must be verified before enabling.'),

  ('SETC',  'SETC Official Website',
   'https://www.setc.tn.gov.in',
   'website', 0, 0,
   'Pending authorization review – robots.txt and ToS must be verified before enabling.'),

  ('CMRL',  'CMRL GTFS Open Data Feed',
   'https://www.chennaimetrorail.org',
   'gtfs', 0, 0,
   'GTFS feed availability must be confirmed with CMRL. Enable once a public feed URL is obtained.');
