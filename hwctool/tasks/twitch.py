"""Update the twitch title to the title specified in the config file."""
import logging

import requests

import hwctool.settings


# create logger
module_logger = logging.getLogger(__name__)

previousTitle = None


def updateTitle(newTitle):
    """Update the twitch title to the title specified in the config file."""
    global previousTitle

    try:
        twitchChannel = hwctool.settings.config.parser.get(
            "Twitch", "Channel").strip()
        userID = getUserID(twitchChannel)

        clientID = hwctool.settings.safe.get('twitch-client-id')
        oauth = hwctool.settings.config.parser.get("Twitch", "oauth")

        headers = {'Accept': 'application/vnd.twitchtv.v5+json',
                   'Authorization': f'OAuth {oauth}',
                   'Client-ID': clientID}

        params = {'channel[status]': newTitle}

        if hwctool.settings.config.parser.getboolean("Twitch", "set_game"):
            params['channel[game]'] = 'Halo Wars 2'

        requests.put(f'https://api.twitch.tv/kraken/channels/{userID}',
                     headers=headers, params=params).raise_for_status()
        msg = _('Updated Twitch title of {} to: "{}"').format(
            twitchChannel, newTitle)
        success = True
        previousTitle = newTitle

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        error_msg = "Twitch API-Error: {}"
        if(status_code == 404):
            msg = _("Not Found - Channel '{}'"
                    " not found.").format(twitchChannel)
            msg = error_msg.format(msg)
        elif(status_code == 403):
            msg = error_msg.format(_("Forbidden - Do you have permission?"))
        elif(status_code == 401):
            msg = error_msg.format(_("Unauthorized - Refresh your token!"))
        elif(status_code == 429):
            msg = error_msg.format(_("Too Many Requests."))
        else:
            msg = str(e)
        success = False
        module_logger.exception("message")
    except Exception as e:
        msg = str(e)
        success = False
        module_logger.exception("message")

    return msg, success


def getUserID(login):
    """Get a user's ID from twitch API."""
    client_id = hwctool.settings.safe.get('twitch-client-id')
    url = 'https://api.twitch.tv/helix/users'
    oauth = hwctool.settings.config.parser.get("Twitch", "oauth")
    headers = {'Client-ID': client_id, 'Authorization': f'Bearer {oauth}'}
    params = {'login': login}

    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json().get('data')[0]['id']
