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
    return
    if len(argv) != 1:
        print 'input file not provided'
        return
    fname = argv[0]
    if not os.path.isfile(fname):
        print 'file not found'
        return 
    stop_nm()
    with open(fname) as f:
        lines = [x.strip('\n') for x in f.readlines()]
    for line in lines:
        func_args = shlex.split(line)
        execute_function(func_args[0], func_args[1:])
    start_nm()


def execute_function(func_name, arg_list):
    if (func_name == 'create_partitions'):
        create_partitions(arg_list[0], arg_list[1:])
    elif(func_name == 'create_partition_table'):
        create_partition_table(arg_list[0], arg_list[1])
    elif (func_name == 'create_virtual_node'):
        create_virtual_node(arg_list[0], arg_list[1], arg_list[2], arg_list[3], \
                            arg_list[4], arg_list[5], arg_list[6], arg_list[7:])
    elif (func_name == 'create_veth_pair'):
        create_veth_pair(arg_list[0], arg_list[1], arg_list[2], arg_list[3])
    elif (func_name == 'create_tunnel_endpoint'):
        create_tunnel_endpoint(arg_list[0], arg_list[1], arg_list[2], arg_list[3], arg_list[4], \
                               arg_list[5], arg_list[6], arg_list[7], arg_list[8], arg_list[9])
    elif (func_name == 'launch_ovs_container' ):
        launch_ovs_container(arg_list[0], arg_list[1], arg_list[2], arg_list[3], arg_list[4], arg_list[5], arg_list[6:])
    elif(func_name == 'bring_down_if'):
        bring_down_if(arg_list[0])
    elif(func_name == 'bring_up_if'):
        bring_up_if(arg_list[0])
    elif(func_name == 'set_QoS_on_interface'):
        set_QoS_on_interface(arg_list[0], arg_list[1])
    else:
        print 'unknown function : ' + func_name
    

def pull_docker_image(image_name):
    cmd_str = 'docker pull '+image_name
    cmd_arg = shlex.split(cmd_str)
    ret = subprocess.check_output(cmd_arg)


def create_veth_pair(if1_name, if2_name, mac1, mac2):
    cmd_str = 'ip link add dev '+if1_name+' type veth peer name '+if2_name
    execute_process([[cmd_str, 'wait']])
    bring_up_if(if1_name)
    bring_up_if(if2_name)
    time.sleep(2)
    bring_down_if(if1_name)
    bring_down_if(if2_name)
    set_mac(if1_name, mac1)
    set_mac(if2_name, mac2)
    disable_dhcp_client(if1_name, mac1)
    disable_dhcp_client(if2_name, mac2)
    bring_up_if(if1_name)
    bring_up_if(if2_name)


def create_tunnel_endpoint(if_name, tid, peer_tid, ip, rip, sport, dport, sid, peer_sid, mac):
    cmd_str = 'ip l2tp add tunnel  tunnel_id ' + tid \
    + ' peer_tunnel_id ' + peer_tid + ' encap udp local ' + ip + ' remote ' + \
    rip + ' udp_sport ' + sport + ' udp_dport ' + dport
    execute_process([[cmd_str, 'wait']])
    create_session_endpoint(if_name, tid, sid, peer_sid)
    bring_up_if(if_name)
    time.sleep(2)
    bring_down_if(if_name)
    set_mac(if_name, mac)
    disable_dhcp_client(if_name, mac)
    bring_up_if(if_name)


def create_session_endpoint(if_name, tid, sid, peer_sid):
    cmd_str = 'ip l2tp add session name ' + if_name + ' tunnel_id ' + tid \
    + ' session_id ' + sid + ' peer_session_id ' + peer_sid 
    execute_process([[cmd_str, 'wait']])


def bring_down_if(if_name):
    cmd_str = 'ip link set '+ if_name +' down'
    execute_process([[cmd_str, 'wait']])


def bring_up_if(if_name):
    cmd_str = 'ip link set '+ if_name +' up mtu 1460'
    execute_process([[cmd_str, 'wait']])


def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate


def launch_ovs_container(image_name, container_name, cpuset, container, dpid, sdn_controller_ip_port, if_names):
    ovs_vsctl_log = ' --log-file=/etc/openvswitch/ovs-vsctl.log '
    ovs_vswitchd_log = ' --log-file=/etc/openvswitch/ovs-vswitchd.log '
    docker_run_cmd = 'docker run --cap-add=NET_ADMIN  --cpuset-cpus="'+cpuset+'" -m 4096m  --name '+ \
    container_name+'  -d -it '+image_name+' /bin/bash'
    docker_prefix = 'docker exec ' + container_name + ' '
    docker_ovs_daemon_cmd = docker_prefix+ '/root/ovs-script.sh'
    add_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' add-br '+container_name
    protocol_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+'set bridge '+container_name+' protocols=OpenFlow10'
    disa_inband_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+'set bridge '+container_name+' other_config:disable-in-band=true' 
    dpid_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' set bridge '+container_name+' other-config:datapath-id='+dpid
    ctrl_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' set-controller '+container_name+' tcp:'+sdn_controller_ip_port
    outband_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' set controller '+container_name+' connection_mode=out-of-band'
    cmds = [[docker_run_cmd, 'wait'], \
            [docker_ovs_daemon_cmd, 'wait'], \
            [add_cmd, 'wait'], \
            [protocol_cmd, 'wait'], \
            [disa_inband_cmd, 'wait'], \
            [dpid_cmd, 'wait'], \
            [ctrl_cmd,'wait'], \
            [outband_cmd, 'wait'] \
            ]
    execute_process(cmds)
    add_interfaces_ovs_container(ovs_vsctl_log, container_name, if_names)
    if (container != '0,0'):
        ioRate = container.split(',')[1]
        set_container_io_bandwidth(container_name, ioRate)


def add_interfaces_ovs_container(ovs_vsctl_log, container_name, if_names):
    cmds = []
    docker_prefix = 'docker exec ' + container_name + ' '
    container_pid_cmd = 'docker inspect -f \'{{.State.Pid}}\'  '+ container_name
    cmd_popen_arg = shlex.split(container_pid_cmd)
    ret = subprocess.check_output(cmd_popen_arg) 
    cpid = ret.strip('\n')
    for interface in if_names:
        intf_data = interface.split(',')
        add_intf_ns = 'ip link set netns '+cpid+'  dev  '+intf_data[0]
        set_mtu_cmd = docker_prefix+'ip link set '+intf_data[0]+' mtu 1460'
        flush_qos_cmd = docker_prefix+'tc qdisc del dev  '+intf_data[0]+' root'
        intf_up_cmd = docker_prefix+'ip link set '+intf_data[0]+' up' 
        qos_cmd_str = get_QoS_on_interface_string(intf_data[0], intf_data[1])
        intf_tc_cmd = docker_prefix+' '+qos_cmd_str
        add_intf_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+'add-port '+container_name+' '+intf_data[0]
        cmds.append([add_intf_ns, 'wait'])
        cmds.append([set_mtu_cmd, 'wait'])
        cmds.append([flush_qos_cmd, 'wait'])
        cmds.append([intf_up_cmd, 'wait'])
        cmds.append([intf_tc_cmd, 'wait'])
        cmds.append([add_intf_cmd, 'wait'])
    execute_process(cmds)


def create_virtual_node(image_name, container_name, cpuset, storage, container, hostname, no_of_slaves, intfs):
    device_arg = ' '
    storage_io_rate = ''
    storage_partition = ''
    output_dir = '/root/'+hostname+'-out'
    output_arg = ' -v '+output_dir+':'+output_dir+' '
    if (storage != '0,0'):
        store = storage.split(',')
        storage_partition = store[0]
        storage_io_rate = store[1]
        device_arg = ' --cap-add=SYS_ADMIN --device='+storage_partition+' '
    docker_run_cmd = 'docker run --cap-add=NET_ADMIN'+device_arg+output_arg+' --net=none --cpuset-cpus="'+cpuset+\
                     '" -m 8192m --name '+ container_name+' -d -it '+image_name+' /bin/bash'
    docker_prefix = 'docker exec ' + container_name + ' '
    docker_hadoop_user_prefix = 'docker exec -u hadoop ' + container_name + ' '
    docker_virtual_host_startup_cmd = docker_prefix+ '/root/startup-script.sh ' +hostname
    docker_virtual_host_add_hadoop_slaves_cmd = docker_hadoop_user_prefix+ '/home/hadoop/add-slaves.sh ' +no_of_slaves
    execute_process([[docker_run_cmd, 'wait']])
    add_interfaces_host_container(container_name, intfs)
    if (container != '0,0'):
        ioRate = container.split(',')[1]
	set_container_io_bandwidth(container_name, ioRate)
    if (storage != '0,0'):
        allocate_disk_partition_to_virtual_node(container_name, storage_partition, storage_io_rate)
    cmds = [[docker_virtual_host_startup_cmd, 'wait'], \
            [docker_virtual_host_add_hadoop_slaves_cmd, 'wait'], \
            ]
    execute_process(cmds)
    #start_tcpdump(container_name, intfs, output_dir)
 

def allocate_disk_partition_to_virtual_node(container_name, partition, ioRate):
    disk = partition[:-1]
    docker_hadoop_user_prefix = 'docker exec -u hadoop ' + container_name + ' '
    mount_cmd = docker_hadoop_user_prefix+' sudo mount '+partition+' /home/hadoop/hadoop-2.6.0/hadoop_store'
    chown_cmd = docker_hadoop_user_prefix+' sudo chown hadoop /home/hadoop/hadoop-2.6.0/hadoop_store'
    cmds = [[mount_cmd, 'wait'], [chown_cmd, 'wait']]
    execute_process(cmds)
    set_disk_io_bandwidth(container_name, disk, ioRate)


def add_interfaces_host_container(container_name, if_names):
    cmds = []
    docker_prefix = 'docker exec ' + container_name + ' '
    cpid = get_container_process_id(container_name)
    for interface in if_names:
        intf_data = interface.split(',')
        add_intf_ns = 'ip link set netns '+cpid+'  dev  '+intf_data[0]
        intf_down = docker_prefix+'ip link set '+intf_data[0]+' down'
        set_mtu_cmd = docker_prefix+'ip link set '+intf_data[0]+' mtu 1460'
        flush_ip_cmd = docker_prefix+'ip addr flush dev '+intf_data[0]
        assign_ip_cmd = docker_prefix+'ip addr add ' + intf_data[1] + ' dev '+intf_data[0]+' broadcast '+ intf_data[2]
        flush_qos_cmd = docker_prefix+'tc qdisc del dev  '+intf_data[0]+' root'
        intf_up_cmd = docker_prefix+'ip link set '+intf_data[0]+' up' 
        qos_cmd_str = get_QoS_on_interface_string(intf_data[0], intf_data[3])
        intf_tc_cmd = docker_prefix+' ' +qos_cmd_str
        cmds.append([add_intf_ns, 'wait'])
        cmds.append([intf_down, 'wait'])
        cmds.append([set_mtu_cmd, 'wait'])
        cmds.append([flush_ip_cmd, 'wait'])
        cmds.append([assign_ip_cmd, 'wait'])
        cmds.append([flush_qos_cmd, 'wait'])
        cmds.append([intf_up_cmd, 'wait'])
        cmds.append([intf_tc_cmd, 'wait'])
    execute_process(cmds)


def set_container_io_bandwidth(container_name, diskiobw):
    cmds = []
    docker_prefix = 'docker exec ' + container_name + ' '
    cpid = get_container_process_id(container_name)
    container_fs_mount_cmd ='nsenter --target '+cpid+' --mount --uts --ipc --net --pid mount'
    fs_cmd_popen_arg = shlex.split(container_fs_mount_cmd)
    ret_fs = subprocess.check_output(fs_cmd_popen_arg)
    fs_mount = ret_fs.split('\n')[0].split(' ')[0]
    runtime = fs_mount.split('-')
    docker_mount_scope = runtime[-1]
    print docker_mount_scope
    set_property_cmd = 'systemctl set-property --runtime docker-'+docker_mount_scope+\
    '.scope "BlockIOWriteBandwidth='+fs_mount+' '+diskiobw+'M" "BlockIOReadBandwidth='+fs_mount+' '+diskiobw+'M"'
    cmds.append([set_property_cmd, 'wait'])
    execute_process(cmds)


def create_partition_table(diskId, tableType):
    mklabel_cmd = 'parted -a opt  -s '+diskId+'   mklabel '+tableType
    cmds = [[mklabel_cmd, 'wait']]
    execute_process(cmds)


def create_partitions(diskId, partitions):
    mkpart_prefix = 'parted -a opt  -s '+diskId +' mkpart ext4 '
    cmds = []
    partition_number = 1
    for part in partitions:
       part_data = part.split(',')
       mkpart_cmd = mkpart_prefix+part_data[0]+' '+part_data[1]
       mkfs_cmd = 'mkfs.ext4 -F '+diskId+str(partition_number)
       cmds.append([mkpart_cmd, 'wait'])
       cmds.append([mkfs_cmd, 'wait'])
       partition_number = partition_number + 1
    execute_process(cmds)

def set_disk_io_bandwidth(container_name, disk, diskiobw):
    cmds = []
    docker_prefix = 'docker exec ' + container_name + ' '
    cpid = get_container_process_id(container_name)
    container_fs_mount_cmd ='nsenter --target '+cpid+' --mount --uts --ipc --net --pid mount'
    fs_cmd_popen_arg = shlex.split(container_fs_mount_cmd)
    ret_fs = subprocess.check_output(fs_cmd_popen_arg)
    fs_mount = ret_fs.split('\n')[0].split(' ')[0]
    runtime = fs_mount.split('-')
    docker_mount_scope = runtime[-1]
    print docker_mount_scope
    set_property_cmd = 'systemctl set-property --runtime docker-'+docker_mount_scope+\
    '.scope "BlockIOWriteBandwidth='+disk+' '+diskiobw+'M" "BlockIOReadBandwidth='+disk+' '+diskiobw+'M"'
    cmds.append([set_property_cmd, 'wait'])
    execute_process(cmds)
    

def get_container_process_id(container_name):
    container_pid_cmd = 'docker inspect -f \'{{.State.Pid}}\'  '+ container_name
    cmd_popen_arg = shlex.split(container_pid_cmd)
    ret = subprocess.check_output(cmd_popen_arg)
    cpid = ret.strip('\n')
    return cpid


def start_tcpdump(container_name, if_names, output_dir):
    docker_prefix = 'docker exec -d ' + container_name + ' '
    cmds = []
    for interface in if_names:
        intf_name = interface.split(',')[0]
        tcpdump_cmd = docker_prefix+' tcpdump -i '+ intf_name+' -s 80 --time-stamp-precision=nano -e  -w '+ output_dir+'/'+intf_name+'.pcap'
        cmds.append([tcpdump_cmd, 'nowait'])
    execute_process(cmds)


def set_mac(ifname, mac):
    set_mac_cmd = 'ip link set '+ifname+' address ' + mac
    execute_process([[set_mac_cmd,'wait']])


def set_QoS_on_interface(if_name, rate):
#    hz_cmd = 'egrep '^CONFIG_HZ_[0-9]+' /boot/config-`uname -r` | cut -d "=" -f 1 | cut -d "_" -f 3'
    #burst = int(rate)/1000 (rate*10^6/10^3)b = rate kb
    cmd_str = 'tc qdisc add dev ' + if_name +' root tbf rate '+rate+'mbit burst 10kb latency 10ms'
    execute_process([[cmd_str,'wait']])


def get_QoS_on_interface_string(if_name, rate):
#    hz_cmd = 'egrep '^CONFIG_HZ_[0-9]+' /boot/config-`uname -r` | cut -d "=" -f 1 | cut -d "_" -f 3'
    #burst = int(rate)/1000 (rate*10^6/10^3)b = rate kb
    burst = int(rate)*1000/100
    cmd_str = 'tc qdisc add dev ' + if_name +' root tbf rate '+rate+'mbit burst '+str(burst)+'kb latency 10ms'
    return cmd_str




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


#TODO: handle p here log results of blocking processes 
#TODO: maintain list of backgroung processes and poll on them. 
#python equivalent of pthread_join 

def disable_dhcp_client(if_name, mac):
    path = '/etc/sysconfig/network-scripts/ifcfg-'+if_name
    with open(path, 'w') as file:
        file.write('NM_CONTROLLED=no'+'\n')
        file.write('HWADDR='+mac+'\n')


def stop_nm():
    cmd_str = 'systemctl stop  NetworkManager.service'
    execute_process([[cmd_str,'wait']])


def start_nm():
    cmd_str = 'systemctl start  NetworkManager.service'
    execute_process([[cmd_str,'wait']])


if __name__ == "__main__":
    main(sys.argv[1:])
