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
import itertools
import time
from time import gmtime, strftime, localtime
import sys
import os
import io
import signal
import argparse
import threading
import networkx as nx
import subprocess, shlex
import numpy as np
from os import system as cmd
import os.path

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

    def execute(self, command_id, command, file_part, log_dump_dir):
        std_out_log_file = log_dump_dir+self.virtual_host+"-"+file_part+".out"
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
            # print("Terminate : " + pstr)
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
        # print("TERMINATED : " + pstr)


class GroupExecution:

    def __init__(self, gr_ip, gr_bw, mem_ia_rd_list, vh_executor_dict, log_dump_dir):
        self.log_dir = log_dump_dir
        self.group_ip = gr_ip
        self.rec_thread_list = []
        self.bw = gr_bw
        self.mem_ia_rd_l = mem_ia_rd_list
        self.vh_exer_dict = vh_executor_dict
        self.sender_command = "iperf -l 1400  -c "+self.group_ip+" -u -b "+self.bw+"k -f m -i 3 -t 1200"
        self.receiver_command = "iperf -s -B "+self.group_ip+" -u -f m -i 3"


    def run_group(self):
        [src_vh, ia, sr] = self.mem_ia_rd_l.pop(0)
        terminate_sender = False
        self.group_src = src_vh
        # start group sources
        virtual_host_executor_sender = self.vh_exer_dict[src_vh]
        virtual_host_executor_sender.execute(self.group_ip, self.sender_command,
                                             self.group_ip+"_s_"+get_str_time(), self.log_dir)
        #starting a timer thread to terminate the sender
        # t_s = threading.Timer(6000, virtual_host_executor.terminate, [self.group_ip])
        # t_s.start()
        for vh, ia, rd in self.mem_ia_rd_l:
            # print("waiting for " + str(ia) + " - group rece " + str(self.group_ip))
            time.sleep(ia) # waiting for inter-arrival time to pass
            #start receiver for rd seconds
            virtual_host_executor_receiver = self.vh_exer_dict[vh]
            virtual_host_executor_receiver.execute(self.group_ip, self.receiver_command,
                                                   self.group_ip+"_r_"+get_str_time(), self.log_dir)
            Logger.LogReceiver()
            if rd != 0: #receivers will be terminated by explicit call
                t_r = threading.Timer(rd, virtual_host_executor_receiver.terminate, [self.group_ip])
                t_r.start()
                self.rec_thread_list.append(t_r)
                terminate_sender = True
        for tr in self.rec_thread_list:
            tr.join()
        if terminate_sender:
            virtual_host_executor_sender.terminate(self.group_ip)
        print("All receivers of group " + str(self.group_ip) + "are instantiated")

    def terminate_receivers_in_the_group(self):
        # get group source
        virtual_host_executor_sender = self.vh_exer_dict[self.group_src]
        for vh, ia, rd in self.mem_ia_rd_l:
            time.sleep(1)
            #start receiver for rd seconds
            virtual_host_executor_receiver = self.vh_exer_dict[vh]
            virtual_host_executor_receiver.terminate(self.group_ip)
        virtual_host_executor_sender.terminate(self.group_ip)
        print("All receivers of group " + str(self.group_ip) + " are terminated")


def get_str_time():
    localtime = time.localtime(time.time())
    time_part = str(localtime.tm_hour) + "_"+ \
                str(localtime.tm_min) + "_" + \
                str(localtime.tm_sec)
    return time_part


def generate_multicast_workload(physical_net_f, virtual_net_f, node_mappings_file,
                                bw_map_file, exe_schedule, sender_schedule, num_groups, workload_dir):
    nh = NetworkMappingHelper(physical_net_f, virtual_net_f, node_mappings_file)
    group_ip_baw_dict = get_group_bw_dict(bw_map_file)
    Logger.OpenFile(workload_dir+"/receivers_count.log")
    print(group_ip_baw_dict)
    virtual_host_executor_dict = {}
    group_sender_inter_arrival_rate = 3
    inter_arrival_rate = 5
    group_execution_list = []
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
        # group_sender_inter_arrival = np.random.randint(1,3, no_of_groups)
    else:
        group_sender_inter_arrival = eval(open(sender_schedule, 'r').read())
    if (exe_schedule is None):
        group_sizes = 10
        # group_sizes = np.random.randint(5, no_virt_host-1, no_of_groups)
        # creates group_mem_ia_rd dictionary
        # group -> [[h11, <inter_arrivale_time_of_memener>, <reception_time> ] , [...], ...]
        for i in range(0,no_of_groups):
            inter_arrival = np.random.exponential(inter_arrival_rate, group_sizes)
            # inter_arrival = np.random.randint(5, 10, group_sizes)
            #recepation_duration = np.random.exponential(recepation_duration_rate, group_sizes)
            # recepation_duration = np.random.randint(10,310, group_sizes)
            recepation_duration = np.full(group_sizes, 0)
            #group_sizes[i]+1 (+1) is for sender
            # group_members = np.random.choice(range(1,no_virt_host), group_sizes[i]+1, replace=False)
            group_members = np.random.choice(range(1,no_virt_host), group_sizes+1, replace=False)
            # print group_receiver_arrival
            # print group_members
            member_inter_arrival = []
            member_inter_arrival.append([ nh.get_virtual_host_name(group_members[0]), 0, 0])
            for s in range(0, group_sizes):
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
    if exe_schedule is None:
        # print("------------------------ group_mem_ia_rd --------------- ----")
        # print(group_mem_ia_rd)
        json.dump(group_mem_ia_rd, open(workload_dir+"group_mem_ia_rd.txt",'w'))
        json.dump(group_ip_baw_dict, open(workload_dir+"group_ip_baw_dict.txt",'w'))
        json.dump(group_sender_inter_arrival.tolist(), open(workload_dir+"group_sender_sched.txt",'w'))
        # print("-------------------------------------------------------------")
    for l in range(0,no_of_groups):
        # print ("waiting for " + str(int(group_sender_inter_arrival[l])))
        time.sleep(int(group_sender_inter_arrival[l]))
        [ip, bw] = group_ip_baw_dict[l]
        print (" group ip " +str(ip))
        ge = GroupExecution(ip, bw, group_mem_ia_rd[l], virtual_host_executor_dict, workload_dir)
        group_execution_list.append(ge)
        tg = threading.Thread(name=ip, target=ge.run_group)
        tg.start()
        group_threads_list.append(tg)
    for t in group_threads_list:
        t.join()
    print (" All group sender-receivers instantiated, waiting for 125 secs ")
    Logger.LogAllReceiverJoinTS()
    time.sleep(125)
    group_terminate_threads_list = []
    print (" stopping all receivers ")
    for groupE in group_execution_list:
        tge = threading.Thread(name=groupE.group_ip, target=groupE.terminate_receivers_in_the_group)
        tge.start()
        group_terminate_threads_list.append(tge)
    for t in group_terminate_threads_list:
        t.join()
    Logger.CloseFile(workload_dir+"./receivers_count.log")


class Logger:
    receiver_count_lock = threading.Lock()
    receiver_count = int(0)
    @classmethod
    def OpenFile(cls, file_name):
        cls.receiver_count_log_f = io.open(file_name, 'a', encoding='utf-8')

    @classmethod
    def LogReceiver(cls):
        cls.receiver_count_lock.acquire()
        cls.receiver_count +=  1
        if cls.receiver_count % 10 == 0:
            line = str(time.strftime("%I:%M:%S +000", time.localtime())+ "-"+str(cls.receiver_count))
            cls.receiver_count_log_f.writelines(str(line+"\n").decode('unicode-escape'))
        cls.receiver_count_lock.release()

    @classmethod
    def LogAllReceiverJoinTS(cls):
        cls.receiver_count_lock.acquire()
        line = str(time.strftime("%I:%M:%S +000", time.localtime())+ "-10000")
        cls.receiver_count_log_f.writelines(str(line+"\n").decode('unicode-escape'))
        cls.receiver_count_lock.release()

    @classmethod
    def CloseFile(cls, file_name):
        cls.receiver_count_log_f.close()


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


class MulticastNetworkExpLauncher:

    def __init__(self, controller_node, physical_net_fn, virtual_net_fn, node_mappings_fn,
                 bw_map_fn, algorithm_cont_binaries, algo_names, exp_root_d, dep_root_d,
                 exp_name, group_sizes_l, run_nums_l, ref_sched=None):
        self.cn_process = None
        self.log_file = None
        self.phy_net = exp_root_d+'/'+physical_net_fn
        self.vir_net = exp_root_d+'/'+virtual_net_fn
        self.node_map = exp_root_d+'/'+node_mappings_fn
        self.bw_map = exp_root_d+'/'+bw_map_fn
        self.ref_workload_sched_algo = ref_sched
        self.gr_sizes_l = group_sizes_l
        self.runs_l = run_nums_l
        self.cn_node = controller_node
        self.cn_bin_list = algorithm_cont_binaries.split(',')
        self.algos_names = algo_names.split(',')
        self.deploy_root_dir = dep_root_d
        self.experiment_root_dir = exp_root_d #'/root/dig-4-cg/vne-for-qos-multicast/internet2/'
        self.exp_data_dir = exp_root_d + '/'+exp_name+'/'
        self.experiment_name = exp_name
        self.debug_ps_file = ' /root/dig-4-cg/vne-for-qos-multicast/internet2/suno-nodes/debug-ps.sh '
        self.cn_node_ssh = 'ssh -t  root'+'@'+self.cn_node + ' '


    def log_message(self, msg):
        self.log_file.writelines(str(msg+"\n").decode('unicode-escape'))

    def build_experimental_nework(self):
        expect_deploy_command = ' expect /root/dig-4-cg/deploy-vne.exp '+self.experiment_root_dir+'/host-config-exp.ini'
        cl = self.cn_node_ssh+ expect_deploy_command
        self.log_message ('-----building experimental nework-----')
        self.log_message (cl)
        out_str = pexpect.run(cl)
        # self.log_message (out_str)
        self.log_message ('--------------------------------------')

    def destroy_experimentail_nework(self):
        expect_delete_command = ' expect /root/dig-4-cg/delete-vne.exp '+self.experiment_root_dir+'/host-clean-up.ini'
        cl = self.cn_node_ssh + expect_delete_command
        self.log_message ('----destroying experimental nework----')
        self.log_message (cl)
        out_str = pexpect.run(cl)
        # self.log_message (out_str)
        self.log_message ('--------------------------------------')

    def launch_controller(self, cn_binary):
        cn_topo_option = ' -Dnet.floodlightcontroller.multicastcontroller.MulticastController.topologyFile='
        cn_topo_value = self.experiment_root_dir+'virtual-net.dot'
        cn_topo_file = cn_topo_option+cn_topo_value
        cn_ip_bw_option = ' -Dnet.floodlightcontroller.multicastcontroller.MulticastController.ipBandwidthQoSFile='
        cn_ip_bw_value = self.experiment_root_dir+'ip-bw-qos-mapping.txt'
        cn_ip = cn_ip_bw_option+cn_ip_bw_value
        cn_options = cn_topo_file+ ' ' + cn_ip +' '
        cn_command = ' java '+ cn_options +' -jar  '+cn_binary
        cl = self.cn_node_ssh + cn_command
        self.log_message ('-----------launch_controller----------')
        self.log_message (cl)
        self.log_message ('--------------------------------------')
        self.cn_process = pexpect.spawnu(cl)

    def restart_controller(self, cn_binary):
        self.log_message ('----restart_controller----')
        if self.cn_process is not None:
            self.terminate_with_control_c(self.cn_process)
            self.cn_process = None
        self.cleanup_controller_logs()
        time.sleep(10)
        self.launch_controller(cn_binary)
        self.log_message ('--------------------------')

    def cleanup_controller_logs(self):
        cl = self.cn_node_ssh + ' rm -rf link-bw-stats.txt cachedir SyncDB controller.log'
        self.log_message ('----cleanup_controller_logs----')
        self.log_message (cl)
        self.log_message ('-------------------------------')
        pexpect.run(cl)

    def terminate_with_control_c(self, process):
        self.log_message ('----------terminating----------')
        process.terminate()
        self.log_message ('-------------------------------')

    def is_experimental_network_up(self):
        cl = self.cn_node_ssh +self.debug_ps_file
        attempt = 1
        while attempt < 5:
            time.sleep(10)
            out_str = pexpect.run(cl, timeout=20)
            v1_c = out_str.count('v1')
            v5_c = out_str.count('v5')
            self.log_message('-----is_experimental_network_up----')
            self.log_message('#Hosts='+str(v1_c)+',#switches='+str(v5_c))
            self.log_message('-----------------------------------')
            if v1_c == 39 and v5_c == 39:
                return True
            attempt += 1
        return False

    def wait_for_experimental_network_cleanup(self):
        cl = self.cn_node_ssh +self.debug_ps_file
        attempt = 1
        time.sleep(4)
        while attempt < 6:
            time.sleep(2)
            out_str = pexpect.run(cl, timeout=40)
            v1_c = out_str.count('v1')
            v5_c = out_str.count('v5')
            self.log_message('-----wait_for_experimental_network_cleanup----')
            self.log_message('#Hosts='+str(v1_c)+',#switches='+str(v5_c))
            self.log_message('----------------------------------------------')
            if v1_c == 0 and v5_c == 0:
                return True
            attempt += 1
        return False


    def copy_controller_logs(self, dest_dir):
        cl = 'rsync -avz root@'+self.cn_node+':link-bw-stats.txt :controller.log ' + dest_dir
        (out_str, exitstatus) = pexpect.run(cl, withexitstatus=True)
        self.log_message("------Copied log files-----")
        self.log_message (cl)
        self.log_message(out_str)
        self.log_message("---------------------------")

    def wait_for_link_updates_in_controller(self):
        self.log_message("------wait_for_link_updates_in_controller-----")
        trials = 0
        out_str = '0'
        text = '\"Total\ links\ in\ map\ :\ 102\" controller.log'
        time.sleep(6)
        while trials < 10:
            time.sleep(3)
            trials += 1
            cl = self.cn_node_ssh + ' grep -c '+text
            out_str = pexpect.run(cl).split('\r')[0]
            self.log_message(cl)
            self.log_message(out_str)
            self.log_message("----------------------------------------------")
            if out_str == '1':
                return True
            if "No such file or directory" in out_str:
                return False


    def check_link_bw_stat_overflow(self):
        out_str = '0'
        text = '\"=-\" link-bw-stats.txt'
        cl = self.cn_node_ssh + ' grep -c '+text
        out_str = pexpect.run(cl).split('\r')
        if out_str[0] is not '0':
            self.log_message('Command -> ' + cl)
            self.log_message('outpur -> ' + out_str)


    def launch_workload(self, group_size, workload_gen_dir):
        self.log_message('--------launch_workload------------')
        exe_schedule_f = workload_gen_dir+'/group_mem_ia_rd.txt'
        sender_sched_f = workload_gen_dir+'/group_sender_sched.txt'
        mem_ia_bool = os.path.exists(exe_schedule_f)
        send_sched_bool = os.path.exists(sender_sched_f)
        workload_gen_command = ''
        if mem_ia_bool == False and send_sched_bool == False:
            self.log_message('------generating new schedule-----')
            generate_multicast_workload(self.phy_net, self.vir_net, self.node_map,
                                        self.bw_map, None, None, group_size, workload_gen_dir)
        elif mem_ia_bool == True and send_sched_bool == True:
            self.log_message('--------schedules exists--------')
            generate_multicast_workload(self.phy_net, self.vir_net, self.node_map, self.bw_map,
                                        exe_schedule_f, sender_sched_f, group_size, workload_gen_dir)
        else:
            self.log_message("Both files are not available at " + workload_gen_dir)
        self.log_message('------------------------------------')


    def execute_all(self):
        # deploy_flag = False
        mk_data = 'mkdir -p '+self.exp_data_dir
        pexpect.run(mk_data)
        self.log_file = io.open(self.exp_data_dir+self.experiment_name+".log", 'w', encoding='utf-8', buffering=1)
        self.log_message(mk_data)
        for cn_bin, algo in itertools.izip(self.cn_bin_list, self.algos_names):
            if algo == self.ref_workload_sched_algo:
                continue
            mkdir_cl = 'mkdir -p '+self.exp_data_dir+algo+'/'
            pexpect.run(mkdir_cl)
            self.log_message(mkdir_cl)
            for gs in self.gr_sizes_l:
                mkdir_cl = 'mkdir -p '+self.exp_data_dir+algo+'/'+str(gs)+'/'
                pexpect.run(mkdir_cl)
                self.log_message(mkdir_cl)
                for run in self.runs_l:
                    nodes_up = False
                    links_up = False
                    deploy_try = 0
                    workload_gen_dir = self.exp_data_dir+algo+'/'+str(gs)+'/run'+str(run)+'/'
                    mkdir_cl = 'mkdir -p '+ workload_gen_dir
                    pexpect.run(mkdir_cl)
                    self.log_message("----------------------"+workload_gen_dir+"----------------------")
                    self.log_message(mkdir_cl)
                    if self.ref_workload_sched_algo is not None:
                        ref_dir = self.exp_data_dir+self.ref_workload_sched_algo+'/'+str(gs)+'/run'+str(run)+'/'
                        src_files = ref_dir+'group_mem_ia_rd.txt ' + ref_dir+'/group_sender_sched.txt'
                        cp_cmd = 'cp '+src_files+' '+workload_gen_dir
                        pexpect.run(cp_cmd)
                        self.log_message(cp_cmd)
                    while (nodes_up == False or links_up == False) and deploy_try < 5:
                        self.destroy_experimentail_nework()
                        self.wait_for_experimental_network_cleanup()
                        self.build_experimental_nework()
                        self.cleanup_controller_logs()
                        self.launch_controller('/root/dig-4-cg/'+cn_bin)
                        time.sleep(15)
                        self.restart_controller('/root/dig-4-cg/'+cn_bin)
                        nodes_up = self.is_experimental_network_up()
                        links_up = self.wait_for_link_updates_in_controller()
                        deploy_try += 1
                    if nodes_up == False or links_up == False:
                        self.log_message("----Error in bringing up network and controller ----")
                        self.stop_execution()
                    self.launch_workload(gs, workload_gen_dir)
                    time.sleep(2)
                    self.terminate_with_control_c(self.cn_process)
                    # self.destroy_experimentail_nework()
                    self.copy_controller_logs(workload_gen_dir)
                    self.cleanup_controller_logs()
                    self.log_message("-------------------------------------------------------------------")
            if self.ref_workload_sched_algo is None:
                self.ref_workload_sched_algo = algo
        self.stop_execution()

    def stop_execution(self):
        self.log_file.close()
        exit(0)


def main():
#    algo_bins = 'multicast-qos-fl.jar,'+'multicast-qos-fl-lb.jar,'+'multicast-qos-fl-spt.jar'
    algo_bins = 'multicast-qos-fl-50.jar'
#    algo_names = 'dcbr,'+'lb,'+'spt'
    algo_names = 'dcbr-50'
    exp_root_d = '/root/dig-4-cg/vne-for-qos-multicast/internet2/'
    dep_root_d = '/root/dig-4-cg/'
    exp_name = 'exp2_2mb_10-100_r1-5'
    g_s = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
    runs = [1, 2, 3, 4, 5]
    mnel = MulticastNetworkExpLauncher('suno-1', 'suno.dot', 'internet2-al2s.dot', 'mapping-al2s.txt',
                                       'ip-bw-qos-mapping.txt', algo_bins, algo_names, exp_root_d,
                                       dep_root_d, exp_name, g_s, runs)
    mnel.execute_all()

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
    main()
    # main(args.physical_net, args.virtual_net, args.mapping, args.bw_map,
    #      args.exe_schedule, args.sender_schedule, args.num_groups)
