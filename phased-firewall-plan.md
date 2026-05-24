# Phased firewall plan

Summary of services (IPs, ports, public exposure):

| Service | IP / Host | Port (proto) | Public? | Notes |
|---|---|---:|---:|---|
| VyOS management (SSH) | WAN (eth0 public IP) | 22 (tcp) | Yes | WAN SSH allow present in live config |
| Existing WireGuard listener (`wg0`) | 192.168.11.106 (DMZ WG host) | 51820 (udp) | Yes | PiVPN on DMZ host; NAT/MASQUERADE remains in Phase 1 |
| Current wg-portal UI | 192.168.11.104 (DMZ web host) | 8888 (tcp) | Yes | Local portal UI (current deployment)
| REST service `scriptum` | 192.168.11.104 (DMZ web host) | 8080 (tcp) | Yes | Internal REST endpoint used by services
| Library API (HTTP) | 192.168.11.104 (DMZ web host) | 3000 (tcp) | No | Library API (HTTP)
| Library API (HTTPS) | 192.168.11.104 (DMZ web host) | 3443 (tcp) | Yes | Library API (HTTPS)
| Library API (GraphQL) | 192.168.11.104 (DMZ web host) | 32484 (tcp) | No | Library GraphQL endpoint (internal)
| DMZ DNS | 192.168.11.105 | 53 (udp/tcp) | No | Internal → DMZ DNS rules (internal clients only)
| AD DNS | 192.168.11.201 (AD), 2001:1470:fffd:a9::185 | 53 (udp/tcp) | No | Client/server AD name resolution (from `v4.conf` rules)
| AD Kerberos | 192.168.11.201 (AD), 2001:1470:fffd:a9::185 | 88 (tcp/udp) | No | Domain authentication / ticketing
| AD LDAP | 192.168.11.201 (AD), 2001:1470:fffd:a9::185 | 389 (tcp/udp) | No | Directory queries and joins
| AD Global Catalog | 192.168.11.201 (AD), 2001:1470:fffd:a9::185 | 3268, 3269 (tcp) | No | Forest-wide lookups / logon support
| AD SMB/RPC/time/kpasswd | 192.168.11.201 (AD), 2001:1470:fffd:a9::185 | 135, 123, 445, 464 (tcp/udp) | No | Group policy, RPC endpoint mapping, time sync, Kerberos password ops
| AD Dynamic RPC | 192.168.11.201 (AD), 2001:1470:fffd:a9::185 | 49152-65535 (tcp) | No | AD RPC high ports required by many management/auth flows
| DMZ SNMP target | VyOS router (DMZ) — 192.168.11.1 | 161 (udp) | No | SNMP enabled on VyOS (listen 192.168.11.1); exporter scrapes this target
| Prometheus (monitoring) | 192.168.11.107 (DMZ monitoring host) | 9090 (tcp) | No | Prometheus scrape UI/service (scrapes exporter)
| snmp_exporter | 192.168.11.107 (DMZ monitoring host) | 9116 (tcp) | No | Exporter endpoint for Prometheus (`/snmp`), scrapes VyOS at 192.168.11.1
| Grafana | 192.168.11.107 (DMZ monitoring host) | 3000 (tcp) | No | Grafana UI for dashboards
| Windows DMZ management (RDP) | 192.168.11.201 | 3389 (tcp) | No | Management allowed only from admin WG (`wg0`)
| DMZ SSH (blanket) | 192.168.11.0/24 + wg0 via 192.168.11.106 | 22 (tcp) | No | SSH allowed only from DMZ peers or WireGuard (via 192.168.11.106)

This table contains only services present in Phase 1 (current deployment). Phase 2 items are described later in the document.

## DHCP mappings

The current VyOS configuration uses static DHCP mappings for the DMZ and related hosts. These are the current IPv4 and IPv6 mappings that should remain stable:

| Host | DHCPv4 address | DHCPv6 address | DHCPv6 DUID / identifier | Notes |
|---|---|---|---|---|
| dmz-windows-AD | 192.168.11.201 | 2001:1470:fffd:a9::185 | 00:01:00:01:31:86:a4:b0:00:0c:29:07:cf:26 | AD / Windows server |
| dns-srv | 192.168.11.105 | - | - | DMZ DNS server |
| raft1 | 192.168.11.101 | 2001:1470:fffd:a9::124 | 00:02:00:00:ab:11:2b:e2:d4:90:70:f3:b3:37 | DMZ server |
| raft2 | 192.168.11.102 | 2001:1470:fffd:a9::114 | 00:02:00:00:ab:11:e1:94:d4:8a:18:52:ad:98 | DMZ server |
| raft3 | 192.168.11.103 | 2001:1470:fffd:a9::16b | 00:02:00:00:ab:11:92:37:c8:9a:00:b8:67:77 | DMZ server |
| rest | 192.168.11.104 | 2001:1470:fffd:a9::115 | 00:02:00:00:ab:11:5a:9d:49:65:ce:4a:b2:48 | REST / web service |
| snmp | 192.168.11.107 | 2001:1470:fffd:a9::17a | 00:02:00:00:ab:11:b8:b7:97:e3:eb:3c:a5:52 | SNMP-managed host |
| wg | 192.168.11.106 | 2001:1470:fffd:a9::1c8 | 00:02:00:00:ab:11:80:f9:48:e8:e6:e2:12:59 | WireGuard host |
| new_wg | 192.168.11.108 | 2001:1470:fffd:a9::18d | 00:02:00:00:ab:11:dd:e2:8d:62:21:b3:d9:00 | New WireGuard-related host |

For the IPv6-only mapping set, `wg` is the current name used in `v5.5.conf` for `2001:1470:fffd:a9::1c8`.

## Network assumptions

- WAN / public interface: `eth0`
- DMZ: `eth1`, subnet `192.168.11.0/24`
- INTERNAL: `eth2`, subnet `10.11.0.0/24`
- IPV6ONLY: `eth3`, subnet `fd11:11:11::/64`
- Existing admin WireGuard tunnel: `wg0`, subnet `10.4.103.0/24`, UDP `51820`
- WireGuard host: Ubuntu server in DMZ at `192.168.11.106`

Important: because the WG host currently MASQUERADEs VPN traffic, VyOS will usually see forwarded VPN traffic as coming from `192.168.11.106`, not from the original WireGuard subnet. That means admin/client separation is enforced on the WG host itself until the later migration to a non-PiVPN VM.

## Phase 1: keep PiVPN/NAT as-is, firewall everything else

Goal: preserve the working `wg0` admin tunnel, harden VyOS, harden all hosts, and include `ipv6only` in the firewall plan.

### 1. VyOS baseline firewall

v5.5.conf summary

The `v5.5.conf` firewall implements a least‑access policy with explicit, numbered rules and a default deny stance. Key points:

- **Default policy:** all `forward`/`input` filters use `default-action "drop"` and rely on explicit `accept` rules.
- **Stateful baseline:** rule `1` permits `ESTABLISHED,RELATED` traffic to allow responses for permitted flows.
- **Rule numbering convention:** public DNAT/forward rules live in the `100-149` range (WAN→DMZ DNAT/allow), internal→server allow rules in the `200-299` range, DMZ east‑west exceptions in the `300-399` range, and IPv6‑only rules mirrored in the `400`+ range. This makes audits and deltas predictable.
- **DNAT (public services):** nat destination rules map explicit WAN ports to DMZ hosts (examples: UDP 51820 → `192.168.11.106`; TCP 8888 → `192.168.11.104`; TCP 8080/3443/32484 → `192.168.11.104` where applicable). Corresponding forward rules accept traffic only for those translated destinations and protocols.
- **Internal-to-DMZ:** internal subnets are allowed only the specific services they need (DNS, LDAP/Kerberos/GC/SMB/RPC/time and AD dynamic high ports to the AD server). These are implemented as specific `accept` entries (rules starting at `210`) that restrict destination address/port and inbound/outbound interfaces.
- **DMZ SSH policy:** a blanket DMZ SSH rule allows TCP/22 only from other DMZ hosts and from the WireGuard host (`192.168.11.106`) to support admin access while PiVPN NAT is still present.
- **SNMP / monitoring:** Prometheus + `snmp_exporter` scrape the VyOS SNMP target (`192.168.11.1:161`). The firewall allows scraping from the monitoring host `192.168.11.107` to VyOS and allows the exporter (DMZ) outbound to reach VyOS; exporter UI is reachable on `192.168.11.107:9116` for testing.
- **Masquerade / NAT:** source NAT (masquerade) rules remain for INTERNAL and DMZ outbound to the Internet. The existing WireGuard PiVPN NAT rule is intentionally preserved in Phase 1 so VyOS continues to see VPN administration traffic as coming from `192.168.11.106`.
- **DHCPv6 / RA:** the DHCPv6 server and router‑advertisement blocks from `v4.conf` are preserved verbatim in `v5.5.conf` so static IPv6 assignments (DUID mappings) remain stable.
- **IPv6 mirror:** equivalent IPv6 filters mirror IPv4 allow rules where services are dual‑stack; IPv6‑only services live in a separate rule range to keep policies clear.

Operational notes:

- Audit by rule range: check `100-149` for WAN exposure, `200-299` for internal→DMZ access, and `300-399` for intra-DMZ exceptions. Use `show configuration commands | match "firewall ipv4"` on VyOS to confirm rule numbers.
- When adding a public service, create a nat destination rule and a paired forward rule in the `1xx` range, and document the DNAT translation in this plan.

### 2. Ubuntu DMZ WireGuard host: keep `wg0` as admin tunnel with NAT

Do not change the existing PiVPN behavior in phase 1. Keep `wg0` as the admin tunnel and keep its current MASQUERADE rules.

```bash
sudo iptables -L
sudo iptables -t nat -L
sudo wg show
```

Test from:
- On the WG host itself: run the commands above to confirm NAT and forwarding are still active.
- From an admin VPN peer connected to `wg0`: `ping 192.168.11.1`, `ping 10.11.0.1`, `ping fd11:11:11::1`

Expected result:
- `wg0` still gives full admin access during phase 1.
- The current NAT remains in place and is treated as the source of truth until phase 2.

Reference from the current WG host:

```text
sudo iptables -L
sudo iptables -t nat -L
sudo wg show

Chain INPUT (policy ACCEPT)
Chain FORWARD (policy ACCEPT)
Chain OUTPUT (policy ACCEPT)
Chain PREROUTING (policy ACCEPT)
Chain POSTROUTING (policy ACCEPT)
MASQUERADE  all  --  10.4.103.0/24        anywhere             /* wireguard-nat-rule */

interface: wg0
	listening port: 51820
	peer: ...
```

Test from:
- On the WG host: `sudo iptables -t nat -L -n -v`, `sudo wg show`
- From an admin peer on `wg0`: `ping 192.168.11.1`, `ping 10.11.0.1`, `ping fd11:11:11::1`

Expected result:
- The NAT rule for `10.4.103.0/24` stays in place for now.
- `wg0` remains the full-access admin tunnel until phase 2.

### 3. Ubuntu DMZ WireGuard host: protect the host itself

Because NAT is kept, admin and client separation is done on the WG host. The WG host must not be reachable from `wg0` except for the services you explicitly allow.

```bash
# Allow established connections
sudo iptables -I INPUT 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow the WireGuard listener itself
sudo iptables -I INPUT 2 -p udp --dport 51820 -j ACCEPT

# Optional SSH access only from internal management network
sudo iptables -I INPUT 3 -p tcp -s 10.11.0.0/24 --dport 22 -j ACCEPT

# Drop direct access from the WG tunnel to the host itself
sudo iptables -I INPUT 4 -i wg0 -j DROP

# IPv6 mirror if the host exposes IPv6 services
sudo ip6tables -I INPUT 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo ip6tables -I INPUT 2 -i wg0 -j DROP
```

Test from:
- From an admin peer on `wg0`: `ssh 192.168.11.106`, `curl http://192.168.11.106:8888`, `ping 192.168.11.106`
- From the WG host itself: `sudo iptables -L INPUT -n --line-numbers`, `sudo ip6tables -L INPUT -n --line-numbers`

Expected result:
- `wg0` users can use the tunnel but cannot reach the WG host's management ports unless explicitly allowed.
- The WG host remains reachable only on the ports you intentionally open.

### 4. DMZ servers: management only from admin WG

The DMZ servers should only accept administration from the existing admin tunnel (`wg0`). Do not expose management directly to WAN.

#### Windows Server in DMZ

```powershell
New-NetFirewallRule -DisplayName "Allow RDP from admin WG" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3389 -RemoteAddress 10.4.103.0/24
New-NetFirewallRule -DisplayName "Allow SSH from admin WG" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 22 -RemoteAddress 10.4.103.0/24
New-NetFirewallRule -DisplayName "Allow SNMP from internal monitoring" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 161 -RemoteAddress 10.11.0.0/24
```

Test from:
- From an admin peer on `wg0`: `Test-NetConnection 192.168.11.201 -Port 3389`, `Test-NetConnection 192.168.11.201 -Port 22`
- From a WAN host: same tests should fail

Expected result:
- RDP/SSH/SNMP work only from the allowed source ranges.

#### Ubuntu / Linux server in DMZ

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 10.4.103.0/24 to any port 22 proto tcp
sudo ufw allow from 10.4.103.0/24 to any port 443 proto tcp
sudo ufw allow from 10.11.0.0/24 to any port 161 proto udp
sudo ufw enable
```

Test from:
- From an admin peer on `wg0`: `ssh 192.168.11.104`, `curl -I https://192.168.11.104`
- From the internal monitoring host: `snmpwalk -v2c -c <community> 192.168.11.1`

Expected result:
- Only approved admin/monitoring sources can reach the services.

### 5. Internal client machines: RDP allowed through WireGuard, not from LAN

Windows and Ubuntu client machines should be reachable by RDP through WireGuard. In phase 1 that means `wg0` admin users can RDP to them. Keep direct LAN exposure closed unless you explicitly need it.

Because the current PiVPN host NATs VPN traffic, the client machines will usually see the WG host DMZ IP as the source, not the original `wg0` subnet. In phase 1, the temporary firewall allow-list should therefore trust the WG host address that the clients actually see.

#### Windows client machines

```powershell
New-NetFirewallRule -DisplayName "Allow RDP from WG host" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3389 -RemoteAddress 192.168.11.106
# If IPv6 is also NATed/translated in your setup, allow the WG host IPv6 that the client sees.
# New-NetFirewallRule -DisplayName "Allow RDP from WG host IPv6" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3389 -RemoteAddress <wg-host-ipv6>
```

Test from:
- From an admin peer on `wg0`: `Test-NetConnection <client-ip> -Port 3389`
- From the Windows client itself: `Get-NetFirewallRule -DisplayName "Allow RDP from WG host"`

Expected result:
- RDP works through the VPN and is blocked from unauthorized sources.

#### Ubuntu client machines

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.11.106 to any port 22 proto tcp
sudo ufw allow from 192.168.11.106 to any port 3389 proto tcp
# If IPv6 is translated or routed differently, add the source that the host actually sees.
# sudo ufw allow from <wg-host-ipv6> to any port 22 proto tcp
# sudo ufw allow from <wg-host-ipv6> to any port 3389 proto tcp
sudo ufw enable
```

Test from:
- From an admin peer on `wg0`: `ssh <ubuntu-client-ip>`, `xfreerdp /v:<ubuntu-client-ip>` if RDP is enabled
- From the Ubuntu client itself: `sudo ufw status numbered`

Expected result:
- SSH and RDP are available only through the VPN sources you allowed.

### 6. IPv6-only segment: keep it separate and reachable only by policy

`ipv6only` must remain IPv6-only, with no IPv4 leakage.

```bash
# On VyOS, keep IPv6 routing for the segment
show ipv6 route

# On the IPv6-only hosts, only allow required inbound traffic
sudo ip6tables -I INPUT 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo ip6tables -I INPUT 2 -p tcp --dport 22 -s fd11:5ee:bad:c0de::/64 -j ACCEPT
sudo ip6tables -I INPUT 3 -p tcp --dport 3389 -s fd11:5ee:bad:c0de::/64 -j ACCEPT
sudo ip6tables -A INPUT -j DROP
```

Test from:
- From an admin peer on `wg0`: `ping6 fd11:11:11::1`, `ssh <ipv6only-host>`, `Test-NetConnection -ComputerName <ipv6only-host> -Port 3389`
- From the IPv6-only host itself: `ip -6 addr`, `ip -6 route`

Expected result:
- IPv6-only hosts remain IPv6-only and are accessible only through the allowed admin paths.

## Phase 2 — Consolidated chronological Phase 2 (all steps)

Goal: migrate from the PiVPN-based host to a fresh DMZ VM running `wg-portal` in `/opt`, introduce `wg-admin` and `wg-client`, have VyOS enforce segmentation, and perform a safe cutover with rollback.

Scope & constraints
- Keep the existing PiVPN VM (`wg0`) unchanged and available as rollback until cutover completes.
- Avoid using `10.11.*` portal-managed pools; this plan uses `10.200.12.0/24` (admin) and `10.200.13.0/24` (client) by default.
- Prefer manual interface creation (wg-quick import or UI/API) to reduce reliance on in-file `servers`/`profiles` which may vary by wg-portal release.

Chronological Steps

Step 0 — Prep & decisions (what to choose before touching VMs)
- Pick the new VM DMZ IP: `<NEW_VM_DMZ_IP>`.
- Choose wg-portal release tarball URL: `<WGPORTAL_RELEASE_TARBALL_URL>`.
- Gather LDAP/AD settings (bind user, secure bind password, AD servers, admin group DN). Keep sensitive secrets out of repo; fill them on the VM.
- Confirm chosen portal-managed CIDRs: `10.200.12.0/24` and `10.200.13.0/24`.

Step 1 — Build the VM and baseline hardening

On the new Ubuntu DMZ VM:

```bash
sudo apt update
sudo apt install -y wireguard wireguard-tools iptables-persistent netfilter-persistent curl unzip ufw
sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv6.conf.all.forwarding=1
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding=1' | sudo tee -a /etc/sysctl.conf
```

- Configure basic firewall (UFW example): allow WG ports and portal web UI (adjust ports/tls as needed):

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 51820/udp   # wg-admin
sudo ufw allow 51821/udp   # wg-client
sudo ufw allow 8080/tcp    # wg-portal UI (change if using TLS/reverse proxy)
sudo ufw enable
```

Step 2 — Install wg-portal into `/opt` and systemd unit

- Copy `install-wgportal-phase2.sh`, `wg-portal.service`, and `wgportal-phase2-config.yml` to the VM (use SCP or `git clone` the repo there).
- Run the installer with the release URL and the local path to the config. The installer will:
	- create `wgportal` system user
	- extract files into `/opt/wg-portal`
	- place config at `/etc/wg-portal/config.yml`
	- create `/var/lib/wg-portal/data` and set ownership
	- install and enable `wg-portal` systemd unit

Example (on VM):

```bash
sudo mv /tmp/wg-portal.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/wg-portal.service
sudo chmod +x /tmp/install-wgportal-phase2.sh
sudo /tmp/install-wgportal-phase2.sh "<WGPORTAL_RELEASE_TARBALL_URL>" /tmp/wgportal-phase2-config.yml
sudo systemctl daemon-reload
sudo systemctl enable --now wg-portal
sudo journalctl -u wg-portal -f
```

Step 3 — Configure secrets and external URL

- Edit `/etc/wg-portal/config.yml` on the VM and:
	- set `auth.ldap[0].bind_pass` to the LDAP bind password (do not store this in the repo)
	- set `web.external_url` → `http://<NEW_VM_DMZ_IP>:8080` (or your reverse proxy/TLS URL)
	- confirm `database.dsn` points to `/var/lib/wg-portal/data/phase2.sqlite.db` (or external DB)
- Restart and verify logs:

```bash
sudo systemctl restart wg-portal
sudo journalctl -u wg-portal -f
```

Step 4 — Decide interface management method (A or B)

- Method A (recommended when you need server-side hooks): create server interfaces locally with `wg-quick` on the VM, then import into wg-portal.
- Method B (recommended if you want wg-portal to manage lifecycle entirely): create interfaces in the wg-portal UI or via its API.

Step 5A — Method A: create `/etc/wireguard` server files and bring them up

Example `/etc/wireguard/wg-admin.conf` (server):

```ini
[Interface]
Address = 10.200.12.1/24, fdfd:d3ad:c0de:2345::1/64
ListenPort = 51820
PrivateKey = <SERVER_PRIVATE_KEY>
SaveConfig = true
# PostUp = iptables -t nat -A POSTROUTING -s 10.200.12.0/24 -o eth1 -j MASQUERADE
# PostDown = iptables -t nat -D POSTROUTING -s 10.200.12.0/24 -o eth1 -j MASQUERADE
```

Example `/etc/wireguard/wg-client.conf` (server):

```ini
[Interface]
Address = 10.200.13.1/24, fdfd:d3ad:c0de:3456::1/64
ListenPort = 51821
PrivateKey = <SERVER_PRIVATE_KEY>
SaveConfig = true
```

Bring up and persist:

```bash
sudo systemctl enable --now wg-quick@wg-admin
sudo systemctl enable --now wg-quick@wg-client
```

- In the wg-portal UI go to Admin → Interfaces → Import existing interfaces (or set `import_existing: true` in config and restart) to link these `wg-quick` interfaces to the portal.

Step 5B — Method B: create interfaces via wg-portal UI or API

- Log in as admin and create `wg-admin` (listen 51820, pool `10.200.12.0/24`) and `wg-client` (listen 51821, pool `10.200.13.0/24`).
- If using the API, use the portal's OpenAPI (or REST endpoints) to create interfaces programmatically (I can generate curl examples once the service is reachable).

Step 6 — Profiles, provisioning, and LDAP controls

- Create two profiles:
	- `Admin` profile: permitted on `wg-admin` and `wg-client`; broader Allowed IPs as required for admin tasks.
	- `Client` profile: permitted only on `wg-client`; Allowed IPs restricted to INTERNAL and IPV6ONLY ranges.
- Use `auth.ldap.interface_filter` (configured in `wgportal-phase2-config.yml`) to restrict who can provision on `wg-admin` (e.g., Domain Admins).
- Verify LDAP group mapping and perform a test LDAP login from the portal UI.

Step 7 — VyOS routing & firewall updates (make the router authoritative)

- Apply only the missing VyOS deltas for the Phase 2 cutover. Keep the current SSH/public services already present in `v4.conf`; add the new portal exposure and routing entries below when you move to the new VM.

```text
configure

# New WireGuard portal exposure on the fresh VM
set nat destination rule 21 description 'wgportal-admin'
set nat destination rule 21 destination port '51820'
set nat destination rule 21 inbound-interface name 'eth0'
set nat destination rule 21 protocol 'udp'
set nat destination rule 21 translation address '<NEW_VM_DMZ_IP>'

set nat destination rule 22 description 'wgportal-client'
set nat destination rule 22 destination port '51821'
set nat destination rule 22 inbound-interface name 'eth0'
set nat destination rule 22 protocol 'udp'
set nat destination rule 22 translation address '<NEW_VM_DMZ_IP>'

# Allow the new forwarded VPN ports to the DMZ VM
set firewall ipv4 forward filter rule 11 action 'accept'
set firewall ipv4 forward filter rule 11 description 'allow-wgportal-admin'
set firewall ipv4 forward filter rule 11 destination address '<NEW_VM_DMZ_IP>'
set firewall ipv4 forward filter rule 11 destination port '51820'
set firewall ipv4 forward filter rule 11 inbound-interface name 'eth0'
set firewall ipv4 forward filter rule 11 outbound-interface name 'eth1'
set firewall ipv4 forward filter rule 11 protocol 'udp'

set firewall ipv4 forward filter rule 12 action 'accept'
set firewall ipv4 forward filter rule 12 description 'allow-wgportal-client'
set firewall ipv4 forward filter rule 12 destination address '<NEW_VM_DMZ_IP>'
set firewall ipv4 forward filter rule 12 destination port '51821'
set firewall ipv4 forward filter rule 12 inbound-interface name 'eth0'
set firewall ipv4 forward filter rule 12 outbound-interface name 'eth1'
set firewall ipv4 forward filter rule 12 protocol 'udp'

# Router must know the new VPN subnets once peers are created
set protocols static route 10.200.12.0/24 next-hop '<NEW_VM_DMZ_IP>'
set protocols static route 10.200.13.0/24 next-hop '<NEW_VM_DMZ_IP>'

commit
save
exit
```

The concrete router source of truth remains [v4.commands](v4.commands), but the commands above are the missing deltas for the fresh wg-portal VM.

- Update VyOS firewall rules to apply the admin/client segmentation for those subnets (mirror earlier Phase 1 rules but target the portal subnets).

Step 8 — Tests (verify access, enforcement, logging)

- Admin test:
	- Create an admin peer (via UI/API), confirm assigned IP in `10.200.12.0/24`.
	- Verify access to DMZ management hosts, INTERNAL hosts, and IPv6-only resources.

```bash
# on admin client
ping 192.168.11.201
ping 10.11.0.5
ping6 fd11:11:11::1
```

- Client test:
	- Create a client peer, confirm IP in `10.200.13.0/24`.
	- Verify INTERNAL and IPV6ONLY access; verify DMZ management addresses are blocked by VyOS/firewall.

Step 9 — Cutover checklist (final switch)

- Confirm: all tests passed, LDAP mappings correct, portal stable for ≥ your chosen test window.
- Remove MASQUERADE/NAT on the new VM (if you left any temporary NAT in place).
- Ensure VyOS static routes are present and correct; remove any temporary PiVPN-based routing used during testing.
- Decommission or repurpose the PiVPN VM after final validation.

Rollback plan
- If major issues appear, revert VyOS static routes to point VPN subnets back to the PiVPN host, re-enable MASQUERADE there, and restore any temporary firewall exceptions. Keep the PiVPN host running as immediate rollback.

Step 10 — Post-cutover hygiene & monitoring

- Enable log rotation and monitoring for `/var/log/wg-portal` (or systemd journal). Ensure portal health checks (HTTP status, LDAP health, DB size) are monitored.
- Harden the portal host (restrict SSH, apply automatic updates if desired, review `sudo` rules for `wgportal` user).
- Document final IP pools and VyOS config in `phased-firewall-plan.md` and `wgportal-phase2-config.yml`.

Files and references
- Example config: [wgportal-phase2-config.yml](wgportal-phase2-config.yml)
- Installer: [install-wgportal-phase2.sh](install-wgportal-phase2.sh)
- Service unit example: [wg-portal.service](wg-portal.service)
- VyOS command source: [v4.commands](v4.commands)
- Cached docs: `vyos-doc-cache/` (wg-portal docs used to validate keys)

If you want, I will now:
- fill placeholders in `wgportal-phase2-config.yml` if you provide the LDAP bind password and `<NEW_VM_DMZ_IP>`; or
- generate `wg-quick` server templates with PostUp/PostDown rules and a VyOS firewall snippet for admin/client separation.

## Practical order of work

1. Finish phase 1: firewall all existing hosts and keep PiVPN/NAT untouched.
2. Verify RDP and SSH over `wg0` on both Windows and Ubuntu clients.
3. Verify `ipv6only` is still separate and reachable only by policy.
4. Build the new VM in phase 2.
5. Move the dual WG stack to the new VM and keep the old one as rollback until the new stack is proven.

## Rule of thumb

- While NAT stays on the WG host, do not expect VyOS to distinguish admin vs client tunnel sources.
- Once the new VM is ready, remove NAT for VPN-to-internal traffic there and let VyOS see the original VPN subnets.
- Keep `ipv6only` explicit in every phase; it is not optional in the design.



