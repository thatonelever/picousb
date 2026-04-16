import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from keyboard_layout_win_tr import KeyboardLayout
import busio
import board
import time
import digitalio
import adafruit_character_lcd.character_lcd as character_lcd
import os

lcd_rs = digitalio.DigitalInOut(board.GP6)
lcd_en = digitalio.DigitalInOut(board.GP7)
lcd_d4 = digitalio.DigitalInOut(board.GP8)
lcd_d5 = digitalio.DigitalInOut(board.GP9)
lcd_d6 = digitalio.DigitalInOut(board.GP10)
lcd_d7 = digitalio.DigitalInOut(board.GP11)

lcd = character_lcd.Character_LCD_Mono(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, 16, 2)

btn_next = digitalio.DigitalInOut(board.GP16)
btn_next.direction = digitalio.Direction.INPUT
btn_next.pull = digitalio.Pull.UP

btn_select = digitalio.DigitalInOut(board.GP17)
btn_select.direction = digitalio.Direction.INPUT
btn_select.pull = digitalio.Pull.UP

uart = busio.UART(board.GP0, board.GP1, baudrate=9600)
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayout(kbd)
buffer = ""
default_delay = 0
last_command = None
max_repeat = 1000

duck_key_map = {
    "ENTER": Keycode.ENTER, "TAB": Keycode.TAB, "ESC": Keycode.ESCAPE,
    "SPACE": Keycode.SPACE, "BACKSPACE": Keycode.BACKSPACE, "DELETE": Keycode.DELETE,
    "INSERT": Keycode.INSERT, "HOME": Keycode.HOME, "END": Keycode.END,
    "PAGEUP": Keycode.PAGE_UP, "PAGEDOWN": Keycode.PAGE_DOWN,
    "UP": Keycode.UP_ARROW, "DOWN": Keycode.DOWN_ARROW,
    "LEFT": Keycode.LEFT_ARROW, "RIGHT": Keycode.RIGHT_ARROW,
    "F1": Keycode.F1, "F2": Keycode.F2, "F3": Keycode.F3, "F4": Keycode.F4,
    "F5": Keycode.F5, "F6": Keycode.F6, "F7": Keycode.F7, "F8": Keycode.F8,
    "F9": Keycode.F9, "F10": Keycode.F10, "F11": Keycode.F11, "F12": Keycode.F12
}

modifier_map = {
    "CTRL": Keycode.CONTROL, "CONTROL": Keycode.CONTROL,
    "ALT": Keycode.ALT, "SHIFT": Keycode.SHIFT,
    "GUI": Keycode.GUI, "WINDOWS": Keycode.GUI
}

key_map = {
    "shift": Keycode.SHIFT, "ctrl": Keycode.CONTROL, "alt": Keycode.ALT,
    "enter": Keycode.ENTER, "left": Keycode.LEFT_ARROW, "right": Keycode.RIGHT_ARROW,
    "up": Keycode.UP_ARROW, "down": Keycode.DOWN_ARROW, "delete": Keycode.DELETE,
    "space": Keycode.SPACE,
}

def update_lcd(msg1, msg2=""):
    lcd.clear()
    lcd.message = f"{msg1}\n{msg2}"

def send_uart(msg):
    try:
        full_msg = str(msg) + "\r\n"
        uart.write(full_msg.encode("utf-8"))
        print(f"UART send: {msg}") 
    except Exception as e:
        print(f"UART send error: {e}")

def apply_default_delay():
    if default_delay > 0:
        time.sleep(default_delay / 1000)

def execute_duck_line(line):
    global default_delay, last_command
    if not line or line.startswith("REM"): return

    if line.startswith("STRING "):
        layout.write(line[7:])
        last_command = line
    elif line.startswith("DELAY "):
        time.sleep(int(line.split()[1]) / 1000)
        return
    elif line.startswith("DEFAULT_DELAY "):
        default_delay = int(line.split()[1])
        return
    elif line.startswith("REPEAT "):
        count = min(int(line.split()[1]), max_repeat)
        if last_command:
            for _ in range(count): execute_duck_line(last_command)
        return
    else:
        parts = line.split()
        modifiers, key = [], None
        for part in parts:
            p_up = part.upper()
            if p_up in modifier_map: modifiers.append(modifier_map[p_up])
            elif p_up in duck_key_map: key = duck_key_map[p_up]
            elif len(p_up) == 1 and p_up.isalpha(): key = getattr(Keycode, p_up)
            elif len(p_up) == 1 and p_up.isdigit(): key = getattr(Keycode, "KEYPAD_" + p_up, None)
        
        if key:
            kbd.press(*modifiers, key) if modifiers else kbd.press(key)
            kbd.release_all()
            last_command = line
    apply_default_delay()

def run_duck_file(path):
    full_path = "/scripts/" + path.strip()
    update_lcd("running...", path[:14])
    try:
        with open(full_path, "r") as f:
            lines = f.readlines()
        send_uart(f"executing: {path}")
        for line in lines:
            execute_duck_line(line.strip())
        update_lcd("finished!", path[:14])
        time.sleep(1.5)
    except Exception as e:
        print(f"error: {e}")
        update_lcd("file error.", "check terminal")
        time.sleep(3)
    show_menu()

script_list = []
try:
    script_list = [f for f in os.listdir("/scripts") if f.endswith(".txt")]
except:
    script_list = ["no /scripts fldr"]
if not script_list: script_list = ["no scripts"]

current_index = 0

def show_menu():
    update_lcd("> select:", script_list[current_index])

def execute_command(cmd):
    cmd = cmd.strip()
    if cmd.startswith("exec:"):
        run_duck_file(cmd.split(":")[1])
    elif cmd.startswith('wr:"') and cmd.endswith('"'):
        layout.write(cmd[5:-1])
    elif cmd.startswith("tap:"):
        key = cmd.split(":")[1]
        if key in key_map: kbd.send(key_map[key])
    elif cmd == "releaseall":
        kbd.release_all()
    update_lcd("bt command", cmd[:14])


update_lcd("picoUSB", "")
time.sleep(1)
update_lcd("for more details","lvrsq.org/p/pusb")
time.sleep(2)
show_menu()

while True:
    if uart.in_waiting:
        data = uart.read().decode("utf-8")
        buffer += data
        if "\n" in buffer:
            execute_command(buffer.strip())
            buffer = ""

    if not btn_next.value:
        current_index = (current_index + 1) % len(script_list)
        show_menu()
        time.sleep(0.3)

    if not btn_select.value:
        if script_list[current_index] not in ["no scripts", "no folder"]:
            run_duck_file(script_list[current_index])
        time.sleep(0.3)