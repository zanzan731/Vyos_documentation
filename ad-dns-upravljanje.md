# AD DNS upravljanje

Ta datoteka vsebuje osnovne PowerShell ukaze za upravljanje AD DNS strežnika na `192.168.11.201`.

## Preverjanje stanja

```powershell
Get-DnsServerForwarder
Get-DnsServerZone
Get-DnsServer
```

## Pregled zapisov v coni

```powershell
Get-DnsServerResourceRecord -ZoneName "startup11.local" |
  Select-Object HostName, RecordType, RecordData

Resolve-DnsName startup11.local -Type A -Server 127.0.0.1
Resolve-DnsName startup11.local -Type AAAA -Server 127.0.0.1
Resolve-DnsName _ldap._tcp.dc._msdcs.startup11.local -Type SRV -Server 127.0.0.1
```

## Urejanje forwarderjev

```powershell
Add-DnsServerForwarder -IPAddress 193.2.1.66,1.1.1.1
Add-DnsServerForwarder -IPAddress 2001:1470:8000::66,2606:4700:4700::1111
Set-DnsServerForwarder -IPAddress 193.2.1.66,1.1.1.1,2001:1470:8000::66,2606:4700:4700::1111
```

## Dodajanje zapisov

```powershell
Add-DnsServerResourceRecordA -ZoneName "startup11.local" -Name "rest" -IPv4Address "192.168.11.104"
Add-DnsServerResourceRecordAAAA -ZoneName "startup11.local" -Name "rest" -IPv6Address "2001:1470:fffd:a9::104"
Add-DnsServerResourceRecordCName -ZoneName "startup11.local" -Name "www" -HostNameAlias "rest.startup11.local"
```

## Dodajanje SRV zapisov

```powershell
Add-DnsServerResourceRecordSrv -ZoneName "startup11.local" -Name "_ldap._tcp.dc._msdcs" -DomainName "startup11.local" -Priority 0 -Weight 100 -Port 389 -Target "win-sgi52j8519e.startup11.local"
Add-DnsServerResourceRecordSrv -ZoneName "startup11.local" -Name "_kerberos._tcp.dc._msdcs" -DomainName "startup11.local" -Priority 0 -Weight 100 -Port 88 -Target "win-sgi52j8519e.startup11.local"
```

## Brisanje zapisov

```powershell
Remove-DnsServerResourceRecord -ZoneName "startup11.local" -RRType A -Name "rest" -RecordData "192.168.11.104" -Force
Remove-DnsServerResourceRecord -ZoneName "startup11.local" -RRType AAAA -Name "rest" -RecordData "2001:1470:fffd:a9::104" -Force
```

## Osvežitev storitve

```powershell
Restart-Service DNS
Get-Service DNS
```

## Uporabna preverjanja

```powershell
nslookup -type=SRV _ldap._tcp.dc._msdcs.startup11.local 192.168.11.201
nslookup -type=A rest.startup11.local 192.168.11.201
nslookup -type=AAAA rest.startup11.local 192.168.11.201
```
