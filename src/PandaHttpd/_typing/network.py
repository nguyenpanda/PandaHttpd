from typing import Union
from socket import socket as Socket
from ipaddress import IPv4Network, IPv6Network


NetworkType = Union[IPv4Network, IPv6Network]
IPAddress = Union[str, IPv4Network, IPv6Network]
PortType = int
SocketAddress = tuple[IPAddress, PortType]
