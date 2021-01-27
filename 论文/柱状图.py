# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt

X=[1,2,3,4,5,6,7,8]
Y=[0/50, 1/50, 0/50, 3/50, 4/50, 6/50, 7/50, 5/50]
fig = plt.figure()
plt.bar(X,Y,0.6)
plt.xlabel("Region number")
plt.ylabel("Packet loss rate")
plt.title("Packet loss rate - Region number")


plt.show()
plt.savefig("barChart.jpg")
