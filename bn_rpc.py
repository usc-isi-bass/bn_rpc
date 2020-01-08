import json
import os
import socket
import sys

if len(sys.argv) != 2:
    print("Usage: python bn_rpyc.py <script>")
    exit(1)

script = sys.argv[1]
if os.path.exists(script):
    script = os.path.abspath(script)
else:
    print("Can't find: %s" % script)
    exit(1)

py3 = sys.version_info[0] >= 3
if not py3:
    input = raw_input


s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(os.path.expanduser('~/.bn_rpc.sock'))
if py3:
    sin = s.makefile('r', buffering=1, encoding='utf8')
else:
    sin = s.makefile('r', bufsize=1)

def send(cmd, **m):
    m['cmd'] = cmd
    s.send((json.dumps(m) + '\n').encode('utf8'))

def recv():
    line = sin.readline()
    if not py3:
        line = line.decode('utf8')
    return json.loads(line)

done = False
while True:
    m = recv()
    cmd = m['cmd']
    if cmd == 'prompt':
        if done:
            s.shutdown(socket.SHUT_RDWR)
            break
        prompt = m['prompt']
        try:
            line = "exec(open(\"%s\").read())" % script
            send('input', text=line + '\n')
        except KeyboardInterrupt:
            send('reset')
        except EOFError:
            s.shutdown(socket.SHUT_RDWR)
            break
        done = True
    elif cmd == 'print':
        print(m['text'].rstrip('\n'))
    elif cmd == 'exit':
        break
print

