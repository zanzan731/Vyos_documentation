# Firewall Test Commands

Run these from a host inside each segment. Commands are read-only. Some HTTPS endpoints may use self-signed certs; use -k where shown.

## WireGuard admin tunnel

Use these from a host connected through WireGuard. They verify SSH/RDP reachability to all non-public segments.

### Windows (PowerShell)
```powershell
Test-NetConnection -ComputerName 10.11.0.1 -Port 22
Test-NetConnection -ComputerName 10.11.0.1 -Port 3389
Test-NetConnection -ComputerName 192.168.11.104 -Port 22
Test-NetConnection -ComputerName 192.168.11.104 -Port 3389
Test-NetConnection -ComputerName 192.168.11.107 -Port 22
Test-NetConnection -ComputerName 192.168.11.107 -Port 3389
Test-NetConnection -ComputerName 2001:1470:fffd:aa::1 -Port 22
Test-NetConnection -ComputerName 2001:1470:fffd:aa::1 -Port 3389
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 22
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 3389
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 22
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 3389
Test-NetConnection -ComputerName fd11:11:11::1 -Port 22
Test-NetConnection -ComputerName fd11:11:11::1 -Port 3389
```

### Linux (bash)
```bash
nc -vz 10.11.0.1 22
nc -vz 10.11.0.1 3389
nc -vz 192.168.11.104 22
nc -vz 192.168.11.104 3389
nc -vz 192.168.11.107 22
nc -vz 192.168.11.107 3389
nc -vz 2001:1470:fffd:aa::1 22
nc -vz 2001:1470:fffd:aa::1 3389
nc -vz 2001:1470:fffd:a9::104 22
nc -vz 2001:1470:fffd:a9::104 3389
nc -vz 2001:1470:fffd:a9::107 22
nc -vz 2001:1470:fffd:a9::107 3389
nc -vz fd11:11:11::1 22
nc -vz fd11:11:11::1 3389
```

## WAN / public internet

Use these from an external host on the public internet.

### Windows (PowerShell)
```powershell
Test-NetConnection -ComputerName 88.200.24.241 -Port 22
Test-NetConnection -ComputerName 88.200.24.241 -Port 8080
Test-NetConnection -ComputerName 88.200.24.241 -Port 4443
Test-NetConnection -ComputerName 88.200.24.241 -Port 3443
Test-NetConnection -ComputerName 88.200.24.241 -Port 3389
Test-NetConnection -ComputerName 2001:1470:fffd:a8::2 -Port 22
```

### Linux (bash)
```bash
nc -vz 88.200.24.241 22
nc -vz 88.200.24.241 8080
nc -vz 88.200.24.241 4443
nc -vz 88.200.24.241 3443
nc -vz 88.200.24.241 3389
nc -vz 2001:1470:fffd:a8::2 22
```

## Internal segment (eth2: 10.11.0.0/24, 2001:1470:fffd:aa::/64)

### Windows (PowerShell)
```powershell
# Hairpin to public IPv4 services (WAN IP)
Test-NetConnection -ComputerName 88.200.24.241 -Port 8080
Test-NetConnection -ComputerName 88.200.24.241 -Port 4443
Test-NetConnection -ComputerName 88.200.24.241 -Port 3443
curl.exe -sS -I http://88.200.24.241:8080/
curl.exe -k -sS -I https://88.200.24.241:4443/
curl.exe -k -sS -I https://88.200.24.241:3443/

# Public services via IPv6 (DMZ public addresses)
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 8080
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 4443
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 3443
curl.exe -g -6 -sS -I "http://[2001:1470:fffd:a9::104]:8080/"
curl.exe -g -6 -k -sS -I "https://[2001:1470:fffd:a9::104]:4443/"
curl.exe -g -6 -k -sS -I "https://[2001:1470:fffd:a9::104]:3443/"

# VyOS SSH via public IPv4/IPv6
Test-NetConnection -ComputerName 88.200.24.241 -Port 22
Test-NetConnection -ComputerName 2001:1470:fffd:a8::2 -Port 22

# Internal-only services (IPv4)
Test-NetConnection -ComputerName 192.168.11.106 -Port 8888
Test-NetConnection -ComputerName 192.168.11.104 -Port 3000
Test-NetConnection -ComputerName 192.168.11.104 -Port 32484
Test-NetConnection -ComputerName 192.168.11.107 -Port 3000
Test-NetConnection -ComputerName 192.168.11.107 -Port 9090
Test-NetConnection -ComputerName 192.168.11.107 -Port 9116
Test-NetConnection -ComputerName 192.168.11.104 -Port 22
Test-NetConnection -ComputerName 192.168.11.104 -Port 3389

# Internal-only services (IPv6)
Test-NetConnection -ComputerName 2001:1470:fffd:a9::106 -Port 8888
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 3000
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 32484
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 3000
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 9090
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 9116
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 22
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 3389

# DNS / AD (IPv4)
Resolve-DnsName rest.startup11.local -Server 192.168.11.105
Resolve-DnsName _ldap._tcp.dc._msdcs.startup11.local -Type SRV -Server 192.168.11.201
Test-NetConnection -ComputerName 192.168.11.201 -Port 88
Test-NetConnection -ComputerName 192.168.11.201 -Port 389
Test-NetConnection -ComputerName 192.168.11.201 -Port 3268
Test-NetConnection -ComputerName 192.168.11.201 -Port 3269
Test-NetConnection -ComputerName 192.168.11.201 -Port 445

# DNS / AD (IPv6)
Resolve-DnsName rest.startup11.local -Server 2001:1470:fffd:a9::105
Resolve-DnsName _ldap._tcp.dc._msdcs.startup11.local -Type SRV -Server 2001:1470:fffd:a9::201
Test-NetConnection -ComputerName 2001:1470:fffd:a9::201 -Port 88
Test-NetConnection -ComputerName 2001:1470:fffd:a9::201 -Port 389
Test-NetConnection -ComputerName 2001:1470:fffd:a9::201 -Port 3268
Test-NetConnection -ComputerName 2001:1470:fffd:a9::201 -Port 3269
Test-NetConnection -ComputerName 2001:1470:fffd:a9::201 -Port 445
```

### Linux (bash)
```bash
# Hairpin to public IPv4 services (WAN IP)
curl -sS -I http://88.200.24.241:8080/
curl -k -sS -I https://88.200.24.241:4443/
curl -k -sS -I https://88.200.24.241:3443/
nc -vz 88.200.24.241 8080
nc -vz 88.200.24.241 4443
nc -vz 88.200.24.241 3443

# VyOS SSH via public IPv4/IPv6
ssh -v vyos@88.200.24.241
ssh -6 -v vyos@2001:1470:fffd:a8::2

# Internal -> DMZ services (IPv4)
nc -vz 192.168.11.104 8080
nc -vz 192.168.11.104 3000
nc -vz 192.168.11.104 3443
nc -vz 192.168.11.104 32484
nc -vz 192.168.11.107 3000
nc -vz 192.168.11.107 9090
nc -vz 192.168.11.107 9116

# DNS / AD (IPv4)
dig @192.168.11.105 rest.startup11.local +short
dig @192.168.11.201 _ldap._tcp.dc._msdcs.startup11.local SRV +short
nc -vz 192.168.11.201 88
nc -vz 192.168.11.201 389
nc -vz 192.168.11.201 3268
nc -vz 192.168.11.201 3269
nc -vz 192.168.11.201 445
```

## DMZ segment (eth1: 192.168.11.0/24, 2001:1470:fffd:a9::/64)

### Windows (PowerShell)
```powershell
# Hairpin to public IPv4 services (WAN IP)
Test-NetConnection -ComputerName 88.200.24.241 -Port 8080
Test-NetConnection -ComputerName 88.200.24.241 -Port 4443
Test-NetConnection -ComputerName 88.200.24.241 -Port 3443
curl.exe -sS -I http://88.200.24.241:8080/
curl.exe -k -sS -I https://88.200.24.241:4443/
curl.exe -k -sS -I https://88.200.24.241:3443/

# VyOS SSH via public IPv4/IPv6
Test-NetConnection -ComputerName 88.200.24.241 -Port 22
Test-NetConnection -ComputerName 2001:1470:fffd:a8::2 -Port 22

# DMZ-hosted services from DMZ (IPv4)
Test-NetConnection -ComputerName 192.168.11.104 -Port 8080
Test-NetConnection -ComputerName 192.168.11.104 -Port 3000
Test-NetConnection -ComputerName 192.168.11.104 -Port 3443
Test-NetConnection -ComputerName 192.168.11.104 -Port 4443
Test-NetConnection -ComputerName 192.168.11.104 -Port 32484
Test-NetConnection -ComputerName 192.168.11.105 -Port 53
Test-NetConnection -ComputerName 192.168.11.106 -Port 8888
Test-NetConnection -ComputerName 192.168.11.107 -Port 3000
Test-NetConnection -ComputerName 192.168.11.107 -Port 9090
Test-NetConnection -ComputerName 192.168.11.107 -Port 9116

# DMZ-hosted services from DMZ (IPv6)
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 8080
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 3000
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 3443
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 4443
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 32484
Test-NetConnection -ComputerName 2001:1470:fffd:a9::105 -Port 53
Test-NetConnection -ComputerName 2001:1470:fffd:a9::106 -Port 8888
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 3000
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 9090
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 9116

# Optional: SNMP to VyOS (if snmpwalk is installed)
# snmpwalk -v2c -c startup11 192.168.11.1 system

# Expected blocked example (should fail)
Test-NetConnection -ComputerName 10.11.0.1 -Port 22
Test-NetConnection -ComputerName 10.11.0.1 -Port 3389
```

### Linux (bash)
```bash
# Hairpin to public IPv4 services (WAN IP)
curl -sS -I http://88.200.24.241:8080/
curl -k -sS -I https://88.200.24.241:4443/
curl -k -sS -I https://88.200.24.241:3443/
nc -vz 88.200.24.241 8080
nc -vz 88.200.24.241 4443
nc -vz 88.200.24.241 3443

# VyOS SSH via public IPv4/IPv6
ssh -v vyos@88.200.24.241
ssh -6 -v vyos@2001:1470:fffd:a8::2

# Optional: SNMP to VyOS (if snmpwalk is installed)
# snmpwalk -v2c -c startup11 192.168.11.1 system

# Expected blocked example (should fail)
nc -vz 10.11.0.1 22
```

## IPv6-only segment (eth3: fd11:11:11::/64)

### Windows (PowerShell)
```powershell
# VyOS SSH via public IPv6
Test-NetConnection -ComputerName 2001:1470:fffd:a8::2 -Port 22
ssh -6 vyos@2001:1470:fffd:a8::2

# IPv6 services on DMZ hosts
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 22
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 3389
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 8080
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 3000
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 3443
Test-NetConnection -ComputerName 2001:1470:fffd:a9::104 -Port 32484
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 3000
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 9090
Test-NetConnection -ComputerName 2001:1470:fffd:a9::107 -Port 9116

# DNS / AD (IPv6)
Resolve-DnsName rest.startup11.local -Server 2001:1470:fffd:a9::105
Resolve-DnsName _ldap._tcp.dc._msdcs.startup11.local -Type SRV -Server 2001:1470:fffd:a9::201
Test-NetConnection -ComputerName 2001:1470:fffd:a9::201 -Port 88
Test-NetConnection -ComputerName 2001:1470:fffd:a9::201 -Port 389
Test-NetConnection -ComputerName 2001:1470:fffd:a9::201 -Port 3268
Test-NetConnection -ComputerName 2001:1470:fffd:a9::201 -Port 3269
Test-NetConnection -ComputerName 2001:1470:fffd:a9::201 -Port 445
```

### Linux (bash)
```bash
# VyOS SSH via public IPv6
ssh -6 -v vyos@2001:1470:fffd:a8::2

# IPv6 services on DMZ hosts
nc -vz 2001:1470:fffd:a9::104 22
nc -vz 2001:1470:fffd:a9::104 3389
curl -g -6 -sS -I "http://[2001:1470:fffd:a9::104]:8080/"
curl -g -6 -k -sS -I "https://[2001:1470:fffd:a9::104]:3443/"

nc -vz 2001:1470:fffd:a9::104 8080
nc -vz 2001:1470:fffd:a9::104 3000
nc -vz 2001:1470:fffd:a9::104 3443
nc -vz 2001:1470:fffd:a9::104 32484
nc -vz 2001:1470:fffd:a9::107 3000
nc -vz 2001:1470:fffd:a9::107 9090
nc -vz 2001:1470:fffd:a9::107 9116

# DNS / AD (IPv6)
dig @2001:1470:fffd:a9::105 rest.startup11.local +short
dig @2001:1470:fffd:a9::201 _ldap._tcp.dc._msdcs.startup11.local SRV +short
nc -vz 2001:1470:fffd:a9::201 88
nc -vz 2001:1470:fffd:a9::201 389
nc -vz 2001:1470:fffd:a9::201 3268
nc -vz 2001:1470:fffd:a9::201 3269
nc -vz 2001:1470:fffd:a9::201 445
```

