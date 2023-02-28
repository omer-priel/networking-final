from scapy.layers.dhcp import BOOTP, DHCP
from scapy.layers.inet import UDP, IP, ICMP
from scapy.layers.l2 import Ether
from scapy.sendrecv import sendp, sniff


def send_discover(iface: str, src_mac: str):
    pkt = Ether(dst='ff:ff:ff:ff:ff:ff', src=src_mac, type=0x0800) / IP(src='0.0.0.0', dst='255.255.255.255') / \
          UDP(dport=67, sport=68) / BOOTP(op=1, chaddr=src_mac) / DHCP(options=[('message-type', 'discover'), 'end'])
    sendp(pkt, iface=iface)


def receive_offer(iface: str):
    # pkt[DHCP].options[0][1] == 2 -> first option (message type) => offer
    return sniff(iface=iface, filter="port 68 and port 67",
                 stop_filter=lambda pkt: BOOTP in pkt and pkt[BOOTP].op == 2 and pkt[DHCP].options[0][1] == 2,
                 timeout=5)


def send_request(iface: str, src_mac: str, request_ip: str, server_ip: str):
    pkt = Ether(dst='ff:ff:ff:ff:ff:ff', src=src_mac, type=0x0800) / IP(src='0.0.0.0', dst='255.255.255.255') / \
          UDP(dport=67, sport=68) / BOOTP(op=1, chaddr=src_mac) / \
          DHCP(options=[('message-type', 'request'), ("client_id", src_mac), ("requested_addr", request_ip),
                        ("server_id", server_ip), 'end'])
    sendp(pkt, iface=iface)


def receive_acknowledge(iface: str, ):
    # pkt[DHCP].options[0][1] == 5 -> first option (message type) => ack
    return sniff(iface=iface, filter="port 68 and port 67",
                 stop_filter=lambda pkt: BOOTP in pkt and pkt[BOOTP].op == 2 and pkt[DHCP].options[0][1] == 5,
                 timeout=5)


def send_test_ip(iface: str, src_mac: str, src_ip: str, dst_mac: str, dst_ip: str):
    pkt = Ether(src=src_mac, dst=dst_mac) / IP(src=src_ip, dst=dst_ip) / ICMP()
    sendp(pkt, iface=iface)
