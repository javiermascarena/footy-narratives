CREATE DATABASE IF NOT EXISTS `footy_narratives`;
USE `footy_narratives`;

CREATE TABLE IF NOT EXISTS `outlets` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL UNIQUE,
    `url` VARCHAR(512) 
);

CREATE TABLE IF NOT EXISTS `authors` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS `teams` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS `articles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,    
    `link` VARCHAR(512) NOT NULL UNIQUE,
    `title` TEXT,
    `summary` TEXT,
    `publication_date` DATETIME,
    `outlet_id` INT,
    `author_id` INT NULL,    
    `full_text` LONGTEXT,
    FOREIGN KEY (`outlet_id`) REFERENCES `outlets`(`id`),
    FOREIGN KEY (`author_id`) REFERENCES `authors`(`id`) 
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS `article_teams` (
    `article_id` INT,
    `team_id` INT,
    PRIMARY KEY (`article_id`, `team_id`),
    FOREIGN KEY (`article_id`) REFERENCES `articles`(`id`),
    FOREIGN KEY (`team_id`) REFERENCES `teams`(`id`)
);
