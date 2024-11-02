#!/usr/bin/env python3
import curses
import sys
import curses.ascii


class SimpleEditor:
    def __init__(self, stdscr, filename=None):
        self.stdscr = stdscr
        self.filename = filename
        self.buffer = []
        self.cursor_y = 0
        self.cursor_x = 0
        self.offset_y = 0
        self.command_mode = False
        self.command_buffer = ''
        self.message = ''
        self.message_is_error = False  # New flag to track error messages
        self.commands = ['write', 'quit', 'write+quit', 'wq', 'x', 'clear']  # Available commands
        self.current_suggestion = ''
        self.init_colors()

        if filename:
            self.load_file(filename)
        else:
            self.buffer = ['']

    @staticmethod
    def init_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Status line
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Command line
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)  # Suggestion line
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_WHITE)  # Error messages
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
        curses.mouseinterval(0)
        try:
            curses.curs_set(1)
        except:
            pass

    def set_message(self, msg, is_error=False):
        self.message = msg
        self.message_is_error = is_error

    def get_suggestion(self, partial):
        if not partial:
            return ''
        for cmd in self.commands:
            if cmd.startswith(partial.lower()):
                return cmd
        return ''

    def load_file(self, filename):
        try:
            with open(filename, 'r') as f:
                self.buffer = f.read().splitlines()
            if not self.buffer:
                self.buffer = ['']
        except FileNotFoundError:
            self.buffer = ['']
            self.set_message(f"New file: {filename}")

    def save_file(self):
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

    def handle_edit_mode(self, key):
        # Only clear non-error messages during editing
        if not self.message_is_error:
            self.message = ''
            self.message_is_error = False

        if key == curses.KEY_F2:  # Toggle command mode
            self.command_mode = True
            self.command_buffer = ''
            self.current_suggestion = ''
            return

        if key in (curses.KEY_BACKSPACE, 127):  # Backspace
            if self.cursor_x > 0:
                line = self.buffer[self.cursor_y]
                self.buffer[self.cursor_y] = line[:self.cursor_x - 1] + line[self.cursor_x:]
                self.cursor_x -= 1
            elif self.cursor_y > 0:  # Join with previous line
                self.cursor_x = len(self.buffer[self.cursor_y - 1])
                self.buffer[self.cursor_y - 1] += self.buffer[self.cursor_y]
                self.buffer.pop(self.cursor_y)
                self.cursor_y -= 1
        elif key == curses.KEY_ENTER or key == 10:  # Enter
            current_line = self.buffer[self.cursor_y]
            self.buffer[self.cursor_y] = current_line[:self.cursor_x]
            self.buffer.insert(self.cursor_y + 1, current_line[self.cursor_x:])
            self.cursor_y += 1
            self.cursor_x = 0
        elif key == curses.KEY_LEFT:
            if self.cursor_x > 0:
                self.cursor_x -= 1
        elif key == curses.KEY_RIGHT:
            if self.cursor_x < len(self.buffer[self.cursor_y]):
                self.cursor_x += 1
        elif key == curses.KEY_UP:
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self.cursor_x = min(self.cursor_x, len(self.buffer[self.cursor_y]))
        elif key == curses.KEY_DOWN:
            if self.cursor_y < len(self.buffer) - 1:
                self.cursor_y += 1
                self.cursor_x = min(self.cursor_x, len(self.buffer[self.cursor_y]))
        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, _ = curses.getmouse()
                height, _ = self.stdscr.getmaxyx()
                if my < height - 2:
                    self.cursor_y = my + self.offset_y
                    self.cursor_x = mx
                    self.cursor_y = min(max(0, self.cursor_y), len(self.buffer) - 1)
                    self.cursor_x = min(max(0, self.cursor_x), len(self.buffer[self.cursor_y]))
            except curses.error:
                pass
        elif curses.ascii.isprint(key):  # Printable characters
            line = self.buffer[self.cursor_y]
            self.buffer[self.cursor_y] = line[:self.cursor_x] + chr(key) + line[self.cursor_x:]
            self.cursor_x += 1

    def handle_command_mode(self, key):
        if key == curses.KEY_F2:  # Cancel command mode
            self.command_mode = False
            self.command_buffer = ''
            self.current_suggestion = ''
            self.set_message("Command mode cancelled")
        elif key in (curses.KEY_BACKSPACE, 127):  # Backspace
            if self.command_buffer:
                self.command_buffer = self.command_buffer[:-1]
                self.current_suggestion = self.get_suggestion(self.command_buffer)
        elif key == curses.KEY_ENTER or key == 10:  # Enter
            self.execute_command(self.command_buffer)
        elif key == ord('\t'):  # Tab completion
            if self.current_suggestion:
                self.command_buffer = self.current_suggestion
                self.current_suggestion = self.get_suggestion(self.command_buffer)
        elif curses.ascii.isprint(key):  # Printable characters
            self.command_buffer += chr(key)
            self.current_suggestion = self.get_suggestion(self.command_buffer)

    def execute_command(self, command):
        cmd = command.strip().lower()
        if cmd in ('q', 'quit'):
            sys.exit(0)
        elif cmd in ('w', 'write'):
            self.save_file()
            self.command_mode = False
        elif cmd in ('write+quit', 'wq', 'x'):
            if self.save_file():
                sys.exit(0)
            # If save failed, we'll stay in the editor with the error message
        elif cmd == 'clear':
            self.buffer = ['']
            self.cursor_x = 0
            self.cursor_y = 0
            self.command_mode = False
            self.set_message("Buffer cleared")
        else:
            self.set_message(f"Unknown command: {cmd}", is_error=True)
            # Don't exit command mode on error, let user try again or cancel

    def draw(self):
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()

        # Adjust offset if cursor is out of view
        if self.cursor_y - self.offset_y >= height - 2:
            self.offset_y = self.cursor_y - height + 3
        elif self.cursor_y < self.offset_y:
            self.offset_y = self.cursor_y

        # Draw buffer content
        for i in range(min(height - 3 if self.command_mode else height - 2,
                           len(self.buffer) - self.offset_y)):
            line = self.buffer[i + self.offset_y]
            try:
                self.stdscr.addstr(i, 0, line[:width - 1])
            except curses.error:
                pass

        # Draw status line
        status = f" {self.filename or '[No Name]'} "
        if self.message:
            status += f"- {self.message}"
        try:
            self.stdscr.attron(curses.color_pair(4 if self.message_is_error else 1))
            self.stdscr.addstr(height - 3 if self.command_mode else height - 2,
                               0, status.ljust(width))
            self.stdscr.attroff(curses.color_pair(4 if self.message_is_error else 1))
        except curses.error:
            pass

        # Draw command line and suggestion
        if self.command_mode:
            # Draw suggestion line
            if self.current_suggestion:
                try:
                    self.stdscr.attron(curses.color_pair(3))
                    self.stdscr.addstr(height - 2, 0, f"→ {self.current_suggestion}".ljust(width))
                    self.stdscr.attroff(curses.color_pair(3))
                except curses.error:
                    pass

            # Draw command input line
            try:
                self.stdscr.attron(curses.color_pair(2))
                self.stdscr.addstr(height - 1, 0, self.command_buffer.ljust(width))
                self.stdscr.attroff(curses.color_pair(2))
            except curses.error:
                pass

        # Position cursor
        try:
            if self.command_mode:
                self.stdscr.move(height - 1, len(self.command_buffer))
            else:
                self.stdscr.move(self.cursor_y - self.offset_y, self.cursor_x)
        except curses.error:
            pass

        # Refresh the screen
        self.stdscr.refresh()

    def run(self):
        while True:
            self.draw()
            key = self.stdscr.getch()

            if self.command_mode:
                self.handle_command_mode(key)
            else:
                self.handle_edit_mode(key)


def main(stdscr):
    # Set up terminal
    curses.raw()
    stdscr.keypad(True)

    # Get filename from command line argument
    filename = sys.argv[1] if len(sys.argv) > 1 else None

    # Create and run editor
    editor = SimpleEditor(stdscr, filename)
    editor.run()


if __name__ == '__main__':
    curses.wrapper(main)