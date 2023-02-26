# entry point to DHCP Client for testing

import random
import time

import socket
from multiprocessing import Process

import psutil
from getmac import get_mac_address

from scapy.all import AsyncSniffer, Packet
from scapy.layers.dhcp import Ether, IP, UDP, BOOTP, DHCP, sendp

from src.lib.config import config

def get_address() -> dict[str, tuple[str, str]]:
    addresses: dict[str, tuple[str, str]] = {}

    nics = psutil.net_if_addrs()
    for nicsName in nics:
        for item in nics[nicsName]:
            if item.family == socket.AddressFamily.AF_INET:
                addresses[nicsName] = (get_mac_address(interface=nicsName), item.address)

    return addresses


def mac_to_bytes(mac_addr: str) -> bytes:
    return int(mac_addr.replace(":", ""), 16).to_bytes(6, "big")


def send_dhcp_discover(client_mac: str, iface: str):
    packet = (
        Ether(dst="ff:ff:ff:ff:ff:ff") /
        IP(src="0.0.0.0", dst="255.255.255.255") /
        UDP(sport=68, dport=67) /
        BOOTP(
            chaddr=mac_to_bytes(client_mac),
            xid=random.randint(1, 2**32-1),
        ) / DHCP(options=[("message-type", "discover"), "end"])
    )
    sendp(packet, iface=iface, verbose=False)


def sniffer_handler(packet: Packet):
    print(packet)
    packet.display()

    bootpLayer: BOOTP = packet.getlayer(3)
    dhcpLayer: DHCP = packet.getlayer(4)

    options = {}

    for option in dhcpLayer.options:
        if option == "end":
            break

        options[option[0]] = option[1]

    if "message-type" not in options:
        return None

    if options["message-type"] == 2:
        # DHCP Offer packet
        fields = ['subnet_mask', 'router', 'name_server']
        for field in fields:
            if field not in options:
                print("The field {} is missing!".format(field))
                return None

        subnetMask, gatway, dns = options['subnet_mask'], options['router'], options['name_server']

        print("IP: {}, Mask: {}, Gatway: {}, DNS: {}".format(bootpLayer.yiaddr, subnetMask, gatway, dns))

def main() -> None:

    sniffer = AsyncSniffer(prn=sniffer_handler, filter="udp port 67", store=False)

    addresses = get_address()
    for iface in addresses:
        mac_address, ip_address = addresses[iface]

        print(iface, mac_address, ip_address)

        sniffer.start()
        send_dhcp_discover(mac_address, iface)
        time.sleep(5)
        sniffer.stop()


if __name__ == "__main__":
    main()
