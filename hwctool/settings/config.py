"""Provide config for hwctool."""
import configparser
import logging
import sys

module_logger = logging.getLogger('hwctool.settings.config')  # create logger

this = sys.modules[__name__]

this.parser = None


def init(file):
    """Init config."""
    # Reading the configuration from file
    module_logger.info(file)
    this.parser = configparser.ConfigParser()
    try:
        this.parser.read(file, encoding='utf-8-sig')
    except Exception:
        this.parser.defaults()

    setDefaultConfigAll()


def representsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def representsFloat(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


# Setting default values for config file
def setDefaultConfig(sec, opt, value, func=None):
    """Set default value in config."""
    if(not this.parser.has_section(sec)):
        this.parser.add_section(sec)

    if(not this.parser.has_option(sec, opt)):
        if(func):
            try:
                value = func()
            except Exception:
                pass
        this.parser.set(sec, opt, value)
    elif(value in ["True", "False"]):
        try:
            this.parser.getboolean(sec, opt)
        except Exception:
            if(func):
                try:
                    value = func()
                except Exception:
                    pass
            this.parser.set(sec, opt, value)
    elif(representsInt(value)):
        try:
            this.parser.getint(sec, opt)
        except Exception:
            if(func):
                try:
                    value = func()
                except Exception:
                    pass
            this.parser.set(sec, opt, value)
    elif(representsFloat(value)):
        try:
            this.parser.getfloat(sec, opt)
        except Exception:
            if(func):
                try:
                    value = func()
                except Exception:
                    pass
            this.parser.set(sec, opt, value)


def setDefaultConfigAll():
    """Define default values and set them."""
    setDefaultConfig("Twitch", "channel", "")
    setDefaultConfig("Twitch", "oauth", "")
    setDefaultConfig("Twitch", "title_template",
                     "(League) – (Team1) vs (Team2)")
    setDefaultConfig("Twitch", "set_game", "True")
    setDefaultConfig("Twitch", "set_community", "True")

    setDefaultConfig("Nightbot", "token", "")

    setDefaultConfig("SCT", "fuzzymatch", "True")
    setDefaultConfig("SCT", "new_version_prompt", "True")
    setDefaultConfig("SCT", "language", "en_US")

    setDefaultConfig("Form", "autotwitch", "False")
    setDefaultConfig("Form", "autonightbot", "False")

    setDefaultConfig("MapIcons", "win_color", "#008000")
    setDefaultConfig("MapIcons", "lose_color", "#f22200")
    setDefaultConfig("MapIcons", "undecided_color", "#aaaaaa")
    setDefaultConfig("MapIcons", "notplayed_color", "#aaaaaa")

    setDefaultConfig("Style", "score", "Default")
    setDefaultConfig("Style", "intro", "Default")
    setDefaultConfig("Style", "use_custom_font", "False")
    setDefaultConfig("Style", "custom_font", "Verdana")

    setDefaultConfig("Intros", "hotkey_player1", "")
    setDefaultConfig("Intros", "hotkey_player2", "")
    setDefaultConfig("Intros", "hotkey_debug", "")
    setDefaultConfig("Intros", "sound_volume", "5")
    setDefaultConfig("Intros", "display_time", "3.0")
    setDefaultConfig("Intros", "animation", "Fly-In")
    setDefaultConfig("Intros", "tts_active", "False")
    setDefaultConfig("Intros", "tts_lang", "en")
    setDefaultConfig("Intros", 'tts_scope', "team_player")
    setDefaultConfig("Intros", "tts_volume", "5")


def nightbotIsValid():
    """Check if nightbot data is valid."""
    from hwctool.settings import nightbot_commands
    return (len(this.parser.get("Nightbot", "token")) > 0 and
            len(nightbot_commands) > 0)


def twitchIsValid():
    """Check if twitch data is valid."""
    twitchChannel = this.parser.get("Twitch", "Channel")
    oauth = this.parser.get("Twitch", "oauth")
    return (len(oauth) > 0 and len(twitchChannel) > 0)


def loadHotkey(string):
    try:
        name, scan_code, is_keypad = str(string).split(',')
        data = dict()
        data['name'] = name.strip().upper()
        data['scan_code'] = int(scan_code.strip())
        data['is_keypad'] = is_keypad.strip().lower() == "true"
        return data
    except Exception:
        return {'name': '', 'scan_code': 0, 'is_keypad': False}


def dumpHotkey(data):
    try:
        return "{name}, {scan_code}, {is_keypad}".format(**data)
    except Exception:
        return ""
