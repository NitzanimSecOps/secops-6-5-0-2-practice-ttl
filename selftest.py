"""selftest.py — run your router locally and watch it handle TTL.

    python selftest.py          # run the example scenarios below
    VS Code: open this file, press F5 (Run and Debug), set breakpoints in host.py.

No real network is needed: this replaces the router's socket factory with a recorder, so
process_packet runs anywhere. It builds IPv4 packets, sends them into your router with
send(), and prints what your code printed and (for a forwarded packet) the TTL that went
out. Edit the scenarios at the bottom, or call send() with your own packets.
"""
import struct

import host as host_module          # your solution's module
from host import Host
from routing import RouteEntry

ROUTER = ("10.0.0.1", "02:00:00:00:00:01")   # (ip, mac)
LAN_HOST = ("10.0.1.5", "02:00:00:00:00:05")  # a machine behind the router, via eth1
ETH_HEADER_LEN = 14
TTL_OFFSET = 8

_SENT = []


class _FakeSock:
    def send(self, data):
        _SENT.append(data)
        return len(data)

    def close(self):
        pass


def _ip(ip):
    return bytes(int(o) for o in ip.split("."))


def ipv4(src, dst, ttl, payload=b"hello"):
    """Build a minimal IPv4 packet (20-byte header + payload)."""
    total_length = 20 + len(payload)
    header = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total_length, 0, 0, ttl, 6, 0,
                         _ip(src), _ip(dst))
    return header + payload


def new_router():
    """A Host whose forwarding uses a fake socket, with one route + ARP entry set up."""
    host_module.make_socket = lambda interface: _FakeSock()   # no real NIC needed
    r = Host(*ROUTER)
    r.routing_table.add_route(RouteEntry("10.0.1.0", "255.255.255.0", None, "eth1"))
    r.arp_table.learn(LAN_HOST[0], LAN_HOST[1])
    return r


def send(r, packet, label=""):
    """Send one packet into the router, and show what happened."""
    _SENT.clear()
    print(f"\n>>> {label or 'send'}")
    r.process_packet(packet)                               # <-- your code runs here; breakpoint it
    if _SENT:
        out_ttl = _SENT[-1][ETH_HEADER_LEN + TTL_OFFSET]
        print(f"    forwarded — TTL on the wire is now {out_ttl}")
    else:
        print("    nothing forwarded (delivered locally or dropped)")


if __name__ == "__main__":
    r = new_router()

    send(r, ipv4("10.0.2.2", LAN_HOST[0], ttl=64), "transit packet, TTL 64")
    send(r, ipv4("10.0.2.2", LAN_HOST[0], ttl=1), "transit packet, TTL 1 (last hop)")
    send(r, ipv4("10.0.2.2", ROUTER[0], ttl=1), "packet addressed to the router itself, TTL 1")
    send(r, ipv4("10.0.2.2", "9.9.9.9", ttl=64), "packet with no route")

    print("\nExpected: TTL 64 forwards with 63 on the wire; TTL 1 transit is dropped (no forward);")
    print("the one addressed to the router is delivered (TTL ignored); no-route is dropped.")
    print("Edit the scenarios above, or call send(r, ipv4(src, dst, ttl), 'label').")
