#!/usr/bin/env python3
import curses
import curses.ascii
import sys

class Liv:
    def __init__(self, stdscr, filename=None):
        self.stdscr, self.filename = stdscr, filename
        self.buffer = [''] if not filename else self._load_file(filename)
        self.cursor_y = self.cursor_x = self.offset_y = 0
        self.command_mode = False
        self.command_buffer = ''
        self.message = ''
        self.message_is_error = False
        self.commands = ['write', 'quit', 'writequit', 'clear', 'name']
        self.aliases = ['w', 'q', 'save', 's', 'wq', 'sq', 'savequit', 'x', 'filename', 'n']
        self._init_colors()

    @staticmethod
    def _init_colors():
        curses.start_color()
        curses.use_default_colors()
        color_pairs = [(1, curses.COLOR_BLACK, curses.COLOR_WHITE),    # Status line
                       (2, curses.COLOR_YELLOW, curses.COLOR_BLACK),   # Command line
                       (3, curses.COLOR_BLUE, curses.COLOR_BLACK),     # Suggestion line
                       (4, curses.COLOR_RED, curses.COLOR_WHITE)]      # Error messages
        for pair, fg, bg in color_pairs:
            curses.init_pair(pair, fg, bg)
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
        curses.mouseinterval(0)
        try: curses.curs_set(1)
        except: pass

    def _load_file(self, filename):
        try:
            with open(filename, 'r') as f:
                lines = f.read().splitlines()
            self.message = f"Loaded {filename}"
            return lines or ['']
        except FileNotFoundError:
            self.message = f"New file: {filename}"
            return ['']

    def _save_file(self):
        if not self.filename:
            self.set_message("No filename specified", is_error=True)
            return False
        try:
            with open(self.filename, 'w') as f:
                f.write('\n'.join(self.buffer))
            self.set_message(f"Saved {self.filename}")
            return True
        except Exception as e:
            self.set_message(f"Error saving file: {str(e)}", is_error=True)
            return False

    def set_message(self, msg, is_error=False):
        self.message, self.message_is_error = msg, is_error

    def _get_suggestion(self, partial):
        return next((cmd for cmd in self.commands if cmd.startswith(partial.lower())), '')

    def _handle_edit_keys(self, key):
        if not self.message_is_error:
            self.message = ''

        if key == curses.KEY_F2:
            self.command_mode, self.command_buffer = True, ''
            return

        line = self.buffer[self.cursor_y]
        if key in (curses.KEY_BACKSPACE, 127):
            # Backspace handling
            self.buffer[self.cursor_y] = line[:self.cursor_x-1] + line[self.cursor_x:] if self.cursor_x > 0 else line
            self.cursor_x = max(0, self.cursor_x - 1) if self.cursor_x > 0 else self._join_previous_line()
        elif key in (curses.KEY_ENTER, 10):
            # Enter key handling
            self.buffer[self.cursor_y] = line[:self.cursor_x]
            self.buffer.insert(self.cursor_y + 1, line[self.cursor_x:])
            self.cursor_y, self.cursor_x = self.cursor_y + 1, 0
        elif key == curses.KEY_LEFT: self.cursor_x = max(0, self.cursor_x - 1)
        elif key == curses.KEY_RIGHT: self.cursor_x = min(len(line), self.cursor_x + 1)
        elif key == curses.KEY_UP: self._move_cursor_vertical(-1)
        elif key == curses.KEY_DOWN: self._move_cursor_vertical(1)
        elif key == curses.KEY_MOUSE: self._handle_mouse_event()
        elif curses.ascii.isprint(key):
            self.buffer[self.cursor_y] = line[:self.cursor_x] + chr(key) + line[self.cursor_x:]
            self.cursor_x += 1

    def _join_previous_line(self):
        if self.cursor_y > 0:
            prev_line_length = len(self.buffer[self.cursor_y - 1])
            self.buffer[self.cursor_y - 1] += self.buffer[self.cursor_y]
            self.buffer.pop(self.cursor_y)
            self.cursor_y -= 1
            return prev_line_length
        return 0

    def _move_cursor_vertical(self, direction):
        new_y = self.cursor_y + direction
        if 0 <= new_y < len(self.buffer):
            self.cursor_y = new_y
            self.cursor_x = min(self.cursor_x, len(self.buffer[self.cursor_y]))

    def _handle_mouse_event(self):
        try:
            _, mx, my, _, _ = curses.getmouse()
            height, _ = self.stdscr.getmaxyx()
            if my < height - 2:
                self.cursor_y = min(max(0, my + self.offset_y), len(self.buffer) - 1)
                self.cursor_x = min(max(0, mx), len(self.buffer[self.cursor_y]))
        except curses.error: pass

    def _handle_command_mode(self, key):
        if key == curses.KEY_F2:
            self.command_mode, self.command_buffer = False, ''
            self.set_message("Command mode cancelled")
        elif key in (curses.KEY_BACKSPACE, 127):
            self.command_buffer = self.command_buffer[:-1]
        elif key in (curses.KEY_ENTER, 10):
            self._execute_command(self.command_buffer)
        elif key == ord('\t'):
            self.command_buffer = self._get_suggestion(self.command_buffer)
        elif curses.ascii.isprint(key):
            self.command_buffer += chr(key)

    def _execute_command(self, command):
        cmd = command.strip().lower()
        actions = {
            'q': sys.exit,
            'quit': sys.exit,
            'w': lambda: self._save_file() and None,
            'write': lambda: self._save_file() and None,
            'save': lambda: self._save_file() and None, #ALIAS
            'writequit': lambda: self._save_file() and sys.exit(0),
            'savequit': lambda: self._save_file() and sys.exit(0),
            'sq': lambda: self._save_file() and sys.exit(0),
            'wq': lambda: self._save_file() and sys.exit(0),
            'x': lambda: self._save_file() and sys.exit(0),
            'clear': lambda: self._clear_buffer(),
            'name': lambda: self._set_filename(cmd),
            'filename': lambda: self._set_filename(cmd),
            'n': lambda: self._set_filename(cmd)
        }

        if cmd.startswith(('name', 'filename', 'n')) and len(cmd.split()) > 1:
            self.filename = cmd.split()[1]
            self.set_message(f"Filename set to {self.filename}")
        elif action := actions.get(cmd):
            action()
        else:
            self.set_message(f"Unknown command: {cmd}", is_error=True)

    def _clear_buffer(self):
        self.buffer, self.cursor_x, self.cursor_y = [''], 0, 0
        self.set_message("Buffer cleared")

    def _set_filename(self, cmd):
        if len(cmd.split()) > 1:
            self.filename = cmd.split()[1]
        self.set_message(f"Filename set to {self.filename}")

    def run(self):
        while True:
            self._draw()
            key = self.stdscr.getch()
            (self._handle_command_mode if self.command_mode else self._handle_edit_keys)(key)

    def _draw(self):
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()

        # Adjust view offset
        self.offset_y = max(0, min(self.offset_y, self.cursor_y - height + 3))

        # Draw buffer content
        try:
            for i, line in enumerate(self.buffer[self.offset_y:self.offset_y + height - 2]):
                self.stdscr.addstr(i, 0, line[:width - 1])
        except curses.error: pass

        # Draw status line
        status = f" {self.filename or 'new file'} - {self.message or 'editing'} ."
        try:
            self.stdscr.attron(curses.color_pair(4 if self.message_is_error else 1))
            self.stdscr.addstr(height - 3 if self.command_mode else height - 2, 0, status.ljust(width))
            self.stdscr.attroff(curses.color_pair(4 if self.message_is_error else 1))
        except curses.error: pass

        # Draw command and suggestion lines
        if self.command_mode:
            try:
                if suggestion := self._get_suggestion(self.command_buffer):
                    self.stdscr.attron(curses.color_pair(3))
                    self.stdscr.addstr(height - 2, 0, f"→ {suggestion}".ljust(width))
                    self.stdscr.attroff(curses.color_pair(3))

                self.stdscr.attron(curses.color_pair(2))
                self.stdscr.addstr(height - 1, 0, self.command_buffer.ljust(width))
                self.stdscr.attroff(curses.color_pair(2))
            except curses.error: pass

        # Position cursor
        try:
            self.stdscr.move(height - 1 if self.command_mode else self.cursor_y - self.offset_y,
                              len(self.command_buffer) if self.command_mode else self.cursor_x)
        except curses.error: pass

        self.stdscr.refresh()

def main(stdscr):
    curses.raw()
    stdscr.keypad(True)
    Liv(stdscr, sys.argv[1] if len(sys.argv) > 1 else None).run()

if __name__ == '__main__':
    curses.wrapper(main)