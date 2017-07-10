from Tkinter import *
tk = Tk()
main_frame = Frame(tk)
main_frame.grid(row=0)
frame1 = Frame(main_frame, bg="orange", width=500, height=100)
frame2 = Frame(main_frame, bg="blue", width=500, height=100)
frame3 = Frame(main_frame, bg="green", width=1000, height=50)
frame1.grid(row=1,column=1)
frame2.grid(row=1,column=2)
frame3.grid(row=2,column=1,columnspan=2)
frame3.pack_propagate(0) # Keeps bottom frame from resizing
btn1 = Button(frame3, text='Next', width = 10)
btn1.pack(side='right')  # sticks on side
btn2 = Button(frame3, text='Previous', width = 10)
btn2.pack(side='right')  # sticks on side
tk.mainloop()

# #!/usr/bin/python
#
# import matplotlib
# matplotlib.use('TkAgg')
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# import matplotlib.pyplot as plt
# import Tkinter as Tk
# import networkx as nx
# import  numpy as np
# import tkMessageBox as messagebox
# from tkMessageBox import showinfo
# import time
# import sys
# import os
# import io
# import argparse
# import networkx as nx
# import subprocess, shlex
#
# from random import randint
# from symbol import arglist
#
# pos_virt = None
# pos_phy = None
# f = None
# phy = None
# virt = None
# root = None
# def main(argv):
#     if len(argv) < 1:
#         print ("input file not provided")
#         return
#     global f, phy, pos_phy, virt, pos_virt, root
#     root = Tk.Tk()
#     root.wm_title("Data Centers in the Grid - UI")
#     root.wm_protocol('WM_DELETE_WINDOW', on_closing)
#     print argv[0]
#     print argv[1]
#     virt=nx.read_dot(argv[0])
#     phy=nx.read_dot(argv[1])
#     pos_virt=nx.graphviz_layout(virt,prog='fdp')
#     pos_phy=nx.graphviz_layout(phy,prog='fdp')
#     f = plt.figure()
#     plot_grpahs()
#     # a tk.DrawingArea
#     canvas = FigureCanvasTkAgg(f, master=root)
#     canvas.show()
#     canvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
#     Tk.mainloop()
#
# def on_closing():
#     global root
#     if messagebox.askokcancel("Quit", "Do you want to quit?"):
#         root.destroy()
#
# def plot_grpahs():
#     a = f.add_subplot(121)
#     plt.axis('off')
#     colors=[]
#     nx.draw_networkx(phy,pos=pos_phy,ax=a, with_labels=True, node_color=colors)
#     axlim=a.get_xlim()
#     aylim=a.get_ylim()
#     b = f.add_subplot(122)
#     plt.axis('off')
#     nx.draw_networkx(virt,pos=pos_virt ,ax=b, with_labels=True)
#     bxlim=b.get_xlim()
#     bylim=b.get_ylim()
#
#
# if __name__ == "__main__":
#     sys.exit(main(sys.argv[1:]))
#
#
#
#    # plt.ion()
#    #  pos=nx.graphviz_layout(g,prog='fdp')
#    #  #pos = nx.fruchterman_reingold_layout(g)
#    #  nx.draw(g, pos, with_labels=True)
#    #  plt.pause(0.0001)
#    #  plt.show()
#    #  time.sleep(1)
#    #  colors=[]
#    #  for n in g.nodes():
#    #      print n
#    #      if str(n).startswith('Cs'):
#    #          colors.append('b')
#    #      else:
#    #          colors.append('g')
#    #  nx.draw(g, pos, node_color=colors, with_labels=True)
#    #  plt.pause(1)
#    #  time.sleep(1)
#    #  plt.show()