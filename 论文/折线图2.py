import matplotlib.pyplot as plt
x=[180, 240, 300, 360, 420, 480]
y=[0, 0.0019,	0.1536,	0.5195,	1.0798,	1.4630]
plt.plot(x,y)
# plt.plot(x,y,label='',linewidth=1, color='r', marker='r')
plt.xlabel('Number of people inside the building')
plt.ylabel('R')
plt.title("Don't know how to name this table")
plt.legend()
plt.show()
