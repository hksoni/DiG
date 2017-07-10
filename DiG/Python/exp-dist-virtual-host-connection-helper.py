# ***** begin license block *****
# dig: data centers in the grid
# copyright (c) 2015-2016, inria.
#
# this work was partially supported by the anr reflexion project (anr-14-ce28-0019).
# the authors alone are responsible for this work.
#
# see the file authors for details and contact information.
#
# this file is part of dig (data centers in the grid tool).
#
# this program is free software; you can redistribute it and/or modify it
# under the terms of the gnu general public license version 3 or later
# (the "gpl"), or the gnu lesser general public license version 3 or later
# (the "lgpl") as published by the free software foundation.
#
# dig is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose.  see the gnu general public license
# or the gnu lesser general public license for more details.
#
# you should have received a copy of the gnu general public license and
# gnu lesser general public license along with dig; see the file
# copying. if not, see <http://www.gnu.org/licenses/>.
#
# ***** end license block ***** */
# author: hardik soni <hardik.soni@inria.fr>

#!/usr/bin/python

from pexpect import pxssh
from pexpect import *
import pexpect
import json
import time
from time import gmtime, strftime
import sys
import os
import io
import signal
import argparse
import threading
import networkx as nx
import subprocess, shlex
import select
import numpy as np
from os import system as cmd

class NetworkMappingHelper:

    def __init__(self, physical_net_f, virtual_net_f, node_mappings_file):
        self.phy_g = nx.read_dot(physical_net_f)
        self.virt_g = nx.read_dot(virtual_net_f)
        self.virtual_phy_map = self.get_mapping_dict_from_file(node_mappings_file)
        self.virtual_phy_ip_map = {}
        self.virtual_node_index_dict = {}
        for vh,ph in self.virtual_phy_map.iteritems():
            str_ip = self.phy_g.node[ph]['ip']
            str_ip = str.replace(str_ip, "\"", "")
            self.virtual_phy_ip_map[vh] = str_ip

    def get_mapping_dict_from_file(self, mapping_file):
        virtual_phy = {}
        node_map = {}
        try:
            with open(mapping_file) as f:
                lines = [x.strip('\n') for x in f.readlines()]
            for line in lines:
                nodes = line.split('-')
                virt_nodes = []
                virt = nodes[1].strip().split(',')
                phy_node = nodes[0].strip()
                for n in virt:
                    n = n.strip()
                    virt_nodes.append(n)
                    virtual_phy[n] = phy_node
                node_map[phy_node] = virt_nodes
        except Exception as e:
            print ('error in reading file named ' + mapping_file)
            sys.exit(1)
        return virtual_phy

    def get_physical_ip(self, vh):
        return self.virtual_phy_ip_map[vh]

    def get_no_of_virtual_host(self):
        num = 0
        for vn, vnd in self.virt_g.nodes_iter(data=True):
            if vnd['type']=="host":
                self.virtual_node_index_dict[num+1] = vn
                num = num + 1
        return num

    def get_virtual_host_name(self, index):
        return  self.virtual_node_index_dict[index]
        # return  self.virt_g.node[self.virtual_node_index_dict[index]]


class VirtualHostExecution:

    def __init__(self, virtual_host, phy_host_ip):
        self.virtual_host = virtual_host
        self.phy_host_ip = phy_host_ip
        self.lock = threading.Lock()
        self.virtual_host_fd_process_map = {}
        self.virtual_host_id_process_map = {}

    def execute(self, command_id, command, file_part):
        std_out_log_file = self.virtual_host+"-"+file_part+".out"
        docker_cmd = '  docker exec -it '+ self.virtual_host + ' /bin/bash '
        remote_virtual_host_command = self.virtual_host  + ' ' + command_id
        std_out_log = io.open(std_out_log_file, 'a', encoding='utf-8')
        process = pexpect.spawnu('ssh -t  root' + '@' + self.phy_host_ip + docker_cmd,
                                 logfile=std_out_log)
        process.expect(str('#').decode('unicode-escape'))
        process.sendline(command)
        self.lock.acquire()
        try:
            # code for debugging
            self.virtual_host_fd_process_map[command_id] = [remote_virtual_host_command]
            self.virtual_host_id_process_map[command_id] = [std_out_log, process]
        finally:
            self.lock.release()

    def terminate(self, command_id):
        self.lock.acquire()
        try:
            # code for debugging
            pstr = str(self.virtual_host_fd_process_map[command_id])
            print("Terminate : " + pstr)
            [std_out_log, process] = self.virtual_host_id_process_map[command_id]
        finally:
            self.lock.release()
        process.sendcontrol(str('c').decode('unicode-escape'))
        try:
            process.expect(str('#').decode('unicode-escape'), 2)
        except TIMEOUT:
            process.sendcontrol(str('c').decode('unicode-escape'))
            try:
                process.expect(str('#').decode('unicode-escape'), 2)
            except TIMEOUT:
                process.terminate()
        std_out_log.close()
        print("TERMINATED : " + pstr)

    # def execute(self, command_id, command, file_part):
    #     std_out_log_file = self.virtual_host+"-"+file_part+".out"
    #     std_err_log_file = self.virtual_host+"-"+file_part+".err"
    #     docker_cmd = ' docker exec -i '+ self.virtual_host + ' ' + command
    #     remote_virtual_host_command = ' ssh  root' + '@' + self.phy_host_ip + ' exec ' + docker_cmd
    #     print(remote_virtual_host_command)
    #     cmd_popen_arg = shlex.split(remote_virtual_host_command)
    #     with io.open(std_out_log_file, 'a') as std_out_log, \
    #             io.open(std_err_log_file, 'a') as std_err_log:
    #         std_out_log.write(str(remote_virtual_host_command).decode('unicode-escape'))
    #         std_err_log.write(str(remote_virtual_host_command).decode('unicode-escape'))
    #         std_out_log.flush()
    #         std_err_log.flush() #stdin=subprocess.PIPE
    #         process = subprocess.Popen(remote_virtual_host_command, shell=True, stdin=subprocess.PIPE, stdout=std_out_log, stderr=std_err_log)
    #         self.lock.acquire()
    #         try:
    #             # code for debugging
    #             self.virtual_host_fd_process_map[command_id] = [remote_virtual_host_command]
    #             self.virtual_host_id_process_map[command_id] = [std_out_log, process]
    #         finally:
    #             self.lock.release()
    #
    # def terminate(self, command_id):
    #     self.lock.acquire()
    #     try:
    #         # code for debugging
    #         pstr = str(self.virtual_host_fd_process_map[command_id])
    #         print("Terminate : " + pstr)
    #         [fd, process] = self.virtual_host_id_process_map[command_id]
    #         process.communicate('^C\n\r^C\n0x03')
    #         # process.terminate()
    #         print("TERMINATED : " + pstr)
    #     finally:
    #         self.lock.release()



class GroupExecution:

    def __init__(self, gr_ip, gr_bw, mem_ia_rd_list, vh_executor_dict):
        self.group_ip = gr_ip
        self.rec_thread_list = []
        self.bw = gr_bw
        self.mem_ia_rd_l = mem_ia_rd_list
        self.vh_exer_dict = vh_executor_dict
        self.sender_command = "iperf -l 1400  -c "+self.group_ip+" -u -b "+self.bw+"k -f m -i 3 -t 1200"
        self.receiver_command = "iperf -s -B "+self.group_ip+" -u -f m -i 3"

    def get_str_time(self):
        localtime = time.localtime(time.time())
        time_part = str(localtime.tm_hour) + "_"+ \
                    str(localtime.tm_min) + "_" + \
                    str(localtime.tm_sec)
        return time_part

    def run_group(self):
        [src_vh, ia, sr] = self.mem_ia_rd_l.pop(0)

        # start group sources
        virtual_host_executor_sender = self.vh_exer_dict[src_vh]
        virtual_host_executor_sender.execute(self.group_ip, self.sender_command,
                                             self.group_ip+"_s_"+self.get_str_time())
        #starting a timer thread to terminate the sender
        # t_s = threading.Timer(6000, virtual_host_executor.terminate, [self.group_ip])
        # t_s.start()
        for vh, ia, rd in self.mem_ia_rd_l:
            # print("waiting for " + str(ia) + " - group rece " + str(self.group_ip))
            time.sleep(ia) # waiting for inter-arrival time to pass
            #start receiver for rd seconds
            virtual_host_executor_receiver = self.vh_exer_dict[vh]
            virtual_host_executor_receiver.execute(self.group_ip, self.receiver_command,
                                                   self.group_ip+"_r_"+self.get_str_time())
            t_r = threading.Timer(rd, virtual_host_executor_receiver.terminate, [self.group_ip])
            t_r.start()
            self.rec_thread_list.append(t_r)
        for tr in self.rec_thread_list:
            tr.join()
        virtual_host_executor_sender.terminate(self.group_ip)
        print("end of run group " + str(self.group_ip))


def main(physical_net_f, virtual_net_f, node_mappings_file, bw_map_file, exe_schedule, sender_schedule, num_groups):
    nh = NetworkMappingHelper(physical_net_f, virtual_net_f, node_mappings_file)
    group_ip_baw_dict = get_group_bw_dict(bw_map_file)
    print(group_ip_baw_dict)
    virtual_host_executor_dict = {}
    group_sender_inter_arrival_rate = 5
    inter_arrival_rate = 6
    recepation_duration_rate = 60
    group_mem_ia_rd = {}
    no_of_groups = 10
    if (num_groups is not None):
        no_of_groups = int(num_groups)
    group_threads_list = []
    # experiment interval
    no_virt_host = nh.get_no_of_virtual_host()
    if sender_schedule is None:
        group_sender_inter_arrival = np.random.exponential(group_sender_inter_arrival_rate, no_of_groups)
    else:
        group_sender_inter_arrival = eval(open(sender_schedule, 'r').read())
    if (exe_schedule is None):
        group_sizes = np.random.randint(5, no_virt_host-1, no_of_groups)
        # creates group_mem_ia_rd dictionary
        # group -> [[h11, <inter_arrivale_time_of_memener>, <reception_time> ] , [...], ...]
        for i in range(0,no_of_groups):
            inter_arrival = np.random.exponential(inter_arrival_rate, group_sizes[i])
            recepation_duration = np.random.exponential(recepation_duration_rate, group_sizes[i])
            #group_sizes[i]+1 (+1) is for sender
            group_members = np.random.choice(range(1,no_virt_host), group_sizes[i]+1, replace=False)
            # print group_receiver_arrival
            # print group_members
            member_inter_arrival = []
            member_inter_arrival.append([ nh.get_virtual_host_name(group_members[0]), 0, 0])
            for s in range(0, group_sizes[i]):
                member_inter_arrival.append([nh.get_virtual_host_name(group_members[s+1]), round(inter_arrival[s]), round(recepation_duration[s])])
            group_mem_ia_rd[i] = member_inter_arrival
    else:
        group_mem_ia_rd_str_key = eval(open(exe_schedule, 'r').read())
        for k,v in group_mem_ia_rd_str_key.iteritems():
            group_mem_ia_rd[int(k)] = v


    # creates virtual host dictionary
    # hostname -> VirtualHostExecution object
    for k in range(1,no_virt_host):
        vname = nh.get_virtual_host_name(k)
        ph_ip = nh.get_physical_ip(vname)
        vhe = VirtualHostExecution(vname, ph_ip)
        virtual_host_executor_dict[vname] = vhe
    #launch threads to execute all the groups
    # print("------------------------ Group ip bw ------------------------")
    # print(group_ip_baw_dict)
    # print("-------------------------------------------------------------")
    if exe_schedule is not None:
        print("------------------------ group_mem_ia_rd --------------- ----")
        print(group_mem_ia_rd)
        json.dump(group_mem_ia_rd, open("group_mem_ia_rd.txt",'w'))
        json.dump(group_ip_baw_dict, open("group_ip_baw_dict.txt",'w'))
        json.dump(group_sender_inter_arrival, open("group_sender_sched.txt",'w'))
        print("-------------------------------------------------------------")
    group_start_log = io.open("group-start-ts.txt", 'a', encoding='utf-8')
    for l in range(0,no_of_groups):
        print ("waiting for " + str(int(group_sender_inter_arrival[l])))
        time.sleep(int(group_sender_inter_arrival[l]))
        [ip, bw] = group_ip_baw_dict[l]
        print (" group ip " +str(ip))
        group_start_log.writelines(str(time.strftime("%H:%M:%S +000", time.gmtime()) + "-"+ip+"\n").decode('unicode-escape'))
        ge = GroupExecution(ip, bw, group_mem_ia_rd[l], virtual_host_executor_dict)
        tg = threading.Thread(name=ip, target=ge.run_group)
        tg.start()
        group_threads_list.append(tg)
    group_start_log.close()
    for t in group_threads_list:
        t.join()


def get_group_bw_dict(bw_map_file):
    ip_bw_map = {}
    try:
        with open(bw_map_file) as f:
            lines = [x.strip('\n') for x in f.readlines()]
            index = 0
            for line in lines:
                ip_bw = line.split('-')
                ip = ip_bw[0].strip()
                bw = ip_bw[1].strip()
                ip_bw_map[index] = [ip, bw]
                index = int(index) + 1
    except Exception as e:
        print ('error in reading file named ' + bw_map_file)
        sys.exit(1)
    return ip_bw_map


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--physical_net", help="DOT file specifying physical network topology")
    parser.add_argument("--virtual_net", help="DOT file specifying experimental network topology")
    parser.add_argument("--mapping", help="mapping file")
    parser.add_argument("--bw_map", help="group bandwidth mapping file")
    parser.add_argument("--exe_schedule", help="previous group execution schedule")
    parser.add_argument("--sender_schedule", help="previous sender execution schedule")
    parser.add_argument("--num_groups", help="number of multicast groups to instantiate ")
    args = parser.parse_args()
    main(args.physical_net, args.virtual_net, args.mapping, args.bw_map,
         args.exe_schedule, args.sender_schedule, args.num_groups)