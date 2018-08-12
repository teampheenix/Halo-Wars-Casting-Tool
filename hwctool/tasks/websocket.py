"""Interaction with Browser Source via Websocket."""
import asyncio
import json
import logging
import re
from uuid import uuid4

import keyboard
import websockets
from PyQt5.QtCore import QThread, pyqtSignal

import hwctool.settings

# create logger
module_logger = logging.getLogger('hwctool.tasks.websocket')


class WebsocketThread(QThread):
    """Thread for websocket interaction."""

    keyboard_state = dict()
    hooked_keys = dict()
    socketConnectionChanged = pyqtSignal(int, str)
    valid_scopes = ['score', 'intro']
    mapicon_sets = dict()
    scopes = dict()
    intro_state = ''
    introShown = pyqtSignal()

    def __init__(self, controller):
        """Init thread."""
        QThread.__init__(self)
        self.connected = dict()
        self.__loop = None
        self.__controller = controller
        self.setup_scopes()
        self._hotkeys_active = False
        self.hooked_keys['intro'] = set()

    def setup_scopes(self):
        self.scope_regex = re.compile(r'_\[\d-\d\]')
        for scope in self.valid_scopes:
            scope = self.scope_regex.sub('', scope)
            self.scopes[scope] = set()

    def get_primary_scopes(self):
        return list(self.scopes.keys())

    def run(self):
        """Run thread."""
        module_logger.info("WebSocketThread starting!")
        self.connected = dict()
        self.__loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__loop)

        port = int(hwctool.settings.profileManager.currentID(), 16)
        module_logger.info(
            'Starting Websocket Server with port {}.'.format(port))
        # Create the server.
        start_server = websockets.serve(self.handler,
                                        host='localhost',
                                        port=port,
                                        max_queue=16,
                                        max_size=10240,
                                        read_limit=10240,
                                        write_limit=10240)
        self.__server = self.__loop.run_until_complete(start_server)
        self.__loop.run_forever()

        # Shut down the server.
        self.__server.close()
        self.__loop.run_until_complete(self.__server.wait_closed())
        self.unregister_hotkeys(force=True)

        module_logger.info("WebSocketThread finished!")

    def stop(self):
        if self.__loop is not None:
            module_logger.info("Requesting stop of WebsocketThread.")
            self.__loop.call_soon_threadsafe(self.__loop.stop)

    def __callback_on_hook(self, scan_code, is_keypad, e, callback):
        if e.is_keypad == is_keypad:
            if e.event_type == keyboard.KEY_DOWN:
                if((scan_code, is_keypad) not in self.keyboard_state or
                   self.keyboard_state[(scan_code, is_keypad)]):
                    try:
                        callback()
                    except Exception as e:
                        module_logger.exception("message")
                self.keyboard_state[(scan_code, is_keypad)] = False
            if e.event_type == keyboard.KEY_UP:
                self.keyboard_state[(scan_code, is_keypad)] = True

    def __register_hotkey(self, hotkey, callback, scope='intro'):
        if isinstance(hotkey, str):
            hotkey = hwctool.settings.config.loadHotkey(hotkey)
        if not hotkey['name']:
            return
        if hotkey['scan_code'] == 0:
            return

        value = keyboard.hook_key(
            hotkey['scan_code'],
            lambda e, hotkey=hotkey: self.__callback_on_hook(
                hotkey['scan_code'],
                hotkey['is_keypad'],
                e,
                callback))
        self.hooked_keys[scope].add(value)

    def register_hotkeys(self, scope=''):
        if not scope:
            for scope in self.hooked_keys:
                self.register_hotkeys(scope)
            return
        elif scope == 'intro':
            if (not self.hooked_keys[scope] and
                    len(self.connected.get('intro', [])) > 0):
                module_logger.info('Register intro hotkeys.')
                player1 = hwctool.settings.config.loadHotkey(
                    hwctool.settings.config.parser.get(
                        "Intros", "hotkey_player1"))
                player2 = hwctool.settings.config.loadHotkey(
                    hwctool.settings.config.parser.get(
                        "Intros", "hotkey_player2"))
                if player1 == player2:
                    self.__register_hotkey(player1,
                                           lambda: self.showIntro(-1))
                else:
                    self.__register_hotkey(player1,
                                           lambda: self.showIntro(0))

                    self.__register_hotkey(player2,
                                           lambda: self.showIntro(1))

                self.__register_hotkey(
                    hwctool.settings.config.parser.get(
                        "Intros", "hotkey_debug"),
                    lambda: self.sendData2Path("intro", "DEBUG_MODE", dict()))

        module_logger.info('Registered {} hotkeys.'.format(scope))

    def unregister_hotkeys(self, scope='', force=False):
        if not scope:
            for scope in self.hooked_keys:
                self.unregister_hotkeys(scope)
            if force:
                try:
                    keyboard.unhook_all()
                except AttributeError:
                    pass
            self.keyboard_state = dict()
        else:
            while self.hooked_keys[scope]:
                try:
                    keyboard.unhook(self.hooked_keys[scope].pop())
                except ValueError:
                    pass

            module_logger.info('Unregistered {} hotkeys.'.format(scope))

    def handle_path(self, path):
        paths = path.split('/')[1:]

        for path in paths:
            for scope in self.valid_scopes:
                if re.match(scope, path):
                    return path
        return ''

    def get_primary_scope(self, path):
        if path in self.scopes.keys():
            return path
        for scope in self.valid_scopes:
            if re.match(scope, path):
                return self.scope_regex.sub('', scope)
        return ''

    async def handler(self, websocket, path):
        path = self.handle_path(path)
        if not path:
            module_logger.info("Client with incorrect path.")
            return
        self.registerConnection(websocket, path)
        module_logger.info("Client connected!")
        primary_scope = self.get_primary_scope(path)
        if primary_scope == 'score':
            data = self.__controller.matchData.getScoreData()
            self.sendData2WS(websocket, "ALL_DATA", data)

        while True:
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=20)
                if msg == self.intro_state:
                    self.intro_state = ''
                    self.introShown.emit()
            except asyncio.TimeoutError:
                try:
                    pong_waiter = await websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10)
                except asyncio.TimeoutError:
                    # No response to ping in 10 seconds, disconnect.
                    module_logger.info(
                        "No response to ping in 10 seconds, disconnect.")
                    break
            except websockets.ConnectionClosed:
                module_logger.info("Connection closed")
                break

        module_logger.info("Connection removed")
        self.unregisterConnection(websocket, path)

    def registerConnection(self, websocket, path):
        if path not in self.connected.keys():
            self.connected[path] = set()
        primary_scope = self.get_primary_scope(path)
        self.scopes[primary_scope].add(path)
        self.connected[path].add(websocket)
        self.socketConnectionChanged.emit(
            len(self.connected[path]), primary_scope)
        if primary_scope == 'intro':
            self.register_hotkeys('intro')

    def unregisterConnection(self, websocket, path):
        if path in self.connected.keys():
            self.connected[path].remove(websocket)
            primary_scope = self.get_primary_scope(path)
            num = len(self.connected[path])
            self.socketConnectionChanged.emit(num, primary_scope)
            if primary_scope == 'intro' and num == 0:
                self.unregister_hotkeys('intro')

    def changeStyle(self, path, style=None, websocket=None):
        primary_scope = self.get_primary_scope(path)
        if primary_scope:
            if style is None:
                style = hwctool.settings.config.parser.get(
                    "Style", primary_scope)
            style_file = "src/css/{}/{}.css".format(primary_scope, style)
            if websocket is None:
                self.sendData2Path(path, "CHANGE_STYLE", {'file': style_file})
            else:
                self.sendData2WS(websocket, "CHANGE_STYLE",
                                 {'file': style_file})
        else:
            raise ValueError('Change style is not available for this path.')

    def changeFont(self, path=None, font=None, websocket=None):
        valid_paths = ['score']
        if path is None:
            for path in valid_paths:
                self.changeFont(path, font)
            return
        if path in valid_paths:
            if font is None:
                if not hwctool.settings.config.parser.getboolean(
                    "Style",
                        "use_custom_font"):
                    font = "DEFAULT"
                else:
                    font = hwctool.settings.config.parser.get(
                        "Style", "custom_font")
            if websocket is None:
                self.sendData2Path(path, "CHANGE_FONT", {'font': font})
            else:
                self.sendData2WS(websocket, "CHANGE_FONT", {'font': font})
        else:
            raise ValueError('Change font is not available for this path.')

    def showIntro(self, idx):
        self.intro_state = self.sendData2Path(
            "intro", "SHOW_INTRO",
            self.__controller.getPlayerIntroData(idx))

    def sendData2Path(self, path, event, input_data, state=''):
        if not state:
            state = str(uuid4())

        if isinstance(path, list):
            for item in path:
                self.sendData2Path(item, event, input_data, state)
            return
        try:
            data = dict()
            data['event'] = event
            data['data'] = input_data
            data['state'] = state

            paths = self.scopes.get(path, [path])

            for path in paths:
                connections = self.connected.get(path, set()).copy()
                for websocket in connections:
                    module_logger.info(
                        "Sending data to '{}': {}".format(path, data))
                    coro = websocket.send(json.dumps(data))
                    asyncio.run_coroutine_threadsafe(coro, self.__loop)
        except Exception as e:
            module_logger.exception("message")

        return state

    def sendData2WS(self, websocket, event, input_data, state=''):
        if not state:
            state = str(uuid4())

        if isinstance(websocket, list):
            for item in websocket:
                self.sendData2WS(item, event, input_data, state)
            return
        try:
            data = dict()
            data['event'] = event
            data['data'] = input_data
            data['state'] = state
            module_logger.info("Sending data: %s" % data)
            coro = websocket.send(json.dumps(data))
            asyncio.run_coroutine_threadsafe(coro, self.__loop)
        except Exception as e:
            module_logger.exception("message")

        return state
