#!/usr/bin/env python3.6
import argparse
import threading as thr
import os.path as path

import working_area
import hand_draw
import mymath
import math

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk


class Conf:
    input_file = path.join(path.dirname(path.realpath(__file__)), 'input.txt')
    step = 6

########################################################################


def read_file(file_name):
    # get file
    try:
        with open(file_name) as f:
            inp = f.read()
    except:
        raise Exception('cant open file, '
                        'file name should be input.txt '
                        'and be in the same folder')

    # execute it, to get variables in this locals scope
    try:
        exec(inp)
    except:
        raise Exception('cant read file')

    # construct robot
    try:
        robot = {
            'do_inverse': locals()['do_inverse'],
            'l': np.array(locals()['l']),  # 1D array
            'theta': locals()['θ'],

            'q_torq': np.array(locals()['q_torq']),  # 1D array
            'pex': np.matrix(locals()['Pex']).transpose(),  # 2D 3x1 matrix

            'q': np.array(locals()['q']),
            'a': locals()['a'],
            'b': locals()['b'],

            # added
            'torque': np.zeros((3, 1)),
            'jacob': np.zeros((3, 3))
        }
    except:
        raise Exception('cant get variables from file,'
                        ' some are not found')

    return robot

########################################################################


def calc_inverse_km(robot):
    ''' calc q_inv1, q_inv2 (each is 1D array) from l, a,b, theta  '''
    theta = robot['theta']
    l1 = robot['l'][0]
    l2 = robot['l'][1]
    l3 = robot['l'][2]

    a1 = robot['a'] - l3 * mymath.cosd(theta)
    b1 = robot['b'] - l3 * mymath.sind(theta)
    r = math.hypot(a1, b1)
    alpha = mymath.alpha(l1, l2, r)

    robot['q_inv1'] = _calc_inverse_km(a1, b1, r, l1, theta, +alpha)
    robot['q_inv2'] = _calc_inverse_km(a1, b1, r, l1, theta, -alpha)


def _calc_inverse_km(a1, b1, r, l1, theta, alpha):
    ''' get one part '''
    q1 = mymath.atan2d(b1, a1) - alpha
    q2 = mymath.atan2d((r * mymath.sind(alpha)), (r * mymath.cosd(alpha) - l1))
    q3 = theta - q1 - q2
    return np.array([q1, q2, q3])

########################################################################


def calc_working_area(robot, step):
    ''' return all x, y of end effector to plot '''
    robot['work_area'] = working_area.get_xy(robot, step)

########################################################################


def calc_torque(robot):
    ''' 3x1 matrix, Q = -J.T x Pex '''
    robot['torque'] = np.matmul(-1 * robot['jacob'].transpose(), robot['pex'])


def calc_jacobian(robot):
    ''' 3x3 matrix, see slide num 4 page 12 '''
    get_dr = lambda ls, qs, func: np.array(
        [ls[i] * func(sum(qs[:i + 1])) for i in range(3)])

    dr1 = -1 * get_dr(robot['l'], robot['q_torq'], mymath.sind)
    dr2 = get_dr(robot['l'], robot['q_torq'], mymath.cosd)

    robot['jacob'] = np.mat([
        [sum(dr1[i:]) for i in range(3)],
        [sum(dr2[i:]) for i in range(3)],
        [1, 1, 1]
    ])

########################################################################


def calc_all(robot, step):
    ''' cal all missing data for robot, then return it '''
    try:
        calc_working_area(robot, step)
    except:
        raise Exception('error while calculating working area')

    if robot['do_inverse']:
        try:
            calc_inverse_km(robot)
        except:
            raise Exception('error while calculating inverse km')
    else:
        robot['q_inv1'] = robot['q_torq']

    try:
        calc_jacobian(robot)
    except:
        raise Exception('error while calculating jacobian')

    try:
        calc_torque(robot)
    except:
        raise Exception('error while calculating torque')

    return robot

########################################################################


class App(tk.Frame):

    def __init__(self):
        self.root = tk.Tk()
        self.root.wm_title('Robotics Project')

        tk.Frame.__init__(self, master=self.root, takefocus=True)
        self.pack()

        self.get_args()

        # hand_draw canvas
        self.drw_canvas = tk.Canvas(self, width=400, height=400)
        self.drw_canvas.pack(side='right')
        self.drawer = hand_draw.Drawer({}, self.drw_canvas)

        # plot canvas
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.subplt = self.fig.add_subplot(111)
        self.plt_canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.plt_canvas.show()
        self.plt_canvas.get_tk_widget().pack(side='left', fill=tk.BOTH, expand=1)
        self.plt_canvas._tkcanvas.pack(side='left', fill=tk.BOTH, expand=1)

        # buttons
        self.btn_update = tk.Button(self, text='update')
        self.btn_update.pack(side='bottom')
        self.btn_update.bind('<Button-1>', self.update_ui)

        # labels
        self.lbl_torq3 = tk.Label(self)
        self.lbl_torq3.pack(side='bottom')
        tk.Label(self, text='torque3').pack(side='bottom')

        self.lbl_torq2 = tk.Label(self)
        self.lbl_torq2.pack(side='bottom')
        tk.Label(self, text='torque2').pack(side='bottom')

        self.lbl_torq1 = tk.Label(self)
        self.lbl_torq1.pack(side='bottom')
        tk.Label(self, text='torque1').pack(side='bottom')

        self.lbl_b = tk.Label(self)
        self.lbl_b.pack(side='bottom')
        tk.Label(self, text='b').pack(side='bottom')

        self.lbl_a = tk.Label(self)
        self.lbl_a.pack(side='bottom')
        tk.Label(self, text='a').pack(side='bottom')

        # update once
        self.update_ui(None)

    def update_ui(self, event):
        self.robot = read_file(self.args.input_file)
        self.robot = calc_all(robot=self.robot, step=self.args.step)

        self._update_hand()
        thr.Thread(target=self._update_labels).start()
        thr.Thread(target=self._update_plot).start()

    def _update_plot(self):
        self.fig.clear()
        self.subplt = self.fig.add_subplot(111)

        x, y = self.robot['work_area']
        self.subplt.plot(x, y, 'g.')
        self.plt_canvas.draw()

    def _update_hand(self):
        self.drawer.robot = self.robot
        self.drawer.draw()

    def _update_labels(self):
        self.lbl_torq1['text'] = self.robot['torque'][0, 0]
        self.lbl_torq2['text'] = self.robot['torque'][1, 0]
        self.lbl_torq3['text'] = self.robot['torque'][2, 0]

        self.lbl_a['text'] = self.robot['a']
        self.lbl_b['text'] = self.robot['b']

    def get_args(self):
        parser = argparse.ArgumentParser()

        parser.add_argument('input_file', nargs='?', default=Conf.input_file)
        parser.add_argument('-s', '--step', nargs='?',
                            default=Conf.step, type=int)

        self.args = parser.parse_args()


if __name__ == '__main__':
    App().mainloop()
