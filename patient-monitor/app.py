from flask import Flask, render_template, url_for
# from flask import Flask, request, render_template, url_for, redirect
import matplotlib.pyplot as plt
import numpy as np


# from sample_data.red_data import red_diode_data


# ***************************************************************************
# ***************************************************************************
# ***************************************************************************

import pandas as pd
import matplotlib.animation as animation 

plt.style.use('fivethirtyeight')

def animate(i):

    data = pd.read_csv('sample_data/data.csv')
    x = data['x_value']
    red = data['red_data']
    ir = data['ir_data']

    plt.cla()

    plt.plot(x, red, label='Red Photodiode')
    plt.plot(x, ir, label='IR Photodiode')

    plt.legend(loc='upper left')
    plt.xlabel("")
    plt.xticks([])
    plt.tight_layout()

# ani = animation.FuncAnimation(plt.gcf(), animate)
ani = animation.FuncAnimation(plt.gcf(), animate, interval=10)
plt.tight_layout()
plt_data = plt.show()



# ***************************************************************************
# ***************************************************************************
# ***************************************************************************




app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return url_for('static', filename='images/favicon.ico')

@app.route('/')
def display_home():


    return render_template('index.html', plt_data=plt_data)