from binaryninja import *
_locals = locals().copy()
_locals.update({m: __import__(m) for m in (
    'os', 're', 'sys',
)})

import gc
import io
import json
import logging
import os
import rlcompleter
import signal
import socket
import sys
import threading
import traceback
from code import InteractiveConsole

# python2/3 compat
py3 = sys.version_info[0] >= 3

if py3: import socketserver
else:   import SocketServer as socketserver

def socket_makefile(s, mode):
    if py3:
        return s.makefile(mode, buffering=1, encoding='utf8')
    else:
        return s.makefile(mode, bufsize=1)

# end python compat

class StdoutWriter(io.IOBase):
    def __init__(self, shell): self.shell = shell
    def write(self, b): return self.shell.output(b)
    def writable(self): return True

class InteractiveServer(socketserver.BaseRequestHandler):
    def handle(self):
        old = sys.stdout
        olderr = sys.stderr
        try:
            shell = Shell(self.request)
            sys.stdout = StdoutWriter(shell) # io.TextIOWrapper(io.BufferedWriter(StdoutWriter(shell)), line_buffering=True, encoding='utf8')
            shell.interact()
        except SystemExit:
            pass
        finally:
            sys.stdout = old
            sys.stderr = olderr

class Shell(InteractiveConsole):
    def __init__(self, s):
        self.s = s
        self.buf = socket_makefile(s, 'r')
        self.outbuf = []
        self.reset_count = 0
        InteractiveConsole.__init__(self)
        self.locals.update(_locals)
        self.completer = rlcompleter.Completer(self.locals)
    """
        self._interpreter = None

    @property
    def interpreter(self):
        if not self._interpreter:
            obj = [o for o in gc.get_objects() if isinstance(o, scriptingprovider.PythonScriptingInstance.InterpreterThread)]
            if obj:
                self._interpreter = obj[0]
        return self._interpreter
    """

    def traceback(self):
        self.write(traceback.format_exc())

    def write(self, data):
        try:
            self.send('print', text=data)
        except IOError:
            logging.info(traceback.format_exc())
            raise SystemExit

    def output(self, b):
        if not py3: b = b.decode('utf8')
        self.outbuf.append(b)
        return len(b)

    def recv(self):
        line = self.buf.readline()
        if not py3: line = line.decode('utf8')
        if not line: return None
        return json.loads(line)

    def send(self, cmd, **kwargs):
        kwargs['cmd'] = cmd
        try:
            self.s.send((json.dumps(kwargs) + '\n').encode('utf8'))
        except socket.error as e:
            logging.info("Sock Error: %s" % str(e))

    def prompt(self, prompt):
        if self.outbuf:
            self.send('print', text=''.join(self.outbuf))
            self.outbuf = []
        self.send('prompt', prompt=prompt)

    def interact(self):
        # ps1 = '>>> '
        # ps2 = '... '
        ps1 = ''
        ps2 = ''
        """
        self.write('Python {} on {}\n'.format(sys.version, sys.platform))
        """
        self.prompt(ps1)
        while True:
            m = self.recv()
            if not m:
                self.send('exit')
                break
            cmd = m['cmd']
            if cmd == 'input':
                self.reset_count = 0
                more = self.push(m['text'])
                if more:
                    self.prompt(ps2)
                else:
                    self.prompt(ps1)
            elif cmd == 'complete':
                self.send('completion', text=self.completer.complete(m['text'], m['state']))
            elif cmd == 'reset':
                if self.buffer:
                    self.resetbuffer()
                    self.prompt(ps1)
                else:
                    self.reset_count += 1
                    if self.reset_count >= 2:
                        self.send('exit')
                        break
                    self.prompt(ps1)

path = os.path.expanduser('~/.bn_rpc.sock')
if os.path.exists(path):
    os.unlink(path)
socketserver.UnixStreamServer.allow_reuse_address = True
server = socketserver.UnixStreamServer(path, InteractiveServer)
t = threading.Thread(target=server.serve_forever)
t.daemon = True
t.start()
