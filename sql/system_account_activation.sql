UPDATE `auth_user` SET `is_active`='1', `is_staff`='1', `is_superuser`='1'
WHERE `auth_user`.`username`='$ACCOUNT_NAME';