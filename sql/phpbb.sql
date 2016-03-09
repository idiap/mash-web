-- Prevent the users to change their account informations via the forum
UPDATE phpbb_modules SET module_display = '0' WHERE module_langname = 'UCP_PROFILE_REG_DETAILS';


-- Add a 'Project members' group
INSERT INTO `phpbb_groups` (`group_id`, `group_type`, `group_founder_manage`, `group_name`, `group_desc`, `group_desc_bitfield`, `group_desc_options`, `group_desc_uid`, `group_display`, `group_avatar`, `group_avatar_type`, `group_avatar_width`, `group_avatar_height`, `group_rank`, `group_colour`, `group_sig_chars`, `group_receive_pm`, `group_message_limit`, `group_max_recipients`, `group_legend`) VALUES
(7, 1, 0, 'Project members', '', '', 7, '', 0, '', 0, 0, 0, 6, 'CC3300', 0, 1, 0, 0, 1);


-- Add some user ranks
INSERT INTO `phpbb_ranks` (`rank_id`, `rank_title`, `rank_min`, `rank_special`, `rank_image`) VALUES
(2, 'Contributor', 0, 0, ''),
(3, 'Core team', 0, 1, ''),
(4, 'Project Leader', 0, 1, ''),
(5, 'The System', 0, 1, '');


-- Make the 'Contributor' rank the default for the new users
ALTER TABLE `phpbb_users` CHANGE `user_rank` `user_rank` MEDIUMINT( 8 ) UNSIGNED NOT NULL DEFAULT '2';


-- Install and use the MASH style
INSERT INTO `phpbb_styles` (`style_id`, `style_name`, `style_copyright`, `style_active`, `template_id`, `theme_id`, `imageset_id`) VALUES
(2, 'mash', '&copy; MASH Project', 1, 2, 2, 2);

INSERT INTO `phpbb_styles_imageset` (`imageset_id`, `imageset_name`, `imageset_copyright`, `imageset_path`) VALUES
(2, 'mash', '&copy; MASH Project', 'mash');

INSERT INTO `phpbb_styles_imageset_data` (`image_name`, `image_filename`, `image_lang`, `image_height`, `image_width`, `imageset_id`)
SELECT `image_name`, `image_filename`, `image_lang`, `image_height`, `image_width`, 2 FROM `phpbb_styles_imageset_data` WHERE `imageset_id`=1;

INSERT INTO `phpbb_styles_template` (`template_id`, `template_name`, `template_copyright`, `template_path`, `bbcode_bitfield`, `template_storedb`, `template_inherits_id`, `template_inherit_path`) VALUES
(2, 'mash', '&copy; MASH Project', 'mash', 'kNg=', 0, 1, 'prosilver');

INSERT INTO `phpbb_styles_theme` (`theme_id`, `theme_name`, `theme_copyright`, `theme_path`, `theme_storedb`, `theme_mtime`, `theme_data`) VALUES
(2, 'mash', '&copy; MASH Project', 'mash', 0, 0, '');


-- Change some settings
UPDATE `phpbb_config` SET `config_value` = '1' WHERE `config_name` = 'allow_avatar_upload';
UPDATE `phpbb_config` SET `config_value` = 'django' WHERE `config_name` = 'auth_method';
UPDATE `phpbb_config` SET `config_value` = '1' WHERE `config_name` = 'board_dst';
UPDATE `phpbb_config` SET `config_value` = '1' WHERE `config_name` = 'board_timezone';
UPDATE `phpbb_config` SET `config_value` = '2' WHERE `config_name` = 'default_style';
UPDATE `phpbb_config` SET `config_value` = '1' WHERE `config_name` = 'override_user_style';
UPDATE `phpbb_config` SET `config_value` = 'Forum of the MASH project' WHERE `config_name` = 'site_desc';
UPDATE `phpbb_config` SET `config_value` = 'MASH forum' WHERE `config_name` = 'sitename';
UPDATE `phpbb_config` SET `config_value` = '61440' WHERE `config_name` = 'avatar_filesize';
UPDATE `phpbb_config` SET `config_value` = '0' WHERE `config_name` = 'allow_birthdays';


-- Delete the default forums, topics, posts, and their permissions
TRUNCATE TABLE `phpbb_forums`;
TRUNCATE TABLE `phpbb_topics`;
TRUNCATE TABLE `phpbb_posts`;

DELETE FROM `phpbb_acl_groups` WHERE `forum_id`!=0;

UPDATE `phpbb_users` SET `user_posts`= '0';


-- Create the forums
INSERT INTO `phpbb_forums` (`forum_id`, `parent_id`, `left_id`, `right_id`, `forum_parents`, `forum_name`, `forum_desc`, `forum_desc_bitfield`, `forum_desc_options`, `forum_desc_uid`, `forum_link`, `forum_password`, `forum_style`, `forum_image`, `forum_rules`, `forum_rules_link`, `forum_rules_bitfield`, `forum_rules_options`, `forum_rules_uid`, `forum_topics_per_page`, `forum_type`, `forum_status`, `forum_posts`, `forum_topics`, `forum_topics_real`, `forum_last_post_id`, `forum_last_poster_id`, `forum_last_post_subject`, `forum_last_post_time`, `forum_last_poster_name`, `forum_last_poster_colour`, `forum_flags`, `display_subforum_list`, `display_on_index`, `enable_indexing`, `enable_icons`, `enable_prune`, `prune_next`, `prune_days`, `prune_viewed`, `prune_freq`) VALUES
(1, 0, 1, 8, '', 'MASH', '', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 0, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(2, 1, 2, 3, '', 'General Discussion', 'Anything and everything that''s related to MASH or the wider machine learning field that doesn''t fit into the other forums', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 1, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(3, 1, 4, 5, '', 'Help', 'Problems with the website', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 1, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(4, 1, 6, 7, '', 'Feature Requests', 'Propose and discuss new features', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 1, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(5, 0, 9, 16, '', 'MASH SDK / Heuristics development', '', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 0, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(6, 5, 10, 11, '', 'Heuristics development', 'Queries about the development of a new heuristic', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 1, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(7, 5, 12, 13, '', 'Help', 'Problems building or using the SDK', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 1, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(8, 5, 14, 15, '', 'Back to Basics', 'Get answers to all your basic programming questions. No MASH questions, please!', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 1, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(9, 0, 17, 22, '', 'Heuristics and experiments', '', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 0, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(10, 9, 18, 19, '', 'Heuristics', 'Official topics of the heuristics. To create an official topic about a heuristic, use the ''Discuss It'' button on the page of this heuristic', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 1, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(11, 9, 20, 21, '', 'Experiments', 'Official topics of the experiments. To create an official topic about an experiment, use the ''Discuss It'' button on the page of this experiment', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 1, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(12, 0, 23, 26, '', 'Project development', 'Only accessible to project members', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 0, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1),
(13, 12, 24, 25, '', 'Development', 'Only accessible to project members', '', 7, '', '', '', 0, '', '', '', '', 7, '', 0, 1, 0, 0, 0, 0, 0, 0, '', 0, '', '', 32, 1, 0, 1, 0, 0, 0, 7, 7, 1);


-- Set the permissions of the forums: group GUESTS, Read only
INSERT INTO `phpbb_acl_groups` (`group_id`, `forum_id`, `auth_option_id`, `auth_role_id`, `auth_setting`)
SELECT `phpbb_groups`.`group_id`, `phpbb_forums`.`forum_id`, 0, `phpbb_acl_roles`.`role_id`, 0
FROM `phpbb_groups`, `phpbb_forums`, `phpbb_acl_roles`
WHERE `phpbb_groups`.`group_name`='GUESTS'
AND `phpbb_acl_roles`.`role_name`='ROLE_FORUM_READONLY'
AND (
    `phpbb_forums`.`forum_name`='MASH'
    OR `phpbb_forums`.`forum_name`='General Discussion'
    OR `phpbb_forums`.`forum_name`='Help'
    OR `phpbb_forums`.`forum_name`='Feature Requests'
    OR `phpbb_forums`.`forum_name`='MASH SDK / Heuristics development'
    OR `phpbb_forums`.`forum_name`='Heuristics development'
    OR `phpbb_forums`.`forum_name`='Back to Basics'
);


-- Set the permissions of the forums: group REGISTERED, Standard Access
INSERT INTO `phpbb_acl_groups` (`group_id`, `forum_id`, `auth_option_id`, `auth_role_id`, `auth_setting`)
SELECT `phpbb_groups`.`group_id`, `phpbb_forums`.`forum_id`, 0, `phpbb_acl_roles`.`role_id`, 0
FROM `phpbb_groups`, `phpbb_forums`, `phpbb_acl_roles`
WHERE `phpbb_groups`.`group_name`='REGISTERED'
AND `phpbb_acl_roles`.`role_name`='ROLE_FORUM_STANDARD'
AND (
    `phpbb_forums`.`forum_name`='MASH'
    OR `phpbb_forums`.`forum_name`='Help'
    OR `phpbb_forums`.`forum_name`='MASH SDK / Heuristics development'
    OR `phpbb_forums`.`forum_name`='Heuristics development'
    OR `phpbb_forums`.`forum_name`='Back to Basics'
);


-- Set the permissions of the forums: group REGISTERED, Standard Access + Polls
INSERT INTO `phpbb_acl_groups` (`group_id`, `forum_id`, `auth_option_id`, `auth_role_id`, `auth_setting`)
SELECT `phpbb_groups`.`group_id`, `phpbb_forums`.`forum_id`, 0, `phpbb_acl_roles`.`role_id`, 0
FROM `phpbb_groups`, `phpbb_forums`, `phpbb_acl_roles`
WHERE `phpbb_groups`.`group_name`='REGISTERED'
AND `phpbb_acl_roles`.`role_name`='ROLE_FORUM_POLLS'
AND (
    `phpbb_forums`.`forum_name`='General Discussion'
    OR `phpbb_forums`.`forum_name`='Feature Requests'
);


-- Set the permissions of the forums: group GLOBAL_MODERATORS, Full Access
INSERT INTO `phpbb_acl_groups` (`group_id`, `forum_id`, `auth_option_id`, `auth_role_id`, `auth_setting`)
SELECT `phpbb_groups`.`group_id`, `phpbb_forums`.`forum_id`, 0, `phpbb_acl_roles`.`role_id`, 0
FROM `phpbb_groups`, `phpbb_forums`, `phpbb_acl_roles`
WHERE `phpbb_groups`.`group_name`='GLOBAL_MODERATORS'
AND `phpbb_acl_roles`.`role_name`='ROLE_FORUM_FULL'
AND (
    `phpbb_forums`.`forum_name`='MASH'
    OR `phpbb_forums`.`forum_name`='General Discussion'
    OR `phpbb_forums`.`forum_name`='Help'
    OR `phpbb_forums`.`forum_name`='Feature Requests'
    OR `phpbb_forums`.`forum_name`='MASH SDK / Heuristics development'
    OR `phpbb_forums`.`forum_name`='Heuristics development'
    OR `phpbb_forums`.`forum_name`='Back to Basics'
    OR `phpbb_forums`.`forum_name`='Project development'
    OR `phpbb_forums`.`forum_name`='Development'
);


-- Set the permissions of the forums: group REGISTERED, Restricted forums
INSERT INTO `phpbb_acl_groups` (`group_id`, `forum_id`, `auth_option_id`, `auth_role_id`, `auth_setting`) VALUES
(2, 9, 21, 0, 1),
(2, 9, 20, 0, 1),
(2, 9, 14, 0, 1),
(2, 9, 4, 0, 1),
(2, 9, 7, 0, 1),
(2, 9, 13, 0, 1),
(2, 9, 24, 0, 1),
(2, 9, 25, 0, 1),
(2, 9, 8, 0, 1),
(2, 9, 9, 0, 1),
(2, 9, 19, 0, 1),
(2, 9, 22, 0, 1),
(2, 9, 27, 0, 1),
(2, 9, 15, 0, 1),
(2, 9, 18, 0, 1),
(2, 9, 23, 0, 1),
(2, 9, 29, 0, 1),
(2, 9, 1, 0, 1);

INSERT INTO `phpbb_acl_groups` (`group_id`, `forum_id`, `auth_option_id`, `auth_role_id`, `auth_setting`)
SELECT `phpbb_acl_groups`.`group_id`, `phpbb_forums`.`forum_id`, `phpbb_acl_groups`.`auth_option_id`, `phpbb_acl_groups`.`auth_role_id`, `phpbb_acl_groups`.`auth_setting`
FROM `phpbb_acl_groups`, `phpbb_groups`, `phpbb_forums`
WHERE `phpbb_groups`.`group_name`='REGISTERED'
AND `phpbb_acl_groups`.`group_id`=`phpbb_groups`.`group_id`
AND `phpbb_acl_groups`.`forum_id`=9
AND (
    `phpbb_forums`.`forum_name`='Heuristics'
    OR `phpbb_forums`.`forum_name`='Experiments'
);


-- Set the permissions of the forums: group 'Project members', Standard Access + Polls
INSERT INTO `phpbb_acl_groups` (`group_id`, `forum_id`, `auth_option_id`, `auth_role_id`, `auth_setting`)
SELECT `phpbb_groups`.`group_id`, `phpbb_forums`.`forum_id`, 0, `phpbb_acl_roles`.`role_id`, 0
FROM `phpbb_groups`, `phpbb_forums`, `phpbb_acl_roles`
WHERE `phpbb_groups`.`group_name`='Project members'
AND `phpbb_acl_roles`.`role_name`='ROLE_FORUM_POLLS'
AND (
    `phpbb_forums`.`forum_name`='Project development'
    OR `phpbb_forums`.`forum_name`='Development'
);
