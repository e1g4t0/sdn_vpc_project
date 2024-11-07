from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI

NUMBER_OF_HOSTS = 5
NUMBER_OF_VPC = 2

def topo():

    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch)
    net.addController("c", controller=RemoteController, ip='127.0.0.1', port=6633)
    list = []
    s = net.addSwitch("s0")

    for i in range(NUMBER_OF_VPC):
        for j in range(NUMBER_OF_HOSTS):
            h = net.addHost("h_" + str(i) + "." + str(j), ip='10.0.{0}.{1}/16'.format(str(i), str(j)))
            net.addLink(s, h)
            list.append(h)

    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    topo()