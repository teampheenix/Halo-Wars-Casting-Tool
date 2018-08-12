"""Sent request to Nightbot and Twitch if needed."""
import logging

from PyQt5.QtCore import pyqtSignal

import hwctool.settings
import hwctool.tasks.nightbot
import hwctool.tasks.twitch
from hwctool.tasks.tasksthread import TasksThread

# create logger
module_logger = logging.getLogger('hwctool.tasks.autorequests')


class AutoRequestsThread(TasksThread):
    """Sent request to Nightbot and Twitch if needed."""

    twitchSignal = pyqtSignal(str)
    nightbotSignal = pyqtSignal(str)
    disableCB = pyqtSignal(str)

    def __init__(self, controller):
        """Init the thread."""
        super().__init__()

        self.__controller = controller
        self.setTimeout(10)

        self.addTask('twitch', self.__twitchTask)
        self.addTask('twitch_once', self.__twitchOnceTask)
        self.addTask('nightbot', self.__nightbotTask)
        self.addTask('nightbot_once', self.__nightbotOnceTask)

        self.twitchSignal.connect(controller.displayWarning)
        self.nightbotSignal.connect(controller.displayWarning)
        self.disableCB.connect(controller.uncheckCB)

    def __twitchTask(self):
        title = hwctool.settings.config.parser.get("Twitch", "title_template")
        title = self.__controller.placeholders.replace(title)

        if(hwctool.tasks.twitch.previousTitle is None):
            hwctool.tasks.twitch.previousTitle = title
        elif(hwctool.tasks.twitch.previousTitle != title):
            msg, success = hwctool.tasks.twitch.updateTitle(title)
            self.twitchSignal.emit(msg)
            if not success:
                self.disableCB.emit('twitch')
                self.deactivateTask('twitch')

    def __twitchOnceTask(self):
        try:
            title = hwctool.settings.config.parser.get(
                "Twitch", "title_template")
            title = self.__controller.placeholders.replace(title)
            msg, success = hwctool.tasks.twitch.updateTitle(title)
            self.twitchSignal.emit(msg)
        finally:
            self.deactivateTask('twitch_once')

    def __nightbotTask(self):
        data = dict()
        for command, message in hwctool.settings.nightbot_commands.items():
            message = self.__controller.placeholders.replace(message)
            if(hwctool.tasks.nightbot.previousMsg.get(command, None) is None):
                hwctool.tasks.nightbot.previousMsg[command] = message
            elif(hwctool.tasks.nightbot.previousMsg[command] != message):
                data[command] = message

        for cmd, msg, success, deleted in \
                hwctool.tasks.nightbot.updateCommand(data):
            self.nightbotSignal.emit(msg)
            if not success:
                self.disableCB.emit('nightbot')
                self.deactivateTask('nightbot')
            if deleted:
                hwctool.settings.nightbot_commands.pop(cmd, None)

    def __nightbotOnceTask(self):
        try:
            data = dict()
            for command, message in hwctool.settings.nightbot_commands.items():
                message = self.__controller.placeholders.replace(message)
                data[command] = message
            for cmd, msg, _, deleted in \
                    hwctool.tasks.nightbot.updateCommand(data):
                self.nightbotSignal.emit(msg)
                if deleted:
                    hwctool.settings.nightbot_commands.pop(cmd, None)
        finally:
            self.deactivateTask('nightbot_once')
