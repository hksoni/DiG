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

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import Tkinter as Tk, tkFileDialog
import tkMessageBox as messagebox
import time
import sys
import os
import io
import argparse
import networkx as nx
import subprocess, shlex
import select
import matplotlib.pyplot as plt
from matplotlib.colors import colorConverter

# Bring that java code to python.. someday!
config_java_jar = './dig-3-cfg.jar'
# python code to be executed on remote hosts
create_vne_py = './create-vne.py'

root = None
plt_fig = None
phy_g = None
virt_g = None
pos_virt = None
pos_phy = None
phy_subplot = None
virt_subplot = None
phy_sp_xlim = None
phy_sp_ylim = None
virt_sp_xlim = None
virt_sp_ylim = None
canvas = None
node_mappings = None
continue_button = None
virt_color_map = {}
host_color_map = {}
deployment_host_color_map = {}
poller = select.epoll()
physical_net_f = None
virtual_net_f = None
mapping_f = None
canvas_frame =None

def main(physical_net, virtual_net, mapping):
    global phy_g, virt_g, pos_phy, pos_virt, root, node_mappings, canvas_frame, canvas, plt_fig
    root = Tk.Tk()
    root.attributes('-zoomed', True)
    root.wm_title("DiG: Data centers in the Grid")
    root.wm_protocol('WM_DELETE_WINDOW', on_closing)
    canvas_frame = Tk.Frame(root)
    create_menu()
    Tk.Label(root, text="Physical Network", fg="red").grid(row=0, column=0)
    Tk.Label(root, text="Experimental Network", fg="dark green").grid(row=0, column=1)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    plt_fig = plt.figure()
    canvas = FigureCanvasTkAgg(plt_fig, master=root)
    canvas.get_tk_widget().grid(row=1, column=0, columnspan=2, sticky='NSEW')
    root.grid_rowconfigure(1, weight=1)
    #draw_physical_virtual_net_with_mapping()
    continue_button = Tk.Button(root, text="Continue Deployment", command = continue_deployment)
    continue_button.grid(row=2, column=0, columnspan=2, sticky='S')
    exit_button = Tk.Button(root, text="Exit",command=on_closing)
    exit_button.grid(row=2, column=1, columnspan=2, sticky='SE')
    Tk.mainloop()


def draw_physical_virtual_net_with_mapping():
    global plt_fig, phy_g, virt_g, pos_phy, pos_virt, phy_subplot, virt_subplot, phy_sp_xlim, phy_sp_ylim, \
        virt_sp_xlim, virt_sp_ylim, canvas, node_mappings, continue_button, deployment_host_color_map
    phy_subplot = plt_fig.add_subplot(121)
    plt.axis('off')
    global virt_color_map
    global host_color_map
    colours = get_n_col(phy_g.number_of_nodes())
    for node,color in zip(phy_g.nodes(), colours):
        host_color_map[node] = color
        deployment_host_color_map[node] = color
    nx.draw_networkx(phy_g, pos=pos_phy,ax=phy_subplot, with_labels=True, node_color=colours)
    phy_sp_xlim=phy_subplot.get_xlim()
    phy_sp_ylim=phy_subplot.get_ylim()
    virt_subplot = plt_fig.add_subplot(122)
    plt.axis('off')
    virt_colors = []
    for host, virt_nodes in node_mappings.iteritems():
        for vt in virt_nodes:
            virt_color_map[vt] = host_color_map[host]
    for node in virt_g.nodes():
        virt_colors.append(virt_color_map[node])
    nx.draw_networkx(virt_g, pos=pos_virt, ax=virt_subplot, with_labels=True, node_color=virt_colors)
    virt_sp_xlim=virt_subplot.get_xlim()
    virt_sp_ylim=virt_subplot.get_ylim()
    canvas.show()


def continue_deployment():
    host_deploy_process_map = {}
    global  virt_g, phy_g, canvas
    # create configuration generator
    update_color_virtual_network(virt_g.nodes(), 'g')
    update_color_physical_network(phy_g.nodes(), 'r')
    canvas.draw()
    [error_msg, ret_code, dir] = generate_configuration(config_java_jar)
    if ret_code != 0:
        messagebox.showerror(title="Error From Configuration Generator", message=error_msg)
        sys.exit(1)
    host_config_ini = dir+'/host-config-exp.ini'
    host_config_map = read_host_config_file(host_config_ini)
    host_config_map_len = len(host_config_map)
    if host_config_map_len == 0:
        messagebox.showerror(title="Error From Configuration Generator",
                             message='something went wrong with configuration generator')
        sys.exit(1)
    messagebox.showinfo(title='Physical Host', message='Establishing connection to physical hosts')
    for host, [ip, cfg_file] in host_config_map.iteritems():
        [scp_ret_code, scp_out, scp_err] = copy_to_remote([cfg_file, create_vne_py], 'root', ip, '~/')
        if scp_ret_code != 0:
            is_exit = messagebox.askyesno(title='Physical Host', message='Error in communicating to '+ host +
                                          '\nDo you want to continue?')
            if is_exit == messagebox.NO:
                sys.exit(1)
        else:
            update_color_physical_network([host])
            canvas.draw()
    for host_name, [ip, cfg_file] in host_config_map.iteritems():
        #print 'before launch ' + host_name
        file_name = cfg_file.split('/')[-1]
        dep_process = launch_deployment_on_remote_host(ip, file_name)
        host_deploy_process_map[dep_process.stdout.fileno()] = [host_name, dep_process]
        poller.register(dep_process.stdout.fileno(), select.EPOLLHUP)
    i = 0
    no_process = len(host_deploy_process_map)
    while i < no_process:
        complet_fds = monitor_deployment_process()
        print complet_fds
        i += len(complet_fds)
        for fd in complet_fds:
            [host_name, dep_process] = host_deploy_process_map.pop(fd)
            dep_process.wait()
            print dep_process.returncode
            if dep_process.returncode == 0:
                update_networks_according_to_mapping(host_name)
            else:
                is_exit = messagebox.askyesno(title='Physical Host', message='Error while deploying on '+ host_name +
                                                                             '\nDo you want to continue?')
                if is_exit == messagebox.YES:
                    sys.exit(1)
    return


def update_networks_according_to_mapping(p_nodes):
    global plt_fig, phy_g, virt_g, pos_phy, pos_virt, phy_subplot, virt_subplot, phy_sp_xlim, phy_sp_ylim, \
        virt_sp_xlim, virt_sp_ylim, canvas, node_mappings, continue_button, virt_color_map, deployment_host_color_map
    ph_nodes = p_nodes
    if type(p_nodes) is not list:
        ph_nodes = [p_nodes]
    for phy_node in ph_nodes:
        print phy_node
        mapped_v_nodes = node_mappings[phy_node]
        update_color_physical_network(phy_node, deployment_host_color_map[phy_node])
        update_color_virtual_network(mapped_v_nodes, deployment_host_color_map[phy_node])
        canvas.draw()


def update_color_virtual_network(node_list, colors='g'):
    global plt_fig, phy_g, virt_g, pos_phy, pos_virt, phy_subplot, virt_subplot, phy_sp_xlim, phy_sp_ylim, \
        virt_sp_xlim, virt_sp_ylim, canvas, node_mappings, continue_button, virt_color_map
    vert_subplot = plt_fig.add_subplot(122)
    plt.axis('off')
    cl = []
    if type(node_list) is not list:
        nodes = [node_list]
    else:
        nodes = node_list
    if colors is list:
        for n,c in zip(nodes, colors):
            virt_color_map[n] = colorConverter.to_rgb(c)
    else:
        for n in nodes:
            virt_color_map[n] = colorConverter.to_rgb(colors)
    for node in virt_g.nodes():
        cl.append(virt_color_map[node])
    nx.draw_networkx(virt_g, pos=pos_virt,ax=vert_subplot, with_labels=True, node_color=cl)
    vert_subplot.set_xlim(virt_sp_xlim)
    vert_subplot.set_ylim(virt_sp_ylim)
    plt.axis('off')


def update_color_physical_network(node_list, colors='b'):
    global plt_fig, phy_g, virt_g, pos_phy, pos_virt, phy_subplot, virt_subplot, phy_sp_xlim, phy_sp_ylim, \
        virt_sp_xlim, virt_sp_ylim, canvas, node_mappings, continue_button, host_color_map
    phy_subplot = plt_fig.add_subplot(121)
    plt.axis('off')
    cl = []
    if type(node_list) is not list:
        nodes = [node_list]
    else:
        nodes = node_list
    if type(colors) is list:
        for n,c in zip(nodes, colors):
            host_color_map[n] = colorConverter.to_rgb(c)
    else:
        for n in nodes:
            host_color_map[n] = colorConverter.to_rgb(colors)
    for node in phy_g.nodes():
        cl.append(host_color_map[node])
    nx.draw_networkx(phy_g, pos=pos_phy,ax=phy_subplot, with_labels=True, node_color=cl)
    phy_subplot.set_xlim(phy_sp_xlim)
    phy_subplot.set_ylim(phy_sp_ylim)
    plt.axis('off')


def monitor_deployment_process():
    fds = []
    global poller
    for fd, flags in poller.poll(timeout=-1):
        poller.unregister(fd)
        fds.append(fd)
    return fds


def on_closing():
    global root
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        root.quit()
        root.destroy()


def generate_configuration(dig_3_cg_jar):
    global  virtual_net_f, physical_net_f, mapping_f
    dir_name = os.getcwd()+'/deployment-meta-data'
    rmdir_cmd = 'rm -rf '+ dir_name
    mkdir_cmd = 'mkdir ' + dir_name
    config_cmd = 'java -jar ' + dig_3_cg_jar + ' ' + physical_net_f + ' ' + virtual_net_f + ' ' + mapping_f + ' ' +\
                 dir_name + '/'
    commands = [rmdir_cmd, mkdir_cmd, config_cmd]
    [error_msg, ret_code] = execute_ordered_list_cmds(commands)
    return [error_msg, ret_code, dir_name]


def read_host_config_file(host_config_file):
    host_config_map = {}
    try:
        with io.open(host_config_file) as f:
            lines = [x.strip('\n') for x in f.readlines()]
        for line in lines:
            [ip, cfg_file, host] = line.strip().split()
            host_config_map[host] = [ip, cfg_file]
    except (IOError, IndexError, Exception) as e:
        print 'error in reading file named ' + host_config_file
        sys.exit(1)
    return host_config_map


def get_mapping_dict_from_file(mapping_file):
    node_map = {}
    try:
        with open(mapping_file) as f:
            lines = [x.strip('\n') for x in f.readlines()]
        for line in lines:
            nodes = line.split('-')
            virt_nodes = []
            virt = nodes[1].strip().split(',')
            for n in virt:
                n = n.strip()
                virt_nodes.append(n)
            phy_node = nodes[0].strip()
            node_map[phy_node] = virt_nodes
    except Exception as e:
        print 'error in reading file named ' + mapping_file
        sys.exit(1)
    return node_map


# executes 'python create-vne.py xyz.cfg' on remote host
def launch_deployment_on_remote_host(remote_host, host_cfg):
    remote_command = 'python ~/' + create_vne_py + ' ' + host_cfg
    return execute_on_remote_host('root', remote_host, remote_command)


def execute_on_remote_host(remote_user, remote_host, remote_command):
    cmd = 'ssh ' + remote_user + '@' + remote_host + ' ' + remote_command
    cmd_popen_arg = shlex.split(cmd)
    process = subprocess.Popen(cmd_popen_arg, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process


def copy_to_remote(srcs, remote_user, remote_host, remote_dest_dir):
    src_files = ''
    for scr in srcs:
        src_files += scr + ' '
    scp_cmd = 'scp ' + src_files + ' ' + remote_user + '@' + remote_host + ':' + remote_dest_dir
    cmd_popen_arg = shlex.split(scp_cmd)
    scp = subprocess.Popen(cmd_popen_arg, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    [out, err] = scp.communicate()
    return [scp.returncode, out, err]


def execute_ordered_list_cmds(cmds):
    ret_code = 0
    error_msg = ''
    for cmd in cmds:
        cmd_popen_arg = shlex.split(cmd)
        p = subprocess.Popen(cmd_popen_arg, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        [out, err] = p.communicate()
        if p.returncode != 0:
            ret_code = 1
            error_msg = 'Execution of ' + cmd + 'threw following error \n' + err
            #print this error message somewhere in UI
            break
    return [error_msg, ret_code]


def get_n_col(n):
    colors = []
    tableau20 = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),
                 (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),
                 (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),
                 (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),
                 (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]
    for x in xrange(n):
        [r, g, b] = tableau20[x]
        tableau20[x] = (r / 255., g / 255., b / 255.)
        colors.append(tableau20[x])
    return colors


def create_menu():
    global  root
    menubar = Tk.Menu(root)
    filemenu = Tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label="Open Physical Network", command=get_physical_net)
    filemenu.add_command(label="Open Experimental Network", command=get_experimental_net)
    filemenu.add_separator()
    filemenu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="Select Files", menu=filemenu)
    root.config(menu=menubar)
    mapping_menu = Tk.Menu(menubar, tearoff=0)
    mapping_menu.add_command(label="RUN ALEVIN", command=hello)
    mapping_menu.add_command(label="Add Mapping File", command=get_mapping)
    menubar.add_cascade(label="Network Mapping", menu=mapping_menu)
    root.config(menu=menubar)


def hello():
    print hello


def get_physical_net():
    global physical_net_f, phy_g, pos_phy
    options = {}
    options['title'] = 'Select physical network DOT format file'
    options['filetypes'] = [('dot files', '.dot')]
    options['defaultextension'] = '.dot'
    physical_net_f = tkFileDialog.askopenfilename(**options)
    phy_g = nx.read_dot(physical_net_f)
    pos_phy=nx.graphviz_layout(phy_g, prog='fdp')
    update_color_physical_network(nx.nodes(phy_g), 'r')
    canvas.draw()


def get_experimental_net():
    global virtual_net_f, pos_virt, virt_g
    options = {}
    options['title'] = 'Select experimental network DOT format file'
    options['filetypes'] = [('dot files', '.dot')]
    options['defaultextension'] = '.dot'
    virtual_net_f = tkFileDialog.askopenfilename(**options)
    virt_g = nx.read_dot(virtual_net_f)
    pos_virt=nx.graphviz_layout(virt_g, prog='fdp')
    update_color_virtual_network(nx.nodes(virt_g), 'g')
    canvas.draw()


def get_mapping():
    global  mapping_f, node_mappings
    options = {}
    options['title'] = 'Get mapping file'
    options['filetypes'] = [('txt files', '.txt')]
    options['defaultextension'] = '.dot'
    mapping_f = tkFileDialog.askopenfilename(**options)
    node_mappings = get_mapping_dict_from_file(mapping_f)
    draw_physical_virtual_net_with_mapping()
    canvas.draw()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--physical_net", help="DOT file specifying physical network topology")
    parser.add_argument("--virtual_net", help="DOT file specifying experimental network topology")
    parser.add_argument("--mapping", help="mapping file")
    args = parser.parse_args()
    main(args.physical_net, args.virtual_net, args.mapping)
