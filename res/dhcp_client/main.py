# entry point to DHCP Client for testing

import random
import time

import socket
from multiprocessing import Process

import psutil
from getmac import get_mac_address

from scapy.all import Packet, AsyncSniffer, sniff, PacketList
from scapy.layers.dhcp import Ether, IP, UDP, BOOTP, DHCP, sendp

import socket
import psutil
ifaces = psutil.net_if_addrs()
ips = []
for iface in ifaces:
    for item in ifaces[iface]:
        if item.family == socket.AddressFamily.AF_INET:
            ips += [item.address]


def sniffer_handler(packet: Packet):
    print(packet)

    bootpLayer: BOOTP = packet[BOOTP]
    dhcpLayer: DHCP = packet[DHCP]

    options = {}

    for option in dhcpLayer.options:
        if option == "end":
            break

        options[option[0]] = option[1]

    if "message-type" not in options:
        return None

    if options["message-type"] == 2:
        # DHCP Offer packet
        packet.display()

        print("IP: {}".format(bootpLayer.yiaddr))

        fields = ['subnet_mask', 'router']
        for field in fields:
            if field not in options:
                print("The field {} is missing!".format(field))
                return None

        subnetMask, gatway = options['subnet_mask'], options['router']
        dns = None
        if 'name_server' in options:
            dns = options['name_server']

        print("IP: {}, Mask: {}, Gatway: {}, DNS: {}".format(bootpLayer.yiaddr, subnetMask, gatway, dns))

def random_mac():
    return "%02x:%02x:%02x:%02x:%02x:%02x" % (
        random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255),
        random.randint(0, 255), random.randint(0, 255))

def main() -> None:
    iface, client_mac, = "wlp0s20f3", "78:2b:46:10:2e:c1"

    client_mac = random_mac()
    sender.send_discover(iface, client_mac)
    pkts = sender.receive_offer(iface)
    print(pkts[0])

    while False:
        packets: PacketList = sniff(filter="port 68 and port 67")
        packet: Packet = packets.res[0]

        sniffer_handler(packets)

if __name__ == "__main__":
    main()
