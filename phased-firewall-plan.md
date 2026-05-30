# Phased firewall plan

Summary of services (IPs, ports, public exposure):

| Service | IP / Host | Port (proto) | Public? | Notes |
|---|---|---:|---:|---|
| VyOS management (SSH) | WAN (eth0 public IP) | 22 (tcp) | Yes | WAN SSH allow present in live config |
| Existing WireGuard listener (`wg0`) | 192.168.11.106 (DMZ WG host) | 51820 (udp) | Yes | PiVPN on DMZ host; NAT/MASQUERADE remains in Phase 1 |
| wg-portal UI | 192.168.11.106 (DMZ WG host) | 8888 (tcp) | No | Local portal UI (internal only)
| REST service `scriptum` | 192.168.11.104 (DMZ web host) | 8080 (tcp) | Yes | Internal REST endpoint used by services
| `scriptum` backend (public) | 192.168.11.104 (DMZ web host) | 4443 (tcp) | Yes | Public backend endpoint
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
- **DNAT (public services):** nat destination rules map explicit WAN ports to DMZ hosts (examples: UDP 51820 → `192.168.11.106`; TCP 8080/4443/3443 → `192.168.11.104`). Corresponding forward rules accept traffic only for those translated destinations and protocols.
- **Internal-to-DMZ:** internal subnets are allowed only the specific services they need (DNS, LDAP/Kerberos/GC/SMB/RPC/time and AD dynamic high ports to the AD server). These are implemented as specific `accept` entries (rules starting at `210`) that restrict destination address/port and inbound/outbound interfaces.
- **DMZ SSH policy:** a blanket DMZ SSH rule allows TCP/22 only from other DMZ hosts and from the WireGuard host (`192.168.11.106`) to support admin access while PiVPN NAT is still present.
- **SNMP / monitoring:** Prometheus + `snmp_exporter` scrape the VyOS SNMP target (`192.168.11.1:161`). The firewall allows scraping from the monitoring host `192.168.11.107` to VyOS and allows the exporter (DMZ) outbound to reach VyOS; exporter UI is reachable on `192.168.11.107:9116` for testing.
- **Masquerade / NAT:** source NAT (masquerade) rules remain for INTERNAL and DMZ outbound to the Internet. The existing WireGuard PiVPN NAT rule is intentionally preserved in Phase 1 so VyOS continues to see VPN administration traffic as coming from `192.168.11.106`. Hairpin DNAT/SNAT rules allow internal and DMZ clients to reach public services via the WAN IP.
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

