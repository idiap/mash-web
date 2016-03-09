UPDATE `phpbb_users` SET `user_rank`='8' WHERE `phpbb_users`.`username`='$ACCOUNT_NAME';


INSERT INTO `phpbb_acl_users` (`user_id`, `forum_id`, `auth_option_id`, `auth_role_id`, `auth_setting`)
SELECT `phpbb_users`.`user_id`, `phpbb_forums`.`forum_id`, 17, 0, 1
FROM `phpbb_users`, `phpbb_forums`
WHERE `phpbb_users`.`username`='$ACCOUNT_NAME'
AND (
    `phpbb_forums`.`forum_name`='Heuristics'
    OR `phpbb_forums`.`forum_name`='Experiments'
);


INSERT INTO `phpbb_acl_users` (`user_id`, `forum_id`, `auth_option_id`, `auth_role_id`, `auth_setting`)
SELECT `phpbb_users`.`user_id`, `phpbb_forums`.`forum_id`, 1, 0, 1
FROM `phpbb_users`, `phpbb_forums`
WHERE `phpbb_users`.`username`='$ACCOUNT_NAME'
AND (
    `phpbb_forums`.`forum_name`='Heuristics'
    OR `phpbb_forums`.`forum_name`='Experiments'
);
