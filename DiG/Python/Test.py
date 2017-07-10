#!/usr/bin/python

import time
import sys
import os
import io
import subprocess
import shlex
from random import randint

std_out_log_file = 'test.stdout'
std_err_log_file = 'test.stderr'

def main():
    try:
        cmd0 = 'echo 888 \n'
        cmd = 'exit 1'
        execute_process([[cmd0, 'wait'], [cmd, 'wait']])
    except Exception as e:
        print e
    finally:
        print 'done'


def execute_process(cmds):
    ret_code = 0
    with io.open(std_out_log_file, 'a') as std_out_log, \
            io.open(std_err_log_file, 'a') as std_err_log:
        for cmd in cmds:
            std_out_log.write(str(cmd[0]).decode('unicode-escape'))
            std_err_log.write(str(cmd[0]).decode('unicode-escape'))
            std_out_log.flush()
            std_err_log.flush()
            cmd_popen_arg = shlex.split(cmd[0])
            p = subprocess.Popen(cmd_popen_arg, stdout=std_out_log, stderr=std_err_log)
            p.wait()
            if p.returncode != 0:
                ret_code = 1
                std_out_log.flush()
                std_err_log.flush()
                break
            else:
                print cmd[0] + '  return zero '
    if  ret_code==1:
        raise subprocess.CalledProcessError
    return 0


if __name__ == "__main__":
    main()
