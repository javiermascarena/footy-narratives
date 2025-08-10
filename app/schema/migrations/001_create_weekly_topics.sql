CREATE TABLE IF NOT EXISTS `weekly_topic`(
    `team_id` INTEGER NOT NULL, 
    `week_start` DATE NOT NULL, 
    `week_end` DATE NOT NULL,   
    `article_id` INTEGER NOT NULL, 
    `cluster_id` INTEGER,   
    `topic_id` INTEGER,
    `topic_probability` FLOAT,
    PRIMARY KEY (`team_id`, `week_start`, `week_end`, `article_id`),
    FOREIGN KEY (`team_id`, `article_id`) REFERENCES `article_teams`(`team_id`, `article_id`)
);