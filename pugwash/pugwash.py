import json
import pathlib

from pathlib import Path

import rect
import gui
import tfont

import sdl2
import sdl2.ext


ROOT_PATH = Path(__file__).parent
DATA_PATH = ROOT_PATH / "data"


class InfoDB():
    def __init__(self, renderer, data_file):
        self._renderer = renderer
        self._data = {}
        self._textures = {}
        self._data_root = None
        self._ports = []

        if data_file.is_file():
            self.data_load(data_file)

    def data_load(self, data_file):
        for texture in self._textures.values():
            texture.destroy()
        self._textures.clear()

        with data_file.open('rt') as fh:
            self._data = json.load(fh)

        self._ports = list(self._data['ports'].keys())
        self._ports.sort(key=lambda port_name: self._data['ports'][port_name]['attr']['title'].casefold())
        self._data_root = data_file.parent

    def _font_key(self, font, style="default"):
        return f"{font.family_name}:{font._styles[style]['size']}:{font._styles[style]['color']!r}:{font._styles[style]['bg']!r}"

    def port_info(self, port_name):
        return self._data["ports"].get(port_name)

    def get_port_attr_text_surface(self, port_name, attr, font, *, width=None, style="default", align="left"):
        text = self.port_info(port_name)['attr'][attr]
        if not isinstance(attr, str):
            raise KeyError(attr)

        key = f"text:{port_name}:{attr}:{self._font_key(font, style)}:{align}"
        if key not in self._textures:
            surface = font.render_text(text, style=style, width=width, align=align)
            texture = self._textures[key] = sdl2.ext.Texture(self._renderer, surface)
            sdl2.SDL_FreeSurface(surface)
            return texture

        return self._textures[key]

    def get_port_image_surface(self, port_name):
        key = f"image:{port_name}"
        if key not in self._textures:
            surface = sdl2.ext.load_img(
                str(self._data_root / self.port_info(port_name)['attr']['image']['screenshot']))
            texture = self._textures[key] = sdl2.ext.Texture(self._renderer, surface)
            sdl2.SDL_FreeSurface(surface)
            return texture

        return self._textures[key]

    def ports_list(self):
        return list(self._data["ports"].keys())


class EventHandler():
    ## TODO: add deadzone code, and key repeat code.

    BUTTON_MAP = {
        sdl2.SDL_CONTROLLER_BUTTON_A: 'A',
        sdl2.SDL_CONTROLLER_BUTTON_B: 'B',
        sdl2.SDL_CONTROLLER_BUTTON_X: 'X',
        sdl2.SDL_CONTROLLER_BUTTON_Y: 'Y',

        sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER: 'L1',
        sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: 'L1',
        # sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT:    'L2',
        # sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT:   'R2',
        sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK:    'L3',
        sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK:   'R3',

        sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:      'UP',
        sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:    'DOWN',
        sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:    'LEFT',
        sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:   'RIGHT',

        sdl2.SDL_CONTROLLER_BUTTON_START:        'START',
        sdl2.SDL_CONTROLLER_BUTTON_GUIDE:        'GUIDE',
        sdl2.SDL_CONTROLLER_BUTTON_BACK:         'BACK',
        }

    AXIS_MAP = {
        sdl2.SDL_CONTROLLER_AXIS_LEFTX: 'LX',
        sdl2.SDL_CONTROLLER_AXIS_LEFTY: 'LY',
        sdl2.SDL_CONTROLLER_AXIS_RIGHTX: 'RX',
        sdl2.SDL_CONTROLLER_AXIS_RIGHTY: 'RY',
        sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT: 'L2',
        sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT: 'R2',
        }

    AXIS_TO_BUTTON = {
        'LX': ('L_LEFT', None, 'L_RIGHT'),
        'LY': ('L_UP',   None, 'L_DOWN'),
        'RX': ('R_LEFT', None, 'R_RIGHT'),
        'RY': ('R_UP',   None, 'R_DOWN'),
        'L2': (None,    None, 'L2'),
        'R2': (None,    None, 'R2'),
        }

    REPEAT_MAP = [
        'UP',
        'DOWN',
        'LEFT',
        'RIGHT',

        'L_UP',
        'L_DOWN',
        'L_LEFT',
        'L_RIGHT',

        'R_UP',
        'R_DOWN',
        'R_LEFT',
        'R_RIGHT',
        ]

    # Wait 1.5 seconds
    REPEAT_DELAY = 800
    # Trigger every 1 second
    REPEAT_RATE = 300

    ANALOG_MIN = 2048
    TRIGGER_MIN = 1024

    def __init__(self):
        sdl2.ext.init(controller=True)

        self.running = True
        self.buttons = {
            key: False
            for key in self.BUTTON_MAP.values()}

        self.buttons.update({
            key: False
            for key in self.AXIS_TO_BUTTON.keys()})

        self.axis = {
            key: 0.0
            for key in self.AXIS_MAP.values()}

        self.axis_button = {
            key: None
            for key in self.AXIS_MAP.values()}

        self.repeat = {
            key: None
            for key in self.REPEAT_MAP}

        self.last_buttons = {}
        self.last_buttons.update(self.buttons)

        self.controller = None
        self.trigger_min = self.TRIGGER_MIN
        self.analog_min = self.ANALOG_MIN
        self.ticks = sdl2.SDL_GetTicks()

        ## Change this to handle other controllers.
        for i in range(sdl2.SDL_NumJoysticks()):
            if sdl2.SDL_IsGameController(i) == sdl2.SDL_TRUE:
                self.controller = sdl2.SDL_GameControllerOpen(i)

    def _axis_map(self, axis, limit):
        if abs(axis) < limit:
            return 1
        if axis < 0:
            return 0
        return 2

    def handle_events(self):
        # To handle WAS pressed do: 
        #    self.buttons['UP'] and not self.last_buttons['UP']
        self.last_buttons.update(self.buttons)

        ticks_now = sdl2.SDL_GetTicks64()

        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                self.running = False
                break

            elif event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
                key = self.BUTTON_MAP.get(event.cbutton.button, None)
                if key is not None:
                    print(f'PRESSED {key}')
                    self.buttons[key] = True

                    if key in self.repeat:
                        self.repeat[key] = ticks_now + self.REPEAT_DELAY

            elif event.type == sdl2.SDL_CONTROLLERBUTTONUP:
                key = self.BUTTON_MAP.get(event.cbutton.button, None)
                if key is not None:
                    print(f'RELEASED {key}')
                    self.buttons[key] = False

                    if key in self.repeat:
                        self.repeat[key] = None

            elif event.type == sdl2.SDL_CONTROLLERAXISMOTION:
                if event.caxis.axis in self.AXIS_MAP:
                    key = self.AXIS_MAP[event.caxis.axis]
                    # print(f'MOVED {key} {event.caxis.value}')
                    self.axis[key] = event.caxis.value

                    last_axis_key = self.axis_button[key]
                    axis_key = self.AXIS_TO_BUTTON[key][self._axis_map(event.caxis.value, self.analog_min)]

                    if axis_key is not None:
                        if last_axis_key is None:
                            print(f"PRESSED {axis_key}")
                            self.buttons[axis_key] = True

                            if axis_key in self.repeat:
                                self.repeat[axis_key] = ticks_now + self.REPEAT_DELAY
                        elif last_axis_key != axis_key:
                            print(f"RELEASED {last_axis_key}")
                            self.buttons[last_axis_key] = True
                            if last_axis_key in self.repeat:
                                self.repeat[last_axis_key] = None

                    elif axis_key is None:
                        if last_axis_key is not None:
                            print(f"RELEASED {last_axis_key}")
                            self.buttons[last_axis_key] = True
                            if last_axis_key in self.repeat:
                                self.repeat[last_axis_key] = None

                    self.axis_button[key] = axis_key

        for key in self.repeat.keys():
            next_repeat = self.repeat[key]
            if next_repeat is not None and next_repeat <= ticks_now:
                # Trigger was_pressed state
                self.last_buttons[key] = False
                print(f'REPEAT {key} {ticks_now - next_repeat}')
                self.repeat[key] = ticks_now + self.REPEAT_RATE


    def was_pressed(self, button):
        return self.buttons.get(button, False) and not self.last_buttons.get(button, False)

    def was_released(self, button):
        return not self.buttons.get(button, False) and self.last_buttons.get(button, False)


def main():
    # Initialize SDL
    sdl2.ext.init(
        joystick=True)

    # Define window dimensions
    display_width = 640
    display_height = 480

    # Get the current display mode
    display_mode = sdl2.video.SDL_DisplayMode()

    if sdl2.video.SDL_GetCurrentDisplayMode(0, display_mode) != 0:
        print("Failed to get display mode:", sdl2.SDL_GetError())
    else:
        display_width = display_mode.w
        display_height = display_mode.h
        # Print the display width and height
        print("Display size:", display_mode.w, "x", display_mode.h)


    # Create the window
    window = sdl2.ext.Window("Game UI", size=(display_width, display_height))
    window.show()

    # Create a renderer for drawing on the window
    renderer = sdl2.ext.Renderer(window,
            flags=sdl2.SDL_RENDERER_ACCELERATED)

    info = InfoDB(
        renderer,
        DATA_PATH / "ports.json")

    fonts = tfont.FontManager(renderer)


    gui.Image.renderer = renderer
    images = gui.ImageManager(renderer)

    # Define font
    # font = sdl2.ext.FontTTF(str(DATA_PATH / "DejaVuSans.ttf"), size=12, color=colors["black"])

    with open(DATA_PATH / "theme.json") as fh:
        theme = json.load(fh)

    regions = {
        }
    registry = {
        "port_list": None,
        "port_title": None,
        "port_preview": None,
        "port_desc": None,
        }

    for region_name in theme:
        region_info = theme[region_name]['info']
        regions[region_name] = region = gui.Region(renderer, theme[region_name], images, fonts)
        if region_info in registry:
            registry[region_info] = region

    # Event loop
    running = True
    selected_game = 0
    update = True

    if registry["port_list"] is not None:
        registry["port_list"].list = [
            info.port_info(port_name)['attr']['title']
            for port_name in info.ports_list()]

    event = EventHandler()

    while True:
        event.handle_events()

        if not event.running:
            break

        if event.was_pressed('UP'):
            selected_game -= 1
            update = True

        if event.was_pressed('DOWN'):
            selected_game += 1
            update = True

        if event.was_pressed('A'):
            print(f"Selected Game: {selected_game} -> {info.ports_list()[selected_game]}")

        if event.buttons['START'] and event.buttons['BACK']:
            # Quit :D
            ## TODO: get code from gptokeyb
            break

        if update:
            port_name = info.ports_list()[selected_game]

            port_info = info.port_info(port_name)

            if registry["port_list"] is not None:
                registry["port_list"].selected = selected_game

            port_preview = registry["port_preview"]
            if port_preview:
                port_preview.image = str(DATA_PATH / port_info['attr']['image']['screenshot'])

            port_desc = registry["port_desc"]
            if port_desc:
                port_desc.text = port_info['attr']['desc']

        if update:
            renderer.clear()

            for region_name in regions:
                regions[region_name].update()

            for region_name in regions:
                regions[region_name].draw()

            update = False

            renderer.present()
        window.refresh()

        sdl2.SDL_Delay(10)

    # Clean up
    sdl2.ext.quit()


if __name__ == '__main__':
    main()
