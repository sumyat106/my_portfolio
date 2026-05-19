-- 1. Bio Table ဆောက်ခြင်း
CREATE TABLE IF NOT EXISTS bio (
    id INT AUTO_INCREMENT PRIMARY KEY,
    text TEXT NOT NULL,
    avatar VARCHAR(255) NULL,
    github_url VARCHAR(255) NULL,
    linkedin_url VARCHAR(255) NULL
);

-- 2. Skill Table ဆောက်ခြင်း
CREATE TABLE IF NOT EXISTS skill (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    display_order INT DEFAULT 0
);

-- 3. Project Table ဆောက်ခြင်း
CREATE TABLE IF NOT EXISTS project (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    image VARCHAR(255) NULL,
    live_url VARCHAR(255) NULL,
    github_url VARCHAR(255) NULL
);

-- 4. Timeline Table ဆောက်ခြင်း
CREATE TABLE IF NOT EXISTS timeline (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    organization VARCHAR(150) NOT NULL,
    type VARCHAR(50) NOT NULL,
    start_date VARCHAR(50) NOT NULL,
    end_date VARCHAR(50) NULL,
    description TEXT NULL
);

-- 5. Contact Message Table ဆောက်ခြင်း
CREATE TABLE IF NOT EXISTS contact_message (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);