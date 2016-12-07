# -*- coding: utf-8 -*-
"""
Debugging on Windows
--------------------

Debugging applications on windows under a debugger/ide can be difficult
because the IDE may use its own 'console' which Prompt Toolkit is unable
to use productively.  In these cases it is possible to set an environment
variable which allows Prompt Toolkit to create a console window and
attach the appropriate handles to allow the program to use the console
productively.

Two conditions need to be present for this to work. First, the code needs
to be imported before anything else that may use the std file handles, or
the console, because they may cache these handles, and thus wouldn't work
as hoped.

.. code:: python

    from prompt_toolkit.utils import is_windows
    if is_windows():
        from prompt_toolkit.terminal import win32_console_debug

        # check if any environment variables are set that induce us to action
        win32_console_debug.check_environment_variables()

The second condition needed is to set an environment variable::

   SET USE_WIN_CONSOLE=Window Identifier

or alternatively, if managing the import directly, right after the import,
call:

.. code:: python

    win32_console_debug.ensure_console(title="Window Identifier")

or, if it is preferred to only invoke when the application is being
'debugged', set an environment variable::

   SET USE_WIN_CONSOLE_DEBUG=Window Identifier

or right after the import, call:

.. code:: python

    win32_console_debug.ensure_console(
        debugger_only=True, title="Window Identifier")

The console will be reused (based on the "Window Identifier" passed in)
when restarting the application.


Other Console Support (or starting in pre-existing terminals)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As an additional operating mode, :module:`~prompt_toolkit.win_console_debug`
may be directly executed in a terminal::

    c:\> python win_console_debug.py Window Identifier

When run as a script it will prep the terminal to allow it to be connected to.
This allows other terminals to be supported by debugging with an environment
variable of::

    SET USE_EXISTING_WIN_CONSOLE=Window Identifier

USE_EXISTING_WIN_CONSOLE will not create a console if a console to connect
to does not already exist.

------

This Module originally by @StephenRauch (on github)
"""
from __future__ import unicode_literals
from __future__ import print_function

import os
import sys

__all__ = (
    'ensure_console',
    'in_debugger',
)


def ensure_console(debugger_only=False, **kwargs):
    """
    Ensure that the program, is attached to a console.  This should be
    imported before other imports as other imports can cache stdin,
    etc and thus would not talk to the console attached by this code.

    :param debugger_only: if forcing a console is only desired when run under a
                            debugger, set to True.
    """
    if os.name == 'nt' and (not debugger_only or in_debugger()):
        if sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty():
            return
        _attach_console(**kwargs)


def _attach_console(title=None, create_console=True):
    """
    attach a console to this process

    :param title: desired window name (also the pipe name to find window pid)
    :param create_console: False if the stub program is already running in a
                           terminal with the correct 'title'
    """

    import json
    import win32console
    import win32api
    import win32file

    def find_window_by_pipe_name(pipe_name, retry=True):
        """
        Use the pipe name to return the pid of our console window for attaching

        :param pipe_name: published pipe name
        :return: pid of the windows console we created
        """
        import win32con
        import win32security
        import win32pipe

        try:
            handle = win32file.CreateFile(
                u'\\\\.\\pipe\\' + pipe_name,
                win32con.GENERIC_READ,
                0,
                win32security.SECURITY_ATTRIBUTES(),
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_OVERLAPPED,
                0)
        except win32file.error as exc:
            if exc.winerror != 2:
                # not file not found...
                print(exc)
            return None, None

        console_pid = win32pipe.GetNamedPipeServerProcessId(handle)
        try:
            status, from_pipe = win32file.ReadFile(handle, 65536)
        except win32file.error as exc:
            if exc.winerror == 109 and retry:
                # The pipe has ended
                return find_window_by_pipe_name(pipe_name, retry=False)
            raise
        win32api.CloseHandle(handle)
        remote_env = json.loads(from_pipe.decode("utf-8")) \
            if status == 0 else None
        return console_pid, remote_env

    def get_new_console(pipe_name, console_title=None):
        """
        Start a new console and return its PID

        :param pipe_name: Name for the pipe used to find the desired window
        :param console_title: window title if different than the pipe name
        """
        import tempfile
        import time
        from subprocess import Popen

        # create a temporary copy of our stub file
        console_title = console_title or pipe_name
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(
                (_stub_program % (pipe_name, console_title)).encode('utf-8'))
            stub_filename = f.name

        # spawn a command shell
        start = 'start cmd /k'.split(' ')
        start.append('@%s %s' % (sys.executable, stub_filename))
        Popen(start, shell=True)

        # find the pid of the newly spawned shell
        tries = 20
        console_pid, remote_env = None, None
        while console_pid is None:
            console_pid, remote_env = find_window_by_pipe_name(pipe_name)
            time.sleep(0.1)
            tries -= 1
            if tries <= 0:
                raise IOError('Did not find window: %s' % pipe_name)

        # remove the copy of the stub file
        os.unlink(stub_filename)

        return console_pid, remote_env

    def do_attach_console(console_pid):
        try:
            win32console.FreeConsole()
        except win32file.error:
            pass
        win32console.AttachConsole(console_pid)

    def set_console_handle(fileno, filename, mode):
        # close the existing fileno file, so we can reuse it
        os.close(fileno)

        # open the file to the console
        f = open(filename, mode, 0)

        # verify that we got the correct fileno
        assert f.fileno() == fileno

        # set the console handle
        osfhandle = win32file._get_osfhandle(fileno)
        win32api.SetStdHandle(-(fileno + 10), osfhandle)

        # return the file
        return f

    def set_console_handles():
        # connect all of std handles to the console
        sys.stdin = sys.__stdin__ = set_console_handle(0, 'CONIN$', 'rb')
        sys.stdout = sys.__stdout__ = set_console_handle(1, 'CONOUT$', 'wb+')
        sys.stderr = sys.__stderr__ = set_console_handle(2, 'CONOUT$', 'wb+')
        if sys.version_info[0] != 2:
            sys.stdout.buffer = sys.stdout
            sys.stderr.buffer = sys.stderr

    def window_to_foreground(window_handle):
        try:
            window_handle = int(window_handle)
        except ValueError:
            window_handle = int(window_handle, 16)
        import win32gui
        try:
            win32gui.ShowWindow(window_handle, 9)
            win32gui.SetForegroundWindow(window_handle)
        except win32file.error:
            pass

    def show_connection_msg(msg):
        """
        When connecting to the console, show an inverted message, and position
        the cursor at the left margin.

        :param msg: message to show
        """
        screen_buffer = win32console.GetStdHandle(-11)
        info = screen_buffer.GetConsoleScreenBufferInfo()
        cursor_position = info['CursorPosition']
        if cursor_position.X != 0:
            # the cursor is not at the left edge...
            #   so go to left edge and down one line
            cursor_position.X = 0
            cursor_position.Y += 1
            screen_buffer.SetConsoleCursorPosition(cursor_position)

        attr = info['Attributes']
        inverted = (attr & 0x8) | ((attr & 7) << 4) | ((attr & 0x70) >> 4)
        screen_buffer.SetConsoleTextAttribute(inverted)
        sys.stdout.write(msg.encode("utf-8"))
        sys.stdout.flush()
        screen_buffer.SetConsoleTextAttribute(attr)

    def show_handles_as_connection_msg():
        """ Small routine to help debug console connection problems """
        hi = win32api.GetStdHandle(-10)
        ho = win32api.GetStdHandle(-11)
        he = win32api.GetStdHandle(-12)
        show_connection_msg(
            "Connecting w/ HANDLES: in:%s out:%s err:%s\n" % (hi, ho, he))

    def find_or_create_console(window_title, create_new=True):
        # find or create a console to attach to
        window_title = window_title or os.path.basename(sys.argv[0])
        console_pipe_name = 'FIND_CONSOLE: %s' % window_title
        console_pid, remote_env = find_window_by_pipe_name(console_pipe_name)
        if not console_pid:
            if create_new:
                console_pid, remote_env = get_new_console(
                    console_pipe_name, console_title=window_title)
            else:
                # announce on stdout, that we failed to found a console
                print("Console window not found for %s" % window_title)
                return None, None

        # announce on the previous stdout, that we found a console
        print("Found debug console pid %d,  pipe name: '%s'" % (
            console_pid, console_pipe_name))

        return console_pid, remote_env

    def reattach_sigint_handler():
        try:
            import thread
        except ImportError:
            import _thread as thread

        # Set our handler for CTRL_C_EVENT. Other control event
        # types will chain to the next handler.
        def handler(dw_ctrl_type, hook_sigint=thread.interrupt_main):
            if dw_ctrl_type == 0:  # CTRL_C_EVENT
                hook_sigint()
                return 1  # don't chain to the next handler
            return 0  # chain to the next handler

        win32api.SetConsoleCtrlHandler(handler, 1)

    def prepare_console(console_pid, remote_env):
        # attach to the console
        do_attach_console(console_pid)
        set_console_handles()

        # grab the sigint handler
        reattach_sigint_handler()

        # bring the console to the front
        window_to_foreground(
            remote_env.get('CONEMUDRAWHWND') or remote_env.get('WINDOW_HANDLE'))

        # put a break in the console output, to show the new connection status
        if True:
            import datetime
            show_connection_msg(
                ("Connected at %s\n" % str(datetime.datetime.now())[:-3]))
        else:
            show_handles_as_connection_msg()

    # get a console window
    pid, env = find_or_create_console(title, create_new=create_console)

    # get the console ready...
    if pid:
        prepare_console(pid, env)


def check_environment_variables():
    _win32_consoles = dict(
        USE_WIN_CONSOLE=(True, False),
        USE_WIN_CONSOLE_DEBUG=(True, True),
        USE_EXISTING_WIN_CONSOLE=(False, False),
        USE_EXISTING_WIN_CONSOLE_DEBUG=(False, True),
    )

    # ensure that the console is attached as requested via environment variable
    for env_var, params in _win32_consoles.items():
        if env_var in os.environ:
            create_console, debug_only = params
            window_title = os.environ[env_var]
            ensure_console(debugger_only=debug_only,
                           create_console=create_console,
                           title=window_title)
            return True
    return False


def _start_remote():
    """
    If this module is 'run' then we will execute the stub program, which
    will patiently wait for someone to connect to its console

    :return: Not usually
    """
    if len(sys.argv) < 2:
        print("USAGE: %s <Window Identifier>" % sys.argv[0])
        sys.exit(-1)

    title = ' '.join(sys.argv[1:])
    pipe_name = 'FIND_CONSOLE: ' + title
    program = _stub_program % (pipe_name, title)
    exec(program)


_in_debugger = None


def in_debugger():
    """
    Try to determine if running under a debugger

    :return: True if in the debugger
    """
    global _in_debugger
    if _in_debugger is None:
        if __debug__ and 'WINGDB_ACTIVE' in os.environ:
            _in_debugger = True
        else:
            _in_debugger = False
            import inspect
            for frame in inspect.stack():
                if os.path.basename(frame[1]) in ("pydevd.py", "pdb.py"):
                    _in_debugger = True
                    break

    return _in_debugger


_stub_program = """# -*- coding: utf-8 -*-
# short program which runs in the console and starts a named pipe so that this
# module can find the window.  This program also ties up the existing shell
# so he doesn't steal keystrokes.

# this is rather a hack because I couldn't figure out how to init a console
# and attach to it. So this module starts this console program which does
# very little.

from __future__ import print_function

import os
import sys
import win32pipe
import win32file
import win32api
import win32console
import win32gui
import json
import uuid

# create a name for our pipe
pipe_name = u"\\\\\\\\.\\\\pipe\\\\%s"
print('debug window pipe name:', pipe_name)

# get our window handle
tmp_title = str(uuid.uuid4())
win32console.SetConsoleTitle(tmp_title)
window_handle = None
while not window_handle:
    window_handle = win32gui.FindWindowEx(0, 0, None, tmp_title)

# set the window title
title = "%s"
win32console.SetConsoleTitle(title)

# get the local environment and add our window handle
env = dict(os.environ)
env['WINDOW_HANDLE'] = '%%s' %% window_handle
json_env = json.dumps(env).encode('utf-8')

def start_pipe(name):
    import win32con
    import win32pipe
    import win32security
    sa = win32security.SECURITY_ATTRIBUTES()
    return win32pipe.CreateNamedPipe(
        name,
        win32con.PIPE_ACCESS_OUTBOUND,
        win32con.PIPE_TYPE_BYTE,
        1, 0, 0, 0, sa)

pipe = start_pipe(pipe_name)
kbdint = False
while 1:
    try:
        if not kbdint:
            h_pipe = win32pipe.ConnectNamedPipe(pipe)
            if h_pipe != 0:
                print("win32pipe.ConnectNamedPipe", h_pipe)
        else:
            kbdint = False

        win32file.WriteFile(pipe, json_env)
        win32file.CloseHandle(h_pipe)
        win32pipe.DisconnectNamedPipe(pipe)
    except win32file.error as exc:
        if exc[0] not in [6, 232]:
            raise
        print(exc)
        win32api.CloseHandle(pipe)
        pipe = start_pipe(pipe_name)
    except KeyboardInterrupt:
        kbdint = True

"""

if __name__ == "__main__":
    _start_remote()
