"""Linux-only OS-enforced sandbox layer inside an already isolated container."""
import base64
import ctypes
import errno
import json
import os
import resource
import shlex
import subprocess
import sys

payload=json.load(open(sys.argv[1]))
resource.setrlimit(resource.RLIMIT_CPU,(2,2))
resource.setrlimit(resource.RLIMIT_FSIZE,(32768,32768))
resource.setrlimit(resource.RLIMIT_AS,(192*1024*1024,192*1024*1024))
resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
# Inherited by shells and subprocesses: no networking, tracing, namespace or mount operations.
lib=ctypes.CDLL('libseccomp.so.2',use_errno=True)
lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
lib.seccomp_load.argtypes=[ctypes.c_void_p];lib.seccomp_release.argtypes=[ctypes.c_void_p]
ctx=lib.seccomp_init(0x7fff0000)
if not ctx: raise RuntimeError('seccomp initialization failed')
for name in ('setsid','setpgid','kill','tkill','tgkill','socket','socketpair','connect','bind','listen','accept','accept4','ptrace','process_vm_readv','process_vm_writev','mount','umount2','unshare','setns','bpf','keyctl'):
    nr=lib.seccomp_syscall_resolve_name(name.encode())
    if nr>=0 and lib.seccomp_rule_add(ctx,0x00050000|errno.EPERM,nr,0)!=0: raise RuntimeError('seccomp rule failed')
if lib.seccomp_load(ctx)!=0: raise RuntimeError('seccomp load failed')
lib.seccomp_release(ctx)

action=payload['action']
if action=='template':
    from flask import Flask,render_template_string
    with Flask('isolated-demo').app_context():
        print(render_template_string(payload.get('template',''),shop='VOLTIX'))
elif action=='upload':
    source=base64.b64decode(payload.get('source',''),validate=True)
    if len(source)>65536: raise ValueError('Python exercise limit: 64KB')
    # This is intentionally real Python execution, only inside the disposable container.
    exec(compile(source,'student-upload.py','exec'),{'__name__':'__main__'})
elif action=='command':
    target=payload.get('target','')
    command='echo '+target  # VULN-10: shell metacharacters influence command processing.
    # Restrict the lesson to demonstrative commands. No arbitrary host tools or paths.
    import re
    if not re.fullmatch(r'[a-zA-Z0-9_ .;|&/\-]*',target): raise ValueError('실습 문자는 영문/숫자/공백/;|&/.-만 허용')
    tokens=list(shlex.shlex(command,posix=True,punctuation_chars=';&|'))
    groups=[];group=[]
    for token in tokens:
        if token in (';','&&','||','|','&'):
            if not group: raise ValueError('Invalid command')
            groups.append(group);group=[]
        else: group.append(token)
    if group: groups.append(group)
    allowed={'echo','id','whoami','pwd','uname'}
    if any(not g or g[0] not in allowed or any('/' in t for t in g) for g in groups): raise ValueError('허용 명령: echo, id, whoami, pwd, uname')
    subprocess.run(command,shell=True,check=False)
