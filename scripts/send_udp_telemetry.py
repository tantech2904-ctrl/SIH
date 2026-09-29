#!/usr/bin/env python3
"""Send sample Syslog UDP telemetry to ULPF on port 5140.

Demonstrates real network log ingestion via UDP datagrams.
"""
import socket
import time
import sys

SAMPLE_LOGS = [
    # RFC 5424 structured syslog
    b"<34>1 2026-09-28T02:20:00.000Z edge-fw01 sudo - - - [auth user=\"admin\" src_ip=\"192.168.1.105\"] User executed /bin/bash as root",
    # RFC 3164 BSD syslog
    b"<13>Sep 28 02:20:05 core-switch sshd[4091]: Failed password for invalid user root from 203.0.113.195 port 54822 ssh2",
    # Firewall drop event
    b"<4>Sep 28 02:20:10 perimeter-pfsense filterlog[112]: 4,,,1000000103,em0,match,block,in,4,0x0,,64,0,0,DF,6,tcp,44,198.51.100.44,192.168.1.1,49152,445,0,S,1024,,",
    # Web server access log
    b"<134>Sep 28 02:20:15 nginx-gateway nginx: 198.51.100.77 - - [28/Sep/2026:02:20:15 +0000] \"GET /admin/config.php HTTP/1.1\" 403 162 \"-\" \"curl/7.88.1\"",
    # Suricata network alert
    b'{"timestamp":"2026-09-28T02:20:20.123Z","event_type":"alert","src_ip":"198.51.100.88","src_port":4444,"dest_ip":"192.168.1.50","dest_port":80,"alert":{"action":"blocked","signature":"ET MALWARE Metasploit Meterpreter Reverse TCP","severity":1}}',
]


def send_telemetry(host="127.0.0.1", port=5140, count=5, delay=0.3):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[*] Sending {count} Syslog UDP datagrams to {host}:{port}...")
    sent = 0
    for i in range(count):
        msg = SAMPLE_LOGS[i % len(SAMPLE_LOGS)]
        sock.sendto(msg, (host, port))
        sent += 1
        print(f" [+] Datagram {sent}/{count} sent ({len(msg)} bytes) -> {msg[:60].decode('utf-8', errors='ignore')}...")
        if delay > 0:
            time.sleep(delay)
    sock.close()
    print(f"[OK] Successfully transmitted {sent} UDP packets to ULPF listener.")


import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send sample Syslog UDP telemetry to ULPF")
    parser.add_argument("--host", default="127.0.0.1", help="Target host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5140, help="Target UDP port (default: 5140)")
    parser.add_argument("--count", type=int, default=5, help="Number of telemetry packets to send (default: 5)")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between packets in seconds (default: 0.2)")
    args = parser.parse_args()

    send_telemetry(host=args.host, port=args.port, count=args.count, delay=args.delay)
