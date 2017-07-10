#
# ***** BEGIN LICENSE BLOCK *****
# DiG: Data centers in the Grid
# Copyright (C) 2015-2016, INRIA.
# 
# This work was partially supported by the ANR Reflexion Project (ANR-14-CE28-0019).
# The authors alone are responsible for this work.
#
# See the file AUTHORS for details and contact information.
# 
# This file is a part of DiG (Data centers in the Grid Tool).
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
# Author: Hardik Soni <hardik.soni@inria.fr>

#!/usr/bin/python

import time
import sys
import os
import subprocess
import shlex
import io
from random import randint
from symbol import arglist

std_out_log_file = ''
std_err_log_file = ''

def main(argv):
    global std_out_log_file
    global std_err_log_file
    if len(argv) != 1:
        print("input file not provided")
        return
    fname = argv[0]
    if not os.path.isfile(fname):
        print("file not found")
        return
    std_out_log_file = fname+'.stdout'
    std_err_log_file = fname+'.stderr'
    stop_nm()
    with open(fname) as f:
        lines = [x.strip('\n') for x in f.readlines()]
    for line in lines:
        func_args = shlex.split(line)
        execute_function(func_args[0], func_args[1:])
    start_nm()


def execute_function(func_name, arg_list):
    ret_code = 0
    if (func_name == 'create_partitions'):
        ret_code = create_partitions(arg_list[0], arg_list[1:])
    elif(func_name == 'create_partition_table'):
        ret_code = create_partition_table(arg_list[0], arg_list[1])
    elif (func_name == 'create_virtual_node'):
        ret_code = create_virtual_node(arg_list[0], arg_list[1], arg_list[2], arg_list[3],
                            arg_list[4], arg_list[5], arg_list[6], arg_list[7:])
    elif (func_name == 'create_veth_pair'):
        ret_code = create_veth_pair(arg_list[0], arg_list[1], arg_list[2], arg_list[3])
    elif (func_name == 'create_tunnel_endpoint'):
        create_tunnel_endpoint(arg_list[0], arg_list[1], arg_list[2], arg_list[3], arg_list[4],
                               arg_list[5], arg_list[6], arg_list[7], arg_list[8], arg_list[9])
    elif (func_name == 'launch_ovs_container' ):
        ret_code = launch_ovs_container(arg_list[0], arg_list[1], arg_list[2], arg_list[3],
                                        arg_list[4], arg_list[5], arg_list[6], arg_list[7:])
    # elif(func_name == 'bring_down_if'):
    #     bring_down_if(arg_list[0])
    # elif(func_name == 'bring_up_if'):
    #     bring_up_if(arg_list[0])
    # elif(func_name == 'set_QoS_on_interface'):
    #     set_QoS_on_interface(arg_list[0], arg_list[1])
    else:
        print("unknown function : ' "+ func_name)
    return ret_code;


def pull_docker_image(image_name):
    cmd_str = 'docker pull '+image_name
    cmd_arg = shlex.split(cmd_str)
    ret = subprocess.check_output(cmd_arg)


def create_veth_pair(if1_name, if2_name, mac1, mac2):
    try:
        cmd_str = 'ip link add dev '+if1_name+' type veth peer name '+if2_name
        execute_process([[cmd_str, 'wait']])
        bring_up_if(if1_name)
        bring_up_if(if2_name)
        bring_down_if(if1_name)
        bring_down_if(if2_name)
        set_mac(if1_name, mac1)
        set_mac(if2_name, mac2)
        disable_dhcp_client(if1_name, mac1)
        disable_dhcp_client(if2_name, mac2)
        bring_up_if(if1_name)
        bring_up_if(if2_name)
    except Exception:
        return 1
    finally:
        return 0


def create_tunnel_endpoint(if_name, tid, peer_tid, ip, rip, sport, dport, sid, peer_sid, mac):
    tun_cmd_str = 'ip l2tp add tunnel  tunnel_id ' + tid + ' peer_tunnel_id ' + peer_tid + ' encap udp local ' + ip + \
                  ' remote ' + rip + ' udp_sport ' + sport + ' udp_dport ' + dport
    ses_cmd_str = 'ip l2tp add session name ' + if_name + ' tunnel_id ' + tid + ' session_id ' + sid + \
                  ' peer_session_id ' + peer_sid
    execute_l2tp_cmds([[tun_cmd_str, 'wait'], [ses_cmd_str, 'wait']])
    bring_up_if(if_name)
    time.sleep(2)
    bring_down_if(if_name)
    set_mac(if_name, mac)
    disable_dhcp_client(if_name, mac)
    bring_up_if(if_name)


# def create_session_endpoint(if_name, tid, sid, peer_sid):
#     ses_cmd_str = 'ip l2tp add session name ' + if_name + ' tunnel_id ' + tid \
#     + ' session_id ' + sid + ' peer_session_id ' + peer_sid
#     execute_process([[ses_cmd_str, 'wait']])


def bring_down_if(if_name):
    try:
        cmd_str = 'ip link set '+ if_name +' down'
        execute_process([[cmd_str, 'wait']])
    except Exception as e:
        raise e
    finally:
        return 0


def bring_up_if(if_name):
    try:
        cmd_str = 'ip link set '+ if_name +' up mtu 1460'
        execute_process([[cmd_str, 'wait']])
    except Exception as e:
        raise e
    finally:
        return 0

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate


def launch_ovs_container(image_name, container_name, cpuset, container, dpid, sdn_controller_ip_port, mgmt_port, if_names):
    try:
        ovs_vsctl_log = ' --log-file=/etc/openvswitch/ovs-vsctl.log '
        #ovs_vsctl_log = ' --verbose=off  '
        #ovs_vswitchd_log = ' --log-file=/etc/openvswitch/ovs-vswitchd.log '
        ovs_vswitchd_log = ' --verbose=off  '
        docker_run_cmd = 'docker run --cap-add=NET_ADMIN  --cpuset-cpus="'+cpuset+'" -m 4096m  --name ' + \
        container_name +' -p '+mgmt_port+':6640'+'  -d -it ' + image_name + ' /bin/bash'
        docker_prefix = 'docker exec ' + container_name + ' '
        docker_ovs_daemon_cmd = docker_prefix+ '/root/ovs-script.sh'
        add_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' add-br '+container_name
        protocol_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+'set bridge '+container_name+' protocols=OpenFlow13'
        disa_inband_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+'set bridge '+container_name+' other_config:disable-in-band=true'
        dpid_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' set bridge '+container_name+' other-config:datapath-id='+dpid
        ctrl_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' set-controller '+container_name+' tcp:'+sdn_controller_ip_port
        outband_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' set controller '+container_name+' connection_mode=out-of-band'
        set_manager_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' set-manager ptcp:6640 '
        cmds = [[docker_run_cmd, 'wait'],
                [docker_ovs_daemon_cmd, 'wait'],
                [add_cmd, 'wait'],
                [protocol_cmd, 'wait'],
                [disa_inband_cmd, 'wait'],
                [dpid_cmd, 'wait'],
                [ctrl_cmd,'wait'],
                [outband_cmd, 'wait'],
                [set_manager_cmd, 'wait']
                ]
        execute_process(cmds)
        add_interfaces_ovs_container(ovs_vsctl_log, container_name, if_names)
        if (container != '0,0'):
            ioRate = container.split(',')[1]
            set_container_io_bandwidth(container_name, ioRate)
    except Exception:
        return 1
    finally:
        return 0


def add_interfaces_ovs_container(ovs_vsctl_log, container_name, if_names):
    try:
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
            #flush_qos_cmd = docker_prefix+'tc qdisc del dev  '+intf_data[0]+' root'
            intf_up_cmd = docker_prefix+'ip link set '+intf_data[0]+' up'
            #qos_cmd_str = get_QoS_on_host_interface_string(intf_data[0], intf_data[1])
            #intf_tc_cmd = docker_prefix+' '+qos_cmd_str
            add_intf_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+'add-port '+container_name+' '+intf_data[0]
            ingress_policing_rate_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' set interface '\
                                        +intf_data[0]+' ingress_policing_rate='+intf_data[1]+"000"
            ingress_policing_burst_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' set interface '\
                                         +intf_data[0]+' ingress_policing_burst='+intf_data[1]+"00"
            add_default_qos_queue_cmd = docker_prefix+'ovs-vsctl'+ovs_vsctl_log+' set port '+intf_data[0]\
                                        +' qos=@newqos -- --id=@newqos create qos type=linux-htb other-config:max-rate='\
                                        +intf_data[1]+'000000'+'  queues:0=@vif10queue --'\
                                        +' --id=@vif10queue create queue other-config:max-rate='+intf_data[1]+'000000'\
                                        +' other_config:priority=99999'
            cmds.append([add_intf_ns, 'wait'])
            cmds.append([set_mtu_cmd, 'wait'])
            #cmds.append([flush_qos_cmd, 'wait'])
            cmds.append([intf_up_cmd, 'wait'])
            #cmds.append([intf_tc_cmd, 'wait'])
            cmds.append([add_intf_cmd, 'wait'])
            cmds.append([ingress_policing_rate_cmd, 'wait'])
            cmds.append([ingress_policing_burst_cmd, 'wait'])
            cmds.append([add_default_qos_queue_cmd, 'wait'])
        execute_process(cmds)
    except Exception as e:
        raise e
    finally:
        return 0


def create_virtual_node(image_name, container_name, cpuset, storage, container, hostname, no_of_slaves, intfs):
    try:
        device_arg = ' '
        storage_io_rate = ''
        storage_partition = ''
        output_dir = '/root/'+hostname+'-out'
        output_arg = ' -v '+output_dir+':'+output_dir+' '
        if storage != '0,0':
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
        cmds = [[docker_virtual_host_startup_cmd, 'wait'],
                [docker_virtual_host_add_hadoop_slaves_cmd, 'wait'],
                ]
        execute_process(cmds)
        #start_tcpdump(container_name, intfs, output_dir)
    except Exception:
        return 1
    finally:
        return 0


def allocate_disk_partition_to_virtual_node(container_name, partition, ioRate):
    try:
        disk = partition[:-1]
        docker_hadoop_user_prefix = 'docker exec -u hadoop ' + container_name + ' '
        mount_cmd = docker_hadoop_user_prefix+' sudo mount '+partition+' /home/hadoop/hadoop-2.6.0/hadoop_store'
        chown_cmd = docker_hadoop_user_prefix+' sudo chown hadoop /home/hadoop/hadoop-2.6.0/hadoop_store'
        cmds = [[mount_cmd, 'wait'], [chown_cmd, 'wait']]
        execute_process(cmds)
        set_disk_io_bandwidth(container_name, disk, ioRate)
    except Exception as e:
        raise e
    finally:
        return 0


def add_interfaces_host_container(container_name, if_names):
    try:
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
            qos_cmd_str = get_QoS_on_host_interface_string(intf_data[0], intf_data[3])
            intf_tc_cmd = docker_prefix+' ' +qos_cmd_str
            ip = intf_data[1].split('/')
            default_gw_cmd_str = docker_prefix+'route add default gw ' + ip[0]
            cmds.append([add_intf_ns, 'wait'])
            cmds.append([intf_down, 'wait'])
            cmds.append([set_mtu_cmd, 'wait'])
            cmds.append([flush_ip_cmd, 'wait'])
            cmds.append([assign_ip_cmd, 'wait'])
            #cmds.append([flush_qos_cmd, 'wait'])
            cmds.append([intf_up_cmd, 'wait'])
            cmds.append([intf_tc_cmd, 'wait'])
            cmds.append([default_gw_cmd_str, 'wait'])
        execute_process(cmds)
    except Exception as e:
        raise e
    finally:
        return 0


def set_container_io_bandwidth(container_name, diskiobw):
    try:
        cmds = []
        docker_prefix = 'docker exec ' + container_name + ' '
        cpid = get_container_process_id(container_name)
        container_fs_mount_cmd ='nsenter --target '+cpid+' --mount --uts --ipc --net --pid mount'
        fs_cmd_popen_arg = shlex.split(container_fs_mount_cmd)
        ret_fs = subprocess.check_output(fs_cmd_popen_arg)
        fs_mount = ret_fs.split('\n')[0].split(' ')[0]
        runtime = fs_mount.split('-')
        docker_mount_scope = runtime[-1]
        print(docker_mount_scope)
        set_property_cmd = 'systemctl set-property --runtime docker-'+docker_mount_scope+\
        '.scope "BlockIOWriteBandwidth='+fs_mount+' '+diskiobw+'M" "BlockIOReadBandwidth='+fs_mount+' '+diskiobw+'M"'
        cmds.append([set_property_cmd, 'wait'])
        execute_process(cmds)
    except Exception as e:
        raise e
    finally:
        return 0


def create_partition_table(diskId, tableType):
    try:
        mklabel_cmd = 'parted -a opt  -s '+diskId+'   mklabel '+tableType
        cmds = [[mklabel_cmd, 'wait']]
        return execute_process(cmds)
    except Exception:
        return 1
    finally:
        return 0


def create_partitions(diskId, partitions):
    try:
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
    except Exception:
        return 1
    finally:
        return 0


def set_disk_io_bandwidth(container_name, disk, diskiobw):
    try:
        cmds = []
        cpid = get_container_process_id(container_name)
        container_fs_mount_cmd ='nsenter --target '+cpid+' --mount --uts --ipc --net --pid mount'
        fs_cmd_popen_arg = shlex.split(container_fs_mount_cmd)
        ret_fs = subprocess.check_output(fs_cmd_popen_arg)
        fs_mount = ret_fs.split('\n')[0].split(' ')[0]
        runtime = fs_mount.split('-')
        docker_mount_scope = runtime[-1]
        set_property_cmd = 'systemctl set-property --runtime docker-'+docker_mount_scope+\
        '.scope "BlockIOWriteBandwidth='+disk+' '+diskiobw+'M" "BlockIOReadBandwidth='+disk+' '+diskiobw+'M"'
        cmds.append([set_property_cmd, 'wait'])
        execute_process(cmds)
    except Exception as e:
        raise e
    finally:
        return 0

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
        cmds.append([tcpdump_cmd, 'wait'])
        #cmds.append([tcpdump_cmd, 'nowait'])
    execute_process(cmds)


def set_mac(ifname, mac):
    try:
        set_mac_cmd = 'ip link set '+ifname+' address ' + mac
        execute_process([[set_mac_cmd,'wait']])
    except Exception as e:
        raise e
    finally:
        return 0


def set_QoS_on_interface(if_name, rate):
#    hz_cmd = 'egrep '^CONFIG_HZ_[0-9]+' /boot/config-`uname -r` | cut -d "=" -f 1 | cut -d "_" -f 3'
#    burst = int(rate)/1000 (rate*10^6/10^3)b = rate kb
    cmd_str = 'tc qdisc add dev ' + if_name +' root tbf rate '+rate+'mbit burst 10kb latency 10ms'
    execute_process([[cmd_str,'wait']])


def get_QoS_on_host_interface_string(if_name, rate):
#    hz_cmd = 'egrep '^CONFIG_HZ_[0-9]+' /boot/config-`uname -r` | cut -d "=" -f 1 | cut -d "_" -f 3'
    #burst = int(rate)/1000 (rate*10^6/10^3)b = rate kb
    burst = int(rate)*1000/100
    cmd_str = 'tc qdisc add dev ' + if_name +' root tbf rate '+rate+'mbit burst '+str(burst)+'kb latency 10ms'
    return cmd_str

def execute_l2tp_cmds(cmds):
    ret_code = 0
    with io.open(std_out_log_file, 'a') as std_out_log, \
            io.open(std_err_log_file, 'a') as std_err_log:
        for cmd in cmds:
            std_out_log.write(str(cmd[0]+'\n').decode('unicode-escape'))
            std_err_log.write(str(cmd[0]+'\n').decode('unicode-escape'))
            std_out_log.flush()
            std_err_log.flush()
            cmd_popen_arg = shlex.split(cmd[0])
            p = subprocess.Popen(cmd_popen_arg, stdout=std_out_log, stderr=std_err_log)
            p.wait()
            ret = str(p.returncode) + '\n'
            std_out_log.write(ret.decode('unicode-escape'))
            std_out_log.flush()
    return 0

def execute_process(cmds):
    ret_code = 0
    with io.open(std_out_log_file, 'a') as std_out_log, \
            io.open(std_err_log_file, 'a') as std_err_log:
        for cmd in cmds:
            std_out_log.write(str(cmd[0]+'\n').decode('unicode-escape'))
            std_err_log.write(str(cmd[0]+'\n').decode('unicode-escape'))
            std_out_log.flush()
            std_err_log.flush()
            cmd_popen_arg = shlex.split(cmd[0])
            p = subprocess.Popen(cmd_popen_arg, stdout=std_out_log, stderr=std_err_log)
            p.wait()
            ret = str(p.returncode) + '\n'
            std_out_log.write(ret.decode('unicode-escape'))
            if p.returncode != 0:
                ret_code = 1
                temp_msg = 'Inside return code is non-zero\n'
                std_out_log.write(temp_msg.decode('unicode-escape'))
                std_out_log.flush()
                std_err_log.flush()
                break
    if  ret_code == 1:
        raise subprocess.CalledProcessError
    return 0


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
