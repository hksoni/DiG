# ***** BEGIN LICENSE BLOCK *****
# DiG: Data centers in the Grid
# Copyright (C) 2015-2016, INRIA.
# 
# This work was partially supported by the ANR Reflexion Project (ANR-14-CE28-0019).
# The authors alone are responsible for this work.
#
# See the file AUTHORS for details and contact information.
# 
# This file is part of DiG (Data centers in the Grid Tool).
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License Version 3 or later
# (the "GPL"), or the GNU Lesser General Public License Version 3 or later
# (the "LGPL") as published by the Free Software Foundation.
#
# DiG is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# or the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU General Public License and
# GNU Lesser General Public License along with DiG; see the file
# COPYING. If not, see <http://www.gnu.org/licenses/>.
#
# ***** END LICENSE BLOCK ***** */
#Author: Hardik Soni <hardik.soni@inria.fr>

#!/usr/bin/python

import time
import sys
import os
import subprocess, shlex
from random import randint
from symbol import arglist

def main(argv):
    if len(argv) != 1:
        print 'input file not provided'
        return
    fname = argv[0]
    if not os.path.isfile(fname):
        print 'file not found'
        return 
    with open(fname) as f:
        lines = [x.strip('\n') for x in f.readlines()]
    for line in lines:
        func_args = shlex.split(line)
        execute_function(func_args[0], func_args[1:])


def execute_function(func_name, arg_list):
    if (func_name == 'delete_container'):
        delete_container(arg_list[0], arg_list[1])
    elif (func_name == 'delete_tunnel_endpoint'):
        delete_tunnel_endpoint(arg_list[0], arg_list[1], arg_list[2])
    else:
        print 'unknown function : ' + func_name

def delete_container(container, disk_io):
    cmds = []
    if(disk_io != '0,0'):
        disk_part = disk_io.split(",")[0]
        docker_umount_cmd = 'docker exec -it -u hadoop '+container+\
            ' sudo umount '+disk_part
        cmds.append([docker_umount_cmd, 'wait'])
    docker_stop_cmd = 'docker stop ' +  container
    docker_rm_cmd = 'docker rm ' +  container
    cmds.append([docker_stop_cmd, 'wait'])
    cmds.append([docker_rm_cmd, 'wait'])
    execute_process(cmds)

def delete_tunnel_endpoint(sId, tunId, intf):
    cmds = []
    del_session_cmd = 'ip l2tp del session tunnel_id ' + tunId + ' session_id ' + sId
    del_tunnel_cmd = 'ip l2tp del tunnel tunnel_id ' + tunId
    cmds.append([del_session_cmd, 'wait'])
    cmds.append([del_tunnel_cmd, 'wait'])
    execute_process(cmds)
    
def execute_process(cmds):
    for cmd in cmds:
        print cmd[0]
        cmd_popen_arg = shlex.split(cmd[0])
        wait_arg = cmd[1]
        p = subprocess.Popen(cmd_popen_arg)
        if (wait_arg == 'wait'):
            print '----'
            p.wait()
        else:
            time.sleep(3)

if __name__ == "__main__":
    main(sys.argv[1:])
