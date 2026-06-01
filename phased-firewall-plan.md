# Phased firewall plan

Summary of services (IPs, ports, public exposure).

### List of services

| Service | IPv4 | IPv6 | Port (proto) | Public? | Notes |
|---|---:|---:|---:|---:|---|
| RDP (GUI hosts + AD server) | 10.11.0.0/24; 192.168.11.201 | fd11:11:11::/64; 2001:1470:fffd:a9::201 | 3389 (tcp) | No | RDP enabled on internal GUI hosts, ipv6only GUI hosts, and AD server |
| SSH (all devices) | 10.11.0.0/24; 192.168.11.0/24; 88.200.24.241 | fd11:11:11::/64; 2001:1470:fffd:aa::1; 2001:1470:fffd:a9::1 | 22 (tcp) | only vyos | SSH service present on all devices; WAN SSH allowed only on management host |
| VyOS management (SSH) | 88.200.24.241 | 2001:1470:fffd:a8::2 | 22 (tcp) | Yes | WAN SSH allow present in live config (management host) |
| DMZ SNMP target (VyOS) | 192.168.11.1 | 2001:1470:fffd:a9::1 | 161 (udp) | No | SNMP on VyOS; exporter scrapes this target |
| REST service (scriptum) | 192.168.11.104 | 2001:1470:fffd:a9::104 | 8080 (tcp) | Yes | Public DNAT exists |
| scriptum backend (public) | 192.168.11.104 | 2001:1470:fffd:a9::104 | 4443 (tcp) | Yes | Public backend endpoint |
| Library API (HTTP) | 192.168.11.104 | 2001:1470:fffd:a9::104 | 3000 (tcp) | No | Internal HTTP API |
| Library API (HTTPS) | 192.168.11.104 | 2001:1470:fffd:a9::104 | 3443 (tcp) | Yes | Public HTTPS endpoint |
| Library API (GraphQL) | 192.168.11.104 | 2001:1470:fffd:a9::104 | 32484 (tcp) | No | Internal GraphQL endpoint |
| DMZ DNS | 192.168.11.105 | - | 53 (udp/tcp) | No | Internal DNS for DMZ clients |
| WireGuard listener (wg0) | 192.168.11.106 | 2001:1470:fffd:a9::106 | 51820 (udp) | Yes | PiVPN on DMZ host; NAT/masquerade remains in Phase 1 |
| wg-portal UI | 192.168.11.106 | 2001:1470:fffd:a9::106 | 8888 (tcp) | No | Local portal UI (internal only) |
| Prometheus | 192.168.11.107 | 2001:1470:fffd:a9::107 | 9090 (tcp) | No | Prometheus scrape UI/service |
| snmp_exporter | 192.168.11.107 | 2001:1470:fffd:a9::107 | 9116 (tcp) | No | Exporter endpoint for Prometheus |
| Grafana | 192.168.11.107 | 2001:1470:fffd:a9::107 | 3000 (tcp) | No | Grafana UI for dashboards |
| AD services (DNS/Kerberos/LDAP/etc.) | 192.168.11.201 | 2001:1470:fffd:a9::201 | 53/88/389/3268/135/123/445/464/49152-65535 | No | Active Directory services (internal only) |

This summary contains Phase 1 services only. Phase 2 items are described later in the document.

## DHCP mappings

The current VyOS configuration uses static DHCP mappings for the DMZ and related hosts. These are the current IPv4 and IPv6 mappings that should remain stable:

| Host | DHCPv4 address | DHCPv6 address | DHCPv6 DUID / identifier | Notes |
|---|---|---|---|---|
| raft1 | 192.168.11.101 | 2001:1470:fffd:a9::101 | 00:02:00:00:ab:11:2b:e2:d4:90:70:f3:b3:37 | DMZ server |
| raft2 | 192.168.11.102 | 2001:1470:fffd:a9::102 | 00:02:00:00:ab:11:e1:94:d4:8a:18:52:ad:98 | DMZ server |
| raft3 | 192.168.11.103 | 2001:1470:fffd:a9::103 | 00:02:00:00:ab:11:92:37:c8:9a:00:b8:67:77 | DMZ server |
| rest | 192.168.11.104 | 2001:1470:fffd:a9::104 | 00:02:00:00:ab:11:5a:9d:49:65:ce:4a:b2:48 | REST / web service |
| dns-srv | 192.168.11.105 | - | - | DMZ DNS server |
| wg | 192.168.11.106 | 2001:1470:fffd:a9::106 | 00:02:00:00:ab:11:80:f9:48:e8:e6:e2:12:59 | WireGuard host |
| snmp | 192.168.11.107 | 2001:1470:fffd:a9::107 | 00:02:00:00:ab:11:b8:b7:97:e3:eb:3c:a5:52 | SNMP-managed host |
| wg2 | 192.168.11.108 | 2001:1470:fffd:a9::108 | 00:02:00:00:ab:11:dd:e2:8d:62:21:b3:d9:00 | New WireGuard-related host |
| AD | 192.168.11.201 | 2001:1470:fffd:a9::201 | 00:01:00:01:31:86:a4:b0:00:0c:29:07:cf:26 | AD / Windows server |

For the IPv6 mapping set, the addresses now mirror the IPv4 1xx/2xx convention: `101-108` for the DMZ hosts and `201` for AD.

## Network assumptions

- WAN / public interface: `eth0`
- DMZ: `eth1`, subnet `192.168.11.0/24`
- INTERNAL: `eth2`, subnet `10.11.0.0/24`
- IPV6ONLY: `eth3`, subnet `fd11:11:11::/64`
- Existing admin WireGuard tunnel: `wg0`, subnet `10.4.103.0/24`, UDP `51820`
- WireGuard host: Ubuntu server in DMZ at `192.168.11.106`

Important: because the WG host currently MASQUERADEs VPN traffic, VyOS will usually see forwarded VPN traffic as coming from `192.168.11.106`, not from the original WireGuard subnet. That means admin/client separation is enforced on the WG host itself until the later migration to a non-PiVPN VM.

