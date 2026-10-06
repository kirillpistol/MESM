#!/usr/bin/env python3
"""Печатает первый свободный порт 8501-8510 на 127.0.0.1 (если все заняты - 8501)."""
import socket

for port in range(8501, 8511):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", port)) != 0:
            print(port)
            break
else:
    print(8501)
