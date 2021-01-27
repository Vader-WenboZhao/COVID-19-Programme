import matplotlib.pyplot as plt
x=range(2,9)
y=[0, 0, 2/100, 10/125, 17/150, 24/175, 29/200]
plt.plot(x,y)
# plt.plot(x,y,label='',linewidth=1, color='r', marker='r')
plt.xlabel('Number of concurrent mobile devices')
plt.ylabel('Packet loss rate')
plt.title('Packet loss rate - number of concurrent mobile devices')
plt.legend()
plt.show()
