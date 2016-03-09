<?php
/**
 * AuthViaDjango MediaWiki extension MediaWiki version 1.15.0
 *
 * @file
 * @ingroup Extensions
 * @version 1.0
 * @author Philip Abbet
 */
 
# Not a valid entry point, skip unless MEDIAWIKI is defined
if( !defined( 'MEDIAWIKI' ) )
{
	echo "AuthViaDjango extension";
	die();
}


function AuthViaDjango($user, &$result)
{
    wfSetupSession();
 
    # Retrieve the user infos from the session id
    $djangoSessionID = $_COOKIE['sessionid'];

	global $wgDBserver, $wgDBname, $wgDBuser, $wgDBpassword;
	
	$db = new Database($wgDBserver, $wgDBuser, $wgDBpassword, $wgDBname);
	
	$sql = "SELECT auth_user.id as user_id, auth_user.username as username, auth_user.email as email
            FROM auth_user, sessionprofile_sessionprofile as sp
            WHERE sp.session_id='" . mysql_real_escape_string($djangoSessionID) . "'
            AND auth_user.id = sp.user_id";
	$result = $db->query($sql);

	if ($db->numRows($result) != 1)
	{
        // Can't load from session ID, user is anonymous
        $user->setName('Guest');
        $user->setId(0);
        return true;
	}

    $row = $db->fetchRow($result);
    
	$db->freeResult($result);

    /**
     * A lot of this is from User::newFromName
     */
    // Force usernames to capital
    global $wgContLang;
 
    $name = $wgContLang->ucfirst($row['username']);
 
    // Clean up name according to title rules
    $t = Title::newFromText($name);
    if (is_null($t))
    {
        return true ;
    }
 
    $canonicalName = $t->getText();
 
    if (!User::isValidUserName($canonicalName))
    {
        return true;
    }
 
    $user->setName($canonicalName);
 
    $user_id_fromMW_DB = $user->idFromName($row['username']);
 
    $user->setId($user_id_fromMW_DB);
    if ($user->getID() == 0)
    {
        /**
        * A lot of this is from LoginForm::initUser
        * LoginForm is in the file called SpecialUserLogin.php line 342 (version 1.14.0rc1)
        */
        $canonicalName = $t->getText();
        $user->setName($canonicalName);
        $user->addToDatabase();
 
        $user->setEmail($row['email']);
        $user->setRealName('');
        $user->setToken();
 
        $user->saveSettings();

        $sql = "UPDATE accounts_userprofile SET wiki_user_id=" . $user->getID() . " WHERE user_id=" . $row['user_id'];
    	$db->query($sql);
    }
    else
    {
        if (!$user->loadFromDatabase())
        {
            // Can't load from ID, user is anonymous
            return true ;
        }
    
        $user->saveToCache();
    }
 
    $result = 1;    // This causes the rest of the authentication process to be skipped.
    return false;   // As should this.
}


# Remove the login link on all pages
function NoLoginLinkOnAllPage(&$personal_urls)
{
    unset($personal_urls['login']);
    unset($personal_urls['logout']);
    unset($personal_urls['anonlogin']);
    return true;
}


# Remove the login special page
function NoLoginSpecialPage(&$special_pages)
{
    unset($special_pages['Userlogin']);
    unset($special_pages['CreateAccount']);
    unset($special_pages['Resetpass']);
    return true;
}


$wgHooks['UserLoadFromSession'][] = 'AuthViaDjango';
$wgHooks['PersonalUrls'][] = 'NoLoginLinkOnAllPage';
$wgHooks['SpecialPage_initList'][] = 'NoLoginSpecialPage';
