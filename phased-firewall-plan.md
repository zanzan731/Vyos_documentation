# Phased firewall plan

This plan keeps the current PiVPN setup on the Ubuntu DMZ host exactly as-is for now. The existing `wg0` tunnel stays the **admin** tunnel and continues to use NAT/MASQUERADE. The next phase is a clean migration to a new VM with `wg-portal`, where the dual WireGuard stack can be introduced without breaking the working config.

## Network assumptions

- WAN / public interface: `eth0`
- DMZ: `eth1`, subnet `192.168.11.0/24`
- INTERNAL: `eth2`, subnet `10.11.0.0/24`
- IPV6ONLY: `eth3`, subnet `fd11:11:11::/64`
- Existing admin WireGuard tunnel: `wg0`, subnet `10.4.103.0/24`, UDP `51820`
- Future client WireGuard tunnel: `wg-client`, subnet `10.4.104.0/24`, UDP `51821`
- WireGuard host: Ubuntu server in DMZ at `192.168.11.106`

Important: because the WG host currently MASQUERADEs VPN traffic, VyOS will usually see forwarded VPN traffic as coming from `192.168.11.106`, not from the original WireGuard subnet. That means admin/client separation is enforced on the WG host itself until the later migration to a non-PiVPN VM.

## Phase 1: keep PiVPN/NAT as-is, firewall everything else

Goal: preserve the working `wg0` admin tunnel, harden VyOS, harden all hosts, and include `ipv6only` in the firewall plan.

### 1. VyOS baseline firewall

Keep VyOS simple in phase 1: protect the router itself, allow the current public services, and do not try to distinguish admin/client WG traffic on VyOS yet.

```text
configure

set firewall name WAN-IN default-action 'drop'
set firewall name WAN-IN rule 10 action 'accept'
set firewall name WAN-IN rule 10 state established 'enable'
set firewall name WAN-IN rule 20 action 'accept'
set firewall name WAN-IN rule 20 protocol 'udp'
set firewall name WAN-IN rule 20 destination port '51820'
set firewall name WAN-IN rule 30 action 'accept'
set firewall name WAN-IN rule 30 protocol 'tcp'
set firewall name WAN-IN rule 30 destination port '443'

set interfaces ethernet eth0 firewall in name 'WAN-IN'

# Internal users may reach only the required DMZ services
set firewall name INTERNAL-TO-DMZ default-action 'drop'
set firewall name INTERNAL-TO-DMZ rule 10 action 'accept'
set firewall name INTERNAL-TO-DMZ rule 10 state established 'enable'
set firewall name INTERNAL-TO-DMZ rule 20 action 'accept'
set firewall name INTERNAL-TO-DMZ rule 20 source address '10.11.0.0/24'
set firewall name INTERNAL-TO-DMZ rule 20 destination address '192.168.11.0/24'
set firewall name INTERNAL-TO-DMZ rule 20 protocol 'tcp'
set firewall name INTERNAL-TO-DMZ rule 20 destination port '53,88,135,389,443,445,464,636,3268,3269,3389'

# Internal users may reach the internet
set firewall name INTERNAL-TO-WAN default-action 'drop'
set firewall name INTERNAL-TO-WAN rule 10 action 'accept'
set firewall name INTERNAL-TO-WAN rule 10 state established 'enable'
set firewall name INTERNAL-TO-WAN rule 20 action 'accept'
set firewall name INTERNAL-TO-WAN rule 20 source address '10.11.0.0/24'
set firewall name INTERNAL-TO-WAN rule 20 protocol 'tcp'
set firewall name INTERNAL-TO-WAN rule 20 destination port '80,443'
set firewall name INTERNAL-TO-WAN rule 30 action 'accept'
set firewall name INTERNAL-TO-WAN rule 30 source address '10.11.0.0/24'
set firewall name INTERNAL-TO-WAN rule 30 protocol 'udp'
set firewall name INTERNAL-TO-WAN rule 30 destination port '53'

commit
save
exit
```

Test from:
- VyOS CLI for rule installation: `show firewall name WAN-IN`, `show firewall name INTERNAL-TO-DMZ`, `show firewall name INTERNAL-TO-WAN`
- External host on WAN for port reachability: `nmap -Pn -p 51820,443 <public-ip>`
- Internal client in `10.11.0.0/24` for DNS/HTTPS reachability to DMZ: `dig @192.168.11.105 startup11.local`, `curl -I https://192.168.11.104`

Expected result:
- WAN can only reach the allowed public services.
- Internal users can reach the necessary DMZ services and the internet.
- `ipv6only` is still handled on the host side in this phase.

### 1b. VyOS IPv6 routing and firewall notes

The current IPv6 routing table already shows the connected networks, so no extra static IPv6 routes are needed in phase 1.

```text
show ipv6 route

S>* ::/0 [1/0] via 2001:1470:fffd:a8::1, eth0, weight 1
C>* 2001:1470:fffd:a8::/64 is directly connected, eth0
C>* 2001:1470:fffd:a9::/64 is directly connected, eth1
C>* 2001:1470:fffd:aa::/64 is directly connected, eth2
C>* fd11:11:11::/64 is directly connected, eth3
```

For IPv6 firewalling on VyOS, mirror the IPv4 policy with the same segment intent:

```text
configure

set firewall name WAN6-IN default-action 'drop'
set firewall name WAN6-IN rule 10 action 'accept'
set firewall name WAN6-IN rule 10 state established 'enable'
set firewall name WAN6-IN rule 20 action 'accept'
set firewall name WAN6-IN rule 20 protocol 'udp'
set firewall name WAN6-IN rule 20 destination port '51820'
set firewall name WAN6-IN rule 30 action 'accept'
set firewall name WAN6-IN rule 30 protocol 'tcp'
set firewall name WAN6-IN rule 30 destination port '443'

set firewall name INTERNAL6-TO-DMZ default-action 'drop'
set firewall name INTERNAL6-TO-DMZ rule 10 action 'accept'
set firewall name INTERNAL6-TO-DMZ rule 10 state established 'enable'
set firewall name INTERNAL6-TO-DMZ rule 20 action 'accept'
set firewall name INTERNAL6-TO-DMZ rule 20 source address '2001:1470:fffd:aa::/64'
set firewall name INTERNAL6-TO-DMZ rule 20 destination address '2001:1470:fffd:a9::/64'
set firewall name INTERNAL6-TO-DMZ rule 20 protocol 'tcp'
set firewall name INTERNAL6-TO-DMZ rule 20 destination port '53,88,135,389,443,445,464,636,3268,3269,3389'

set firewall name INTERNAL6-TO-WAN default-action 'drop'
set firewall name INTERNAL6-TO-WAN rule 10 action 'accept'
set firewall name INTERNAL6-TO-WAN rule 10 state established 'enable'
set firewall name INTERNAL6-TO-WAN rule 20 action 'accept'
set firewall name INTERNAL6-TO-WAN rule 20 source address '2001:1470:fffd:aa::/64'
set firewall name INTERNAL6-TO-WAN rule 20 protocol 'tcp'
set firewall name INTERNAL6-TO-WAN rule 20 destination port '80,443'
set firewall name INTERNAL6-TO-WAN rule 30 action 'accept'
set firewall name INTERNAL6-TO-WAN rule 30 source address '2001:1470:fffd:aa::/64'
set firewall name INTERNAL6-TO-WAN rule 30 protocol 'udp'
set firewall name INTERNAL6-TO-WAN rule 30 destination port '53'

commit
save
exit
```

Test from:
- VyOS CLI for IPv6 route visibility: `show ipv6 route`
- VyOS CLI for IPv6 firewall rules: `show firewall name WAN6-IN`, `show firewall name INTERNAL6-TO-DMZ`, `show firewall name INTERNAL6-TO-WAN`
- IPv6-capable host in INTERNAL: `ping6 2001:1470:fffd:a9::1`, `curl -6 -I https://[2001:1470:fffd:a9::104]`

Expected result:
- IPv6 routing matches the connected subnets already present on VyOS.
- IPv6 policy mirrors the IPv4 intent and keeps `ipv6only` isolated.

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
- From the internal monitoring host: `snmpwalk -v2c -c <community> 192.168.11.107`

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

- Add static routes so VyOS sees the new source subnets and can enforce segmentation:

```text
configure
set protocols static route 10.200.12.0/24 next-hop <NEW_VM_DMZ_IP>
set protocols static route 10.200.13.0/24 next-hop <NEW_VM_DMZ_IP>
commit
save
exit
```

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



