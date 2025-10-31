my_folder/README.md
python -m uvicorn app.main:app --reload --port 8000  ||| paste this in backend terminal
python -m http.server 5500 ||| paste this in frontend terminal

IN CASE OF DB CORRUPTION prompt this in my SQL:

step 1

CREATE DATABASE piggery_db;
USE piggery_db;


-- ========================
-- USERS TABLE (must be created first)
-- ========================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(60) NOT NULL,
    username VARCHAR(30) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'sales', 'procurement', 'caretaker', 'client') NOT NULL,
    email VARCHAR(255),
    profile_picture VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status ENUM('active', 'inactive') DEFAULT 'active',
    updated_by INT,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ========================
-- LITTERS TABLE
-- ========================
CREATE TABLE litters (
    litter_id INT AUTO_INCREMENT PRIMARY KEY,
    litter_size TINYINT,
    birth_date DATE,
    sow_id VARCHAR(30),
    caretaker_id INT,
    FOREIGN KEY (caretaker_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ========================
-- PIGS TABLE
-- ========================
CREATE TABLE pigs (
    pigs_id INT AUTO_INCREMENT PRIMARY KEY,
    litter_id INT,
    sow_identifier VARCHAR(30),
    birth_date DATE,
    status ENUM('healthy', 'sick', 'deceased', 'for sale') DEFAULT 'healthy',
    notes TEXT,
    FOREIGN KEY (litter_id) REFERENCES litters(litter_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ========================
-- SUPPLIES TABLE
-- ========================
CREATE TABLE supplies (
    supply_id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(80) NOT NULL,
    category ENUM('feed', 'vitamin', 'vaccine', 'tool', 'other') NOT NULL,
    quantity INT NOT NULL,
    unit VARCHAR(10),
    updated_by INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ========================
-- PIG HEALTH RECORDS
-- ========================
CREATE TABLE pig_health_records (
    health_record_id INT AUTO_INCREMENT PRIMARY KEY,
    pigs_id INT,
    symptoms TEXT,
    diagnosis TEXT,
    treatment TEXT,
    mortality BOOLEAN DEFAULT FALSE,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    caretaker_id INT,
    FOREIGN KEY (pigs_id) REFERENCES pigs(pigs_id) ON DELETE CASCADE,
    FOREIGN KEY (caretaker_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ========================
-- FEEDING LOGS
-- ========================
CREATE TABLE feeding_logs (
    feeding_log_id INT AUTO_INCREMENT PRIMARY KEY,
    litter_id INT,
    caretaker_id INT,
    feed_type VARCHAR(50),
    quantity_kg DECIMAL(5,2),
    feeding_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (litter_id) REFERENCES litters(litter_id) ON DELETE CASCADE,
    FOREIGN KEY (caretaker_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ========================
-- BOOKINGS
-- ========================
CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT,
    type ENUM('pig', 'lechon') NOT NULL,
    item_details TEXT,
    status ENUM('pending', 'approved', 'declined') DEFAULT 'pending',
    booking_date DATE NOT NULL,
    approved_by INT,
    FOREIGN KEY (client_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ========================
-- SALES
-- ========================
CREATE TABLE sales (
    sale_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT,
    client_id INT,
    item_type ENUM('pig', 'lechon') NOT NULL,
    item_description TEXT,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_date DATE,
    recorded_by INT,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (recorded_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ========================
-- RESERVATION RECEIPTS
-- ========================
CREATE TABLE reservation_receipts (
    receipt_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT,
    receipt_data TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ========================
-- REPORTS
-- ========================
CREATE TABLE reports (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    report_type ENUM('sales', 'inventory', 'mortality', 'feed_consumption', 'profit_loss'),
    generated_by INT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data TEXT,
    FOREIGN KEY (generated_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ========================
-- FEEDBACK
-- ========================
CREATE TABLE feedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT,
    comment TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ========================
-- EXPENSES
-- ========================
CREATE TABLE expenses (
    expense_id INT AUTO_INCREMENT PRIMARY KEY,
    description VARCHAR(150),
    amount DECIMAL(10,2) NOT NULL,
    category ENUM('feed', 'vitamin', 'vaccine', 'tool', 'other'),
    date_spent DATE NOT NULL,
    recorded_by INT,
    FOREIGN KEY (recorded_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ========================
-- INQUIRY
-- ========================
CREATE TABLE inquiry (
    inquiry_id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT,
    subject VARCHAR(100),
    message TEXT,
    status ENUM('unread', 'read', 'responded') DEFAULT 'unread',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_by INT NULL,
    responded_at TIMESTAMP NULL,
    FOREIGN KEY (client_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (responded_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;


-- ============== available_pigs =================
CREATE TABLE IF NOT EXISTS `available_pigs` (
  `available_pigs_id` INT NOT NULL AUTO_INCREMENT,
  `pigs_id`           INT NOT NULL,
  `weight_kg`         DECIMAL(6,2) NOT NULL,
  `sale_type`         ENUM('market','lechon') NOT NULL,
  `status`            ENUM('available','reserved','sold','removed') NOT NULL DEFAULT 'available',
  `listed_by`         INT NULL,
  `notes`             VARCHAR(255) NULL,
  `created_at`        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`available_pigs_id`),
  KEY `idx_available_pigs_pig`       (`pigs_id`),
  KEY `idx_available_pigs_listed_by` (`listed_by`),
  CONSTRAINT `fk_available_pigs_pig`
    FOREIGN KEY (`pigs_id`) REFERENCES `pigs`(`pigs_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_available_pigs_user`
    FOREIGN KEY (`listed_by`) REFERENCES `users`(`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ============== booking_pigs (junction) =========
CREATE TABLE IF NOT EXISTS `booking_pigs` (
  `booking_id` INT NOT NULL,
  `pigs_id`    INT NOT NULL,
  PRIMARY KEY (`booking_id`, `pigs_id`),
  KEY `idx_booking_pigs_booking` (`booking_id`),
  KEY `idx_booking_pigs_pig`     (`pigs_id`),
  CONSTRAINT `fk_booking_pigs_booking`
    FOREIGN KEY (`booking_id`) REFERENCES `bookings`(`booking_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_booking_pigs_pig`
    FOREIGN KEY (`pigs_id`) REFERENCES `pigs`(`pigs_id`) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============== sows ============================
CREATE TABLE IF NOT EXISTS `sows` (
  `sow_id`         INT NOT NULL AUTO_INCREMENT,
  `sow_identifier` VARCHAR(100) NOT NULL UNIQUE,
  `status`         ENUM('pregnant','nonpregnant','miscarriage','gave_birth','nursing')
                   NOT NULL DEFAULT 'nonpregnant',
  `mating_date`    DATE NULL,
  `expected_birth` DATE NULL,
  `last_birth_date` DATE NULL,
  `caretaker_id`   INT NULL,
  PRIMARY KEY (`sow_id`),
  KEY `idx_sows_status`        (`status`),
  KEY `idx_sows_expected_birth`(`expected_birth`),
  KEY `idx_sows_caretaker`     (`caretaker_id`),
  CONSTRAINT `fk_sows_caretaker`
    FOREIGN KEY (`caretaker_id`) REFERENCES `users`(`user_id`)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS email_otp (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  email         VARCHAR(255)    NOT NULL,
  purpose       VARCHAR(64)     NOT NULL,              -- e.g. 'register'
  hashed_code     VARCHAR(255)    NOT NULL,              -- store HASH(OTP), never raw
  expires_at    DATETIME        NOT NULL,              -- 5-minute expiry from issuance
  attempts      TINYINT UNSIGNED NOT NULL DEFAULT 0,   -- up to 3 attempts
  last_sent_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 60s resend cooldown
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                 ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  UNIQUE KEY uq_email_purpose (email, purpose),
  KEY idx_email_otp_email (email),
  KEY idx_email_otp_expires (expires_at)
) ENGINE=InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- =========================
-- Table: email_verification
-- =========================
CREATE TABLE IF NOT EXISTS email_verification (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  jti         CHAR(36)        NOT NULL,               -- UUID v4 as string
  email       VARCHAR(255)    NOT NULL,
  purpose     VARCHAR(64)     NOT NULL,               -- e.g. 'register'
  issued_at   DATETIME        NOT NULL,
  expires_at  DATETIME        NOT NULL,               -- short TTL, e.g., 15 min
  used        BOOLEAN         NOT NULL DEFAULT 0,
  used_at     DATETIME        NULL,
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  UNIQUE KEY uq_email_verification_jti (jti),
  KEY idx_email_verif_email (email),
  KEY idx_email_verif_expires (expires_at)
) ENGINE=InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;



========== ADD THIS AFTER THE TOP CODE ========== 

step 2

ALTER TABLE email_otp
  ADD COLUMN IF NOT EXISTS superseded TINYINT(1) NOT NULL DEFAULT 0 AFTER attempts;

-- Make sure attempts has a default (optional hardening)
ALTER TABLE email_otp
  MODIFY attempts INT NOT NULL DEFAULT 0;

-- Optional: make timestamps behave nicely
ALTER TABLE email_otp
  MODIFY created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  MODIFY updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- Helpful indexes for lookups and expiry sweeps
CREATE INDEX IF NOT EXISTS idx_emailotp_lookup  ON email_otp (email, purpose, superseded);
CREATE INDEX IF NOT EXISTS idx_emailotp_expires ON email_otp (expires_at);

========== ADD THIS AFTER THE TOP CODE ========== 

step 3

ALTER TABLE `email_otp`
  ADD COLUMN `resend_after` DATETIME NULL DEFAULT NULL
    COMMENT 'Next allowed resend time (cooldown)'
    AFTER `attempts`;

========== ADD THIS AFTER THE TOP CODE ========== 

step 4

-- Email OTP timestamps as naive DATETIME
ALTER TABLE email_otp
  MODIFY expires_at   DATETIME NOT NULL,
  MODIFY resend_after DATETIME NULL,
  MODIFY last_sent_at DATETIME NULL,
  MODIFY created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  MODIFY updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- Email verification timestamps as naive DATETIME
ALTER TABLE email_verification
  MODIFY issued_at    DATETIME NOT NULL,
  MODIFY expires_at   DATETIME NOT NULL,
  MODIFY used_at      DATETIME NULL,
  MODIFY created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

========== ADD THIS AFTER THE TOP CODE ========== 

step 5

ALTER TABLE `inquiry`
ADD COLUMN `response` VARCHAR(1000) NULL AFTER `responded_at`;

========== INSTALL PIPS ================

step 6
Paste this after step 5 in your vscode backend terminal 

python -m pip install annotated-types==0.7.0 anyio==4.10.0 bcrypt==4.3.0 certifi==2025.10.5 cffi==2.0.0 charset-normalizer==3.4.4 click==8.2.1 colorama==0.4.6 cryptography==46.0.1 dnspython==2.8.0 ecdsa==0.19.1 email-validator==2.3.0 fastapi==0.116.1 greenlet==3.2.4 h11==0.16.0 httptools==0.6.4 idna==3.10 passlib==1.7.4 pyasn1==0.6.1 pycparser==2.23 pydantic==2.11.7 pydantic_core==2.33.2 pydantic-settings==2.11.0 PyMySQL==1.1.2 python-dotenv==1.1.1 python-jose==3.5.0 python-multipart==0.0.20 PyYAML==6.0.2 requests==2.32.5 resend==2.16.0 rsa==4.9.1 six==1.17.0 sniffio==1.3.1 SQLAlchemy==2.0.43 starlette==0.47.3 typing_extensions==4.15.0 typing-inspection==0.4.1 urllib3==2.5.0 uvicorn==0.35.0 watchfiles==1.1.0 websockets==15.0.1


============ .ENV ==================

step 7
create this folder under SWINETECH

DB_HOST=127.0.0.1
DB_PORT=3306       
DB_NAME=piggery_db
DB_USER=root
DB_PASSWORD=

ADMIN_SIGNUP_CODE=altremus
SECRET_KEY=altremus
ACCESS_TOKEN_EXPIRE_MINUTES=120

RESEND_API_KEY=re_FAfX3fgQ_EHcnAFrDLc4n8o9MkWdaR9Jw
APP_SECRET=super_long_random_secret  # for signing the short-lived token
OTP_CODE_LENGTH=6
OTP_EXP_MINUTES=5
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_ATTEMPTS=3

================= requirements.txt ================
ignore if you have this already, otherwise create the file 

annotated-types==0.7.0
anyio==4.10.0
click==8.2.1
colorama==0.4.6
fastapi==0.116.1
h11==0.16.0
httptools==0.6.4
idna==3.10
pydantic==2.11.7
pydantic_core==2.33.2
python-dotenv==1.1.1
PyYAML==6.0.2
sniffio==1.3.1
starlette==0.47.3
typing-inspection==0.4.1
typing_extensions==4.15.0
uvicorn==0.35.0
watchfiles==1.1.0
websockets==15.0.1

============ requirements.lock.txt =============
ignore if you have this already, otherwise create the file 

annotated-types==0.7.0
anyio==4.10.0
bcrypt==4.3.0
certifi==2025.10.5
cffi==2.0.0
charset-normalizer==3.4.4
click==8.2.1
colorama==0.4.6
cryptography==46.0.1
dnspython==2.8.0
ecdsa==0.19.1
email-validator==2.3.0
fastapi==0.116.1
greenlet==3.2.4
h11==0.16.0
httptools==0.6.4
idna==3.10
passlib==1.7.4
pyasn1==0.6.1
pycparser==2.23
pydantic==2.11.7
pydantic-settings==2.11.0
pydantic_core==2.33.2
PyMySQL==1.1.2
python-dotenv==1.1.1
python-jose==3.5.0
python-multipart==0.0.20
PyYAML==6.0.2
requests==2.32.5
resend==2.16.0
rsa==4.9.1
six==1.17.0
sniffio==1.3.1
SQLAlchemy==2.0.43
starlette==0.47.3
typing-inspection==0.4.1
typing_extensions==4.15.0
urllib3==2.5.0
uvicorn==0.35.0
watchfiles==1.1.0
websockets==15.0.1

======= Create the venv with 3.12 and install from your lockfile ============

install python 3.12 and check add to PATH when installing

ctrl + shift + p > select python 3.12 as interpreter
py -3.12 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.lock.txt

