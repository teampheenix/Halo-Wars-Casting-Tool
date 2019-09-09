"""Halo Wars Casting Tool."""

import gettext
import logging
import sys

from PyQt5.QtCore import QLocale, QTranslator
from PyQt5.QtWidgets import QApplication, QStyleFactory

import hwctool.settings
import hwctool.settings.config

logger = logging.getLogger('hwctool')

__version__ = "0.1.7"
__latest_version__ = __version__
__new_version__ = False


def main():
    """Run Halo Wars Casting Tool."""
    from hwctool.view.main import MainWindow
    from PyQt5.QtCore import QSize
    from PyQt5.QtGui import QIcon

    translator = None

    currentExitCode = MainWindow.EXIT_CODE_REBOOT
    while currentExitCode == MainWindow.EXIT_CODE_REBOOT:
        try:
            hwctool.settings.loadSettings()
            app = QApplication(sys.argv)
            app.setStyle(QStyleFactory.create('Fusion'))
            translator = choose_language(app, translator)

            icon = QIcon()
            icon.addFile(hwctool.settings.getResFile(
                'hwct.ico'), QSize(32, 32))
            app.setWindowIcon(icon)

            showChangelog, updater = initial_download()
            if updater:
                hwctool.settings.loadSettings()
            main_window(app, showChangelog)
            currentExitCode = app.exec_()
            app = None
        except Exception as e:
            logger.exception("message")
            break

    sys.exit(currentExitCode)


def main_window(app, showChangelog=False):
    """Run the main exectuable."""
    from PyQt5.QtCore import QSize
    from PyQt5.QtGui import QIcon
    from hwctool.controller import MainController
    from hwctool.view.main import MainWindow

    try:
        """Run the main program."""
        icon = QIcon()
        icon.addFile(hwctool.settings.getResFile('hwct.ico'), QSize(32, 32))
        icon.addFile(hwctool.settings.getResFile('hwct.png'), QSize(256, 256))
        app.setWindowIcon(icon)
        cntlr = MainController()
        MainWindow(cntlr, app, showChangelog)
        logger.info("Starting...")
        return cntlr

    except Exception as e:
        logger.exception("message")
        raise


def initial_download():
    """Download the required data at an inital startup."""
    import hwctool.tasks.updater
    from hwctool.view.widgets import InitialUpdater

    version = hwctool.tasks.updater.getDataVersion()
    restart_flag = hwctool.tasks.updater.getRestartFlag()
    updater = False

    if hwctool.tasks.updater.needInitialUpdate(version):
        InitialUpdater()
        updater = True
    elif restart_flag:
        InitialUpdater(version)
        updater = True

    hwctool.tasks.updater.setRestartFlag(False)

    return restart_flag, updater


def choose_language(app, translator):
    language = hwctool.settings.config.parser.get("SCT", "language")

    try:
        lang = gettext.translation(
            'messages',
            localedir=hwctool.settings.getLocalesDir(),
            languages=[language])
    except Exception:
        lang = gettext.NullTranslations()

    lang.install()
    app.removeTranslator(translator)
    translator = QTranslator(app)
    translator.load(QLocale(language), "qtbase",
                    "_", hwctool.settings.getLocalesDir(), ".qm")
    app.installTranslator(translator)

    return translator
