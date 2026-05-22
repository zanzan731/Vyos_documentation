---
date: 2026-05-22
title: Dokumentacija VyOS usmerjevalnika - startup11
---

# Osnovne informacije

- **Ime naprave:** startup11-vyos

- **Domena:** startup11.local

- **Uporabnik:** vyos (prijava prek SSH ključa)

# Omrežni vmesniki

| **Vmesnik** | **Opis**       | **IPv4**         | **IPv6**                |
|:------------|:---------------|:-----------------|:------------------------|
| eth0        | javni internet | 88.200.24.241/25 | 2001:1470:fffd:a8::2/64 |
| eth1        | DMZ            | 192.168.11.1/24  | 2001:1470:fffd:a9::1/64 |
| eth2        | interna LAN    | 10.11.0.1/24     | 2001:1470:fffd:aa::1/64 |
| eth3        | IPv6-only      | \-               | fd11:11:11::1/64        |

# Privzete usmeritve (statične usmeritve)

| **Destinacija** | **Naslednji hop**    |
|:----------------|:---------------------|
| 0.0.0.0/0       | 88.200.24.129        |
| ::/0            | 2001:1470:fffd:a8::1 |

# NAT (IPv4)

| **Vrsta** | **Viri / kriterij** | **Prevod / opomba** |
|:---|:---|:---|
| Izvorni NAT (SNAT) | 10.11.0.0/24, izhodni vmesnik eth0 | maskiranje (masquerade) |
| Izvorni NAT (SNAT) | 192.168.11.0/24, izhodni vmesnik eth0 | maskiranje (masquerade) |

# DMZ strežniki (vsi v omrežju 192.168.11.0/24)

## Pregled strežnikov

| **Ime strežnika** | **IP naslov** | **MAC naslov** | **Namen** |
|:---|:---|:---|:---|
| raft1 | 192.168.11.101 | 00:0c:29:15:42:6f | Raft (cluster node) |
| raft2 | 192.168.11.102 | 00:0c:29:2b:64:27 | Raft (cluster node) |
| raft3 | 192.168.11.103 | 00:0c:29:a2:5c:63 | Raft (cluster node) |
| rest | 192.168.11.104 | 00:0c:29:17:1a:72 | REST API / ostali servisi |
| dns-srv | 192.168.11.105 | 00:0c:29:4a:b1:99 | DNS strežnik (lokalni) |
| wireguard | 192.168.11.106 | 00:0c:29:c4:d1:52 | WireGuard VPN končna točka |
| snmp | 192.168.11.107 | 00:0c:29:69:75:09 | SNMP / monitoring cilj |
| AD (dmz windows 1) | 192.168.11.201 | 00:0c:29:07:cf:1c | Active Directory (Domain Controller) |

## DHCP - statične mape

Statične DHCP mape so konfigurirane v DHCP strežniku na VyOS in ujemajo IP naslove s MAC naslovi, kot je prikazano spodaj.

| **Ime**            | **MAC naslov**    | **IP naslov**  |
|:-------------------|:------------------|:---------------|
| raft1              | 00:0c:29:15:42:6f | 192.168.11.101 |
| raft2              | 00:0c:29:2b:64:27 | 192.168.11.102 |
| raft3              | 00:0c:29:a2:5c:63 | 192.168.11.103 |
| rest               | 00:0c:29:17:1a:72 | 192.168.11.104 |
| dns-srv            | 00:0c:29:4a:b1:99 | 192.168.11.105 |
| wireguard          | 00:0c:29:c4:d1:52 | 192.168.11.106 |
| AD (dmz windows 1) | 00:0c:29:07:cf:1c | 192.168.11.201 |
| snmp               | 00:0c:29:69:75:09 | 192.168.11.107 |

# NAT in preusmeritve vrat

## IPv4 DNAT (port forwarding)

- **Pravila:** zunanja vmesnik `eth0`, UDP port `51820` preusmerjen na `192.168.11.106` (WireGuard).

| **Tip** | **Kriterij** | **Cilj / opomba** |
|:---|:---|:---|
| DNAT (preusmeritev vrat) | vhod: eth0, proto UDP, dst port 51820 | 192.168.11.106 (WireGuard) |
| SNAT / maskiranje | 10.11.0.0/24 -\> izhod eth0 | maskiranje (masquerade) |
| SNAT / maskiranje | 192.168.11.0/24 -\> izhod eth0 | maskiranje (masquerade) |
| NAT66 | fd11:11:11::/64 -\> izhod eth0 | 2001:1470:fffd:ab::/64 |

## IPv4 source NAT (masquerade)

Masquerade je nastavljen za notranji in DMZ promet, ki gre preko javnega vmesnika `eth0`.

    # 10.11.0.0/24 -> eth0 (masquerade)
    set nat source rule 100 outbound-interface name 'eth0'
    set nat source rule 100 source address '10.11.0.0/24'
    set nat source rule 100 translation address 'masquerade'

    # 192.168.11.0/24 -> eth0 (masquerade)
    set nat source rule 110 outbound-interface name 'eth0'
    set nat source rule 110 source address '192.168.11.0/24'
    set nat source rule 110 translation address 'masquerade'

## NAT66 (NPTv6, IPv6-to-IPv6 Network Prefix Translation - RFC 6296)

Prevod naslovov: `fd11:11:11::/64` se prevaja na `2001:1470:fffd:ab::/64` za promet, ki izhaja prek `eth0`.

# Varnost (firewall)

## IPv4 - vhodni promet (input)

- Pravilo za ohranjanje stanj: dovoli `established` in `related` povezave.

- Pravilo za SSH: na javnem vmesniku `eth0` je dovoljeno TCP dst port `22` za novo povezavo.

| **IP verzija** | **Veriga** | **Ključno pravilo / opis** |
|:---|:---|:---|
| IPv4 | INPUT | Dovoli vzpostavljene in sorodne povezave (established, related). |
| IPv4 | INPUT | Dovoli nove TCP povezave na port 22 na vmesniku eth0 (SSH). |
| IPv4 | FORWARD | Dovoli nove UDP povezave iz eth0 proti 192.168.11.106:51820 (WireGuard). |
| IPv6 | INPUT | Dovoli vzpostavljene in sorodne povezave; dovoli nove TCP povezave na port 22 na eth0. |
| IPv6 | FORWARD | Dovoli nove UDP povezave na port 51820 na vhodnem vmesniku eth0 (WireGuard). |

## IPv4 - forward (posredovanje)

- Pravilo za WireGuard: dovoli novo UDP povezavo iz `eth0` proti `192.168.11.106:51820` s prehodi na `eth1`.

- Pravila 210-241 eksplicitno dovolijo dostop iz `eth2` do AD DNS/DC na `192.168.11.201` (DNS, Kerberos, LDAP, Global Catalog, SMB/RPC, dynamic RPC).

## IPv6 - vhodni promet in posredovanje

IPv6 ima podobna vhodna pravila (dovoli `established/related` in SSH na `eth0`), forward pravilo za WireGuard (UDP port 51820 na vhodnem vmesniku `eth0`) in pravila 210-241 za dostop do AD strežnika na `2001:1470:fffd:a9::185`.

# Storitve

## DHCP (IPv4)

DHCP server ima dve skupini: **SERVERS** (192.168.11.0/24) z navedenimi statičnimi mapami in **USERS** (10.11.0.0/24) za uporabniške naprave z avtomatskim razponom.

| **Skupina** | **Subnet / opomba**                            |
|:------------|:-----------------------------------------------|
| SERVERS     | 192.168.11.0/24 (statične mape)                |
| USERS       | 10.11.0.0/24 (dinamični range 10.11.0.100-200) |

## DHCPv6

DHCPv6 podeljuje naslove v subnetu `2001:1470:fffd:a9::/64` z range `::100` - `::1ff`. Ime strežnika za DHCPv6 je `2001:1470:fffd:a9::1`.

## DNS (posredovanje in split DNS)

DNS posredovanje na VyOS sprejema poizvedbe iz notranjih omrežij in uporablja conditional forward za AD domeno.

**Ključna split-DNS logika:**

- poizvedbe za `startup11.local` se na VyOS preusmerijo na AD DNS `192.168.11.201`;

- vse ostale poizvedbe gredo na javne upstream DNS strežnike (ARNES + Cloudflare).

**AD DNS server (authoritative):** `192.168.11.201` / `2001:1470:fffd:a9::185`

### Trenutno stanje AD DNS

Trenutna AD zona `startup11.local` vsebuje ključne notranje zapise za domeno, DC in DMZ strežnike:

- korenski zapis `@` vsebuje A zapis `192.168.11.201` in AAAA zapis `2001:1470:fffd:a9::185`;

- NS in SOA na vrhu cone kažeta na `win-sgi52j8519e.startup11.local.`;

- standardni AD SRV zapisi so prisotni za `_gc._tcp`, `_kerberos._tcp`, `_kerberos._udp`, `_ldap._tcp` in `_kpasswd._tcp` ter ustrezne `Default-First-Site-Name` in `ForestDnsZones` / `DomainDnsZones` podcone;

- glavni DC gostitelj `win-sgi52j8519e` ima A zapis `192.168.11.201` in AAAA zapis `2001:1470:fffd:a9::185`;

- dodatna notranja zapisa sta `rest.startup11.local` `192.168.11.104` in `snmp.startup11.local` `192.168.11.107`.

**Forwarderji na AD DNS:**

- IPv4: `193.2.1.66`, `1.1.1.1`

- IPv6: `2001:1470:8000::66`, `2606:4700:4700::1111`

**Dovoljena omrežja za VyOS DNS forwarding:** 10.11.0.0/24, 192.168.11.0/24, 2001:1470:fffd:aa::/64, 2001:1470:fffd:a9::/64, fd11:11:11::/64.

**Upstream DNS strežniki:**

| **Ponudnik** | **IPv4**   | **IPv6**             |
|:-------------|:-----------|:---------------------|
| ARNES        | 193.2.1.66 | 2001:1470:8000::66   |
| Cloudflare   | 1.1.1.1    | 2606:4700:4700::1111 |

### Split DNS (dnsmasq)

Strežnik `dns-srv` (192.168.11.105) z **dnsmasq** je opcijski notranji resolver. Trenutna pravilna konfiguracija uporablja `server=/.../` in ne `address=/.../` za AD domeno, da se ohranijo SRV zapisi za AD prijavo.

**Trenutna konfiguracija:**

- dnsmasq posluša na: `192.168.11.105:53` (DMZ naslov)

- `startup11.local` se posreduje na AD DNS: `192.168.11.201` in `2001:1470:fffd:a9::185`

- Konfiguracija: `/etc/dnsmasq.d/startup11.conf`

**Pomembno za AD prijavo:** notranji odjemalci morajo za `startup11.local` dobiti SRV zapise iz AD DNS, ne samo A/AAAA zapisov. Zato je v VyOS nastavljen:

    set service dns forwarding domain startup11.local name-server 192.168.11.201
    set service dns forwarding domain startup11.local recursion-desired

**Sprememba konfiguracije:**

    # Edit configuration file
    sudo nano /etc/dnsmasq.d/startup11.conf

    # Test configuration
    sudo dnsmasq --test

    # Restart service
    sudo systemctl restart dnsmasq

    # Check service status
    sudo systemctl status dnsmasq

    # Check listening on port 53
    ss -ltnup '( sport = :53 )'

    # Test DNS response
    dig +short _ldap._tcp.dc._msdcs.startup11.local @192.168.11.105 SRV
    dig +short example.com @192.168.11.105

### dnsmasq - aktivna konfiguracija in ponovna postavitev

Spodaj je preverjena konfiguracija, ki trenutno teče na `192.168.11.105:53`.

    # /etc/dnsmasq.d/startup11.conf
    # Bind only to the DMZ address to avoid conflicts with systemd-resolved on localhost
    listen-address=192.168.11.105
    bind-interfaces

    # Forward AD domain to AD DNS (preserves SRV records)
    server=/startup11.local/192.168.11.201
    server=/startup11.local/2001:1470:fffd:a9::185

    # Upstream resolvers for non-local domains
    server=1.1.1.1
    server=193.2.1.66
    server=2001:1470:8000::66
    server=2606:4700:4700::1111

Koraki za ponovno postavitev:

1.  Namesti pakete.

        sudo apt update
        sudo apt install -y dnsmasq dnsutils

2.  Ustvari konfiguracijsko datoteko.

        sudo tee /etc/dnsmasq.d/startup11.conf > /dev/null << 'EOF'
        # (vsebina kot zgoraj)
        EOF

3.  Preveri sintakso in ponovno zaženi storitev.

        sudo dnsmasq --test
        sudo systemctl restart dnsmasq
        sudo systemctl enable dnsmasq

4.  Preveri delovanje.

        ss -ltnup '( sport = :53 )'
        dig +short _ldap._tcp.dc._msdcs.startup11.local @192.168.11.105 SRV
        dig +short example.com @192.168.11.105

### mDNS in systemd-resolved: rešitev za .local

Na nekaterih Ubuntu gostiteljih storitev `systemd-resolved` obravnava domeno `.local` kot mDNS (Avahi). Posledično lahko DNS poizvedbe za `startup11.local` prejmejo odgovor `REFUSED` ali pa jih sistem poskuša obdelati z mDNS namesto prek omrežnega DNS resolverja.

Na gostitelju, kjer teče `wg-portal`, smo uporabili preprost popravek: za vmesnik smo nastavili routing domain in onemogočili mDNS, tako da se poizvedbe za `startup11.local` pošljejo na DHCP-provided resolver (192.168.11.1) in dosežejo AD DNS.

    # Nastavi routing domain (tilde pomeni routing domain)
    sudo resolvectl domain ens160 ~startup11.local

    # Onemogoci mdns na vmesniku
    sudo resolvectl mdns ens160 no

    # Pocisti predpomnilnik, ce je potrebno
    sudo resolvectl flush-caches

    # Preizkus
    resolvectl query startup11.local
    dig +short _ldap._tcp.dc._msdcs.startup11.local @192.168.11.1 SRV

Ta rešitev ohranja mDNS obnašanje za druge gostitelje, hkrati pa zagotavlja, da poizvedbe za `startup11.local` dosežejo avtoritativni AD DNS.

## wg-portal (WireGuard portal) in integracija z Active Directory

**Kaj je wg-portal:** `wg-portal` je spletna aplikacija za upravljanje WireGuard konfiguracij, dovoljenj in omogočanje samopostrežnega ustvarjanja peer konfiguracij za uporabnike.

**Kje teče:** Aplikacija je dosegljiva na `http://192.168.11.106:8888`. Lokacije ostalih storitev so navedene v razdelku "DMZ strežniki" zgoraj.

**Kako se poveže z AD:**

- Aplikacija uporablja LDAP bind račun za poizvedbe uporabnikov in preverjanje članstev v skupinah.

- Avtentikacija poteka z bindanjem (bind) in iskanjem vnosa, ki ustreza `sAMAccountName` ali `userPrincipalName`.

- Atribute AD lahko preslikamo, npr. uporabimo `userPrincipalName` kot `email`, kadar je `mail` prazen.

- Administratorske pravice se določijo preko članstva v AD skupini (npr. `Domain Admins`).

Pri namestitvi smo se v veliki meri držali vodnika: https://medium.com/@seeneeru/complete-guide-installing-and-configuring-wireguard-portal-on-linux-d23261027520 z nekaj lokalnimi modifikacijami prilagoditvami za naš okolje. Konfiguracija, ki smo jo uporabili v tem repozitoriju, je na voljo v datoteki `wgportal.yaml`.

**Opombe:**

- Privzeta podatkovna shramba aplikacije je SQLite (`data/sqlite.db`). Če aplikacija poroča o napaki `unable to open database file`, preverite, da mapa `data` obstaja in ima pravilne pravice/lastništvo (npr. `/opt/wg-portal/data`).

- Primer ukazov za ustvarjanje bind uporabnika v AD (PowerShell):

<!-- -->

    # Ustvari servisnega uporabnika (prilagodi geslo varno)
    New-ADUser -Name "wgportal_bind" -SamAccountName wgportal_bind -AccountPassword (ConvertTo-SecureString 'StrongP@ssw0rd' -AsPlainText -Force) -Enabled $true

    # Po potrebi dodaj uporabnike v administratorsko skupino
    Add-ADGroupMember -Identity "Domain Admins" -Members "zanadmin","pavlogal"

**Preizkusi in dnevniški pregledi:**

- Testirajte LDAP poizvedbe z orodjem `ldapsearch` kjer je na voljo.

- Preverjajte dnevniške datoteke aplikacije za napake pri bindanju ali iskanju uporabnika.

- Če uporabniki ne vidijo konfiguracij, preverite, da so vklopljene nastavitve `create_default_peer_on_login` in `self_provisioning_allowed`.

**Opomba:** Po vsaki spremembi preveri sintakso in ponovno zaženi storitev, da se spremembe uveljavijo.

## NTP

## SNMP in monitoring

SNMP je omogočen na VyOS in služi kot vir metrike za orodja za monitoring (Prometheus + Grafana).

**VyOS konfiguracija (primer iz v4.commands):**

    set service snmp community startup11 authorization 'ro'
    set service snmp contact 'pd43760@student.uni-lj.si'
    set service snmp listen-address 192.168.11.1
    set service snmp location 'FRI'

**Kako pobrati metrike (pregledno):**

- Preveri dostop z: `snmpwalk -v2c -c startup11 192.168.11.1 1.3.6.1.2.1.1.3.0`

- Pri uspehu bo vrnil `sysUpTime` in podobne OID vrednosti.

**Monitoring stack (kratka navodila)**

- Uporabi `snmp_exporter` (port 9116), `prometheus` in `grafana` (npr. Docker Compose stack).

- Priporočen potek: pripravite `generator.yml` s modulom `vyos` (walk: ifTable, ifXTable, sysUpTime), zaženite generator in pridobite `snmp.yml`.

- Preizkus exporterja (primer):

      curl "http://<snmp_exporter>:9116/snmp?module=vyos&target=192.168.11.1"

- Primer Prometheus scrape job (poenostavljeno):

      scrape_configs:
        - job_name: 'snmp'
          static_configs:
            - targets: ['192.168.11.1']
          metrics_path: /snmp
          params:
            module: [vyos]
            auth: [vyos_auth]
          relabel_configs: ...

**Hitri nasveti:**

- Namestite MIB datoteke, če generator potrebuje lokalne MIB‑e (paket `snmp-mibs-downloader`).

- Če exporter vrne napako `Unknown auth`, preverite, da so v `snmp.yml` in Prometheus parametri usklajeni (auth ime in modul).

Konfigurirani NTP strežniki so:

- ntp.arnes.si

- time1.vyos.net

- time2.vyos.net

- time3.vyos.net

## Router Advertisements (RA)

RA so omogočeni na:

- `eth1`: prefix `2001:1470:fffd:a9::/64` (managed flag, no-autonomous)

- `eth2`: prefix `2001:1470:fffd:aa::/64`

- `eth3`: prefix `fd11:11:11::/64`, name-server `fd11:11:11::1`

## SSH

SSH je konfiguriran za prijavo prek ključev (avtentikacija z geslom je onemogočena) na privzetem portu 22. Če želite začasno omogočiti prijavo z geslom, uredite datoteko `/etc/ssh/sshd_config.d/50-cloud-init.conf` in nastavite `PasswordAuthentication yes`, nato ponovno zaženite `sshd`.

# Sistem

## Uporabniki in ključi

Glavni lokalni uporabnik na napravi je `vyos`. V konfiguraciji so vpisani javni ključi za uporabnika `vyos`:

- **pavle**: `AAAAC3NzaC1lZDI1NTE5AAAAIClsTiUna0lG4FgaZOZ8cpxWvlWM7h9B2dbL53+QXr3h`

- **zanzan**: `AAAAC3NzaC1lZDI1NTE5AAAAIIGRVCofZkoaEaAcW0LquGsYgpRyHZ4Dg0fqVlssZUIL`

Za začasno ponovno omogočanje SSH gesel: uredite `/etc/ssh/sshd_config.d/50-cloud-init.conf` in nastavite `PasswordAuthentication yes`.

## Uporabniška imena

Uporabniki na dmz virtualkag so vsi poimenovani `zanzan0X`, kjer je X številka virtualke. Na klientih TODO.

## Splošno geslo

<div class="center">

</div>

# Upravljanje s konfiguracijami

## Nalaganje celotne konfiguracije

Če želite naložiti celotno konfiguracijo iz datoteke (npr. `v4.conf`), uporabite:

    configure
    load v4.conf
    commit
    save

## Apliciranje seznama ukazov

Če želite aplicirati seznam ukazov iz datoteke (npr. `v4.commands`), uporabite:

    configure
    source v4.commands
    commit
    save

## Opozorilo pri uporabi

Pri apliciranju ukazov je potrebna pazljivost — nekateri ukazi ne delujejo kot pričakovano:

- Ukaz `set` pri vmesnikih (`interface`) ne nastavlja vrednosti, ampak jo dodaja (deluje kot `add`). To lahko vodi do podvajanja nastavitev.\
  item Originalne konfiguracije\
  verb\|v1.commands\| in\
  verb\|v3.commands\| so zgodovinski osnutki; za trenutno stanje uporabljaj\
  verb\|v4.conf\| in\
  verb\|v4.commands\|.

- Najnovejšo in pravilno konfiguracijo (`v4.commands`) generirajte avtomatsko z ukazom (zunaj `configure` moda):

<!-- -->

    show configuration commands > v4.commands

Uporabite to avtomatsko generirano datoteko za zanesljivo apliciranje vseh trenutnih nastavitev.

# WireGuard

## Splošne informacije

WireGuard VPN je nastavljeno na napravi na IP naslovu `192.168.11.106` v DMZ omrežju. Konfiguracija je bila avtomatsko generirana s **pivpn** skripto, ki poenostavi upravljanje in vzpostavitev WireGuard VPN strežnika.

## Dostop in port

- **Notranji naslov:** 192.168.11.106

- **Javni port:** UDP 51820 (preusmeran prek NAT/DNAT na eth0)

- **Storitev:** Aktivna in dostopna iz javnega interneta

## Upravljanje VPN uporabnikov

WireGuard uporabnike upravljate s pivpn ukazom. Osnovni koraki:

    # Dodaj novega VPN uporabnika
    pivpn add

    # Ogled aktivnih povezav
    pivpn -c

    # Ogled konfiguracije in QR koda
    pivpn -qr

    # Brisanje uporabnika
    pivpn remove

## Poskus z wg-portal

Poskusil sem postaviti tudi `wg-portal`, ker podpira LDAP avtentikacijo, vendar se je zagon ustavil pri odpiranju SQLite baze z napako `out of memory (14)`. Zaradi tega je ostalo upravljanje WireGuard uporabnikov na `pivpn`.

    2026/05/21 23:16:51 INFO Starting WireGuard Portal V2... version=v2.2.3-1c3eacb
    time=2026-05-21T23:16:51.752Z level=INFO msg="Configuration loaded!" logLevel=info
    panic: failed to open sqlite database: unable to open database file: out of memory (14)

## Konfiguracija in nastavitve

Privzete pivpn nastavitve:

- Podatkovna mapa: `/etc/wireguard/`

- Datoteka strežnika: `/etc/wireguard/wg0.conf`

- Konfiguracije VPN uporabnikov (QR kode, ključi): `~/configs/` (domača mapa pivpn skripty)

- VPN subnet v našem sistemu: `10.4.103.0/24`

## Odpravljanje težav

Če WireGuard ni dostopen ali se ne povezuje:

    # Preverka stanja vmesnika
    ip link show wg0

    # Preverka aktivnih povezav
    wg show

    # Resetiranje WireGuard vmesnika
    sudo ip link delete wg0
    sudo systemctl restart wg-quick@wg0

# Active Directory (Windows Server)

## Osnovne informacije

Active Directory domena je nastavljena na strežniku **sk11-dmz-windows**. Strežnik deluje kot primarni Domain Controller (PDC) za domeno `startup11.local`.

- **Ime strežnika:** sk11-dmz-windows

- **Domena:** startup11.local

- **NetBIOS ime:** startup11

- **OS:** Windows Server (Core)

- **Vloga:** Domain Controller

## Ustvarjanje uporabnikov v Active Directory

Uporabnike v domeni ustvarjamo s PowerShell ukazi neposredno na Domain Controllerju.

**Primer: Ustvarjanje uporabnika**

``` bash
$password = Read-Host "Enter password for User" -AsSecureString
New-ADUser -Name "Ime Priimek" `
           -GivenName Ime `
           -Surname Priimek `
           -SamAccountName imepriimek `
           -UserPrincipalName ime.priimek@startup11.local `
           -Enabled $true `
           -AccountPassword $password `
           -PassThru
```

## Upravljanje uporabnikov

**Prikaz vseh uporabnikov v domeni:**

``` bash
Get-ADUser -Filter * | Select-Object Name, SamAccountName, Enabled
```

**Dodajanje grupe in dodajanje uporabnika grupi:**

    New-ADGroup -Name "Group name" -GroupScope Global -GroupCategory Security
    Add-ADGroupMember -Identity "Group name" -Members "account name"

**Onemogočanje uporabniškega računa:**

``` bash
Disable-ADAccount -Identity "ime"
```

**Brisanje uporabniškega računa:**

``` bash
Remove-ADUser -Identity "ime" -Confirm:$false
```

## Prijava v domeno

Računalnike (Windows Pro/Enterprise ali Linux s konfiguriranim SSSD) lahko priklopimo v domeno `startup11.local`. Po uspešnem priklopu se uporabniki prijavljajo z:

- **Uporabniško ime:** `startup11\ime` (npr. `startup11\jdoe`)

- **Geslo:** (geslo, nastavljeno ob ustvarjanju uporabnika)

## Dodatne informacije

- Administrator domene: `startup11\Administrator` z enakim geslom kot lokalni Administrator na strežniku

## Upravljanje AD DNS streznika

AD DNS je avtoritativen za `startup11.local` in vraca AD SRV zapise (npr. `_ldap._tcp.dc._msdcs.startup11.local`).

**Preverjanje forwarderjev:**

``` bash
Get-DnsServerForwarder
```

**Preverjanje, da je DNS na AD strezniku lokalen:**

``` bash
Get-DnsClientServerAddress
Get-DnsServerZone
```

**Izpis DNS zapisov v AD zoni:**

``` bash
Get-DnsServerResourceRecord -ZoneName "startup11.local" |
  Select-Object HostName, RecordType, RecordData
```

**Preverjanje SRV zapisov na AD DNS:**

``` bash
Resolve-DnsName _ldap._tcp.dc._msdcs.startup11.local -Type SRV -Server 127.0.0.1
nslookup -type=SRV _ldap._tcp.dc._msdcs.startup11.local 192.168.11.201
```

**Dodajanje notranjih zapisov za DMZ streznike (primer):**

``` bash
Add-DnsServerResourceRecordA -ZoneName "startup11.local" -Name "rest" -IPv4Address "192.168.11.104"
Add-DnsServerResourceRecordA -ZoneName "startup11.local" -Name "snmp" -IPv4Address "192.168.11.107"
```

**Test novih zapisov po dodajanju:**

``` bash
Resolve-DnsName rest.startup11.local -Type A -Server 127.0.0.1
Resolve-DnsName snmp.startup11.local -Type A -Server 127.0.0.1
```

**Opomba o split DNS:** VyOS izvaja DNS posredovanje in conditional forward na AD DNS za `startup11.local`, AD DNS pa ostane avtoritativni vir notranjih zapisov.

# REST

Vse datoteke se nahajajo na sk11-dmz-linux-04 v home directoriju od zanzan04. Imamo dve rest storitvi in sicer Scriptum_kp in library-api. V tem delu bom govoril o library-api za probleme s Scriptum_kp pa se obrnite na github dokumentacijo projekta <https://github.com/zanzan731/Scriptum_kp>.

## Arhitektura

Komponente:

- Node.js Express aplikacija (`server.js`)

- SQLite baza (`library.db`)

- TLS certifikati

- Docker in Docker Compose

- LDAP povezava proti Active Directory

## Konfiguracija

Pomembne okoljske spremenljivke (`server.js`):

    LDAP_URL=ldap://192.168.11.201:389
    AD_DOMAIN=startup11.local
    AD_BASE_DN=DC=startup11,DC=local
    AD_LIBRARIAN_GROUP_DN=CN=LIBRARIAN,CN=Users,DC=startup11,DC=local
    AD_ADMIN_USERS=zan_admin,other.user

Opis:

- `LDAP_URL` določa LDAP strežnik

- `AD_BASE_DN` določa osnovni DN

- `AD_LIBRARIAN_GROUP_DN` določa skupino z dovoljenji

## Docker zagon

Kljub temu da je možen lokalni zagon z `npm` (`npm install`, `npm run dev`), kar vam omogoča lokalno testiranje na <https://localhost:3443/> in <http://localhost:3000/> na serverju vedno buildamo to z dockerjem.

Build slike:

    docker build -t library-api-ad:latest .

Zagon kontejnerja:

    docker run -d \
      --name library-api-ad-test \
      -p 3000:3000 \
      -p 3443:3443 \
      -e LDAP_URL=ldap://192.168.11.201:389 \
      -e AD_DOMAIN=startup11.local \
      -e AD_BASE_DN=DC=startup11,DC=local \
      -e AD_LIBRARIAN_GROUP_DN=CN=LIBRARIAN,CN=Users,DC=startup11,DC=local \
      library-api-ad:latest

## Preverjanje delovanja

Ko imate enkrat zagnano bi morala biti spletna stran dostopna preko vseh računalnikov znotraj omrežja na <https://192.168.11.104:3443/> in <http://192.168.11.104:3000/>.

### Javni GET zahtevek

    curl -k -i https://192.168.11.104:3443/authors
    curl --http2 -k -i https://192.168.11.104:3443/authors
    curl -i http://192.168.11.104:3000/authors

### Vsebinsko pogajanje in podprti formati

JSON:

    curl -k -H "Accept: application/json" \
    https://192.168.11.104:3443/authors

XML:

    curl -k -H "Accept: application/xml" \
    https://192.168.11.104:3443/authors

HTML:

    curl -k \
    "https://192.168.11.104:3443/authors?format=html"

To je samo za authors imas pa tudi veliko drugih poti:

    GET /authors  - list all (public)
    GET /authors/:id  - single author (public)
    GET /authors/:id/books  - books by author (public)
    POST /authors  - create (requires librarian or admin)
    PUT /authors/:id  - update (requires librarian or admin)
    DELETE /authors/:id  - delete (requires admin only)
    GET /books  - list all, optional ?genre= filter (public)
    GET /books/:id  - single book (public)
    POST /books  - create (requires librarian or admin)
    PUT /books/:id  - update (requires librarian or admin)
    PATCH /books/:id/availability  - toggle availability (requires librarian or admin)
    DELETE /books/:id  - delete (requires admin only)

### LDAP avtorizacija

Rabis userja pod librarian ali admin za dodaten dostop.

- branje (GET) avtorjev in knjig — javno dostopno brez prijave

- ustvarjanje (POST) avtorjev in knjig

- posodabljanje (PUT) avtorjev in knjig

- brisanje (DELETE) je rezervirano za admin uporabnike

Za windows PowerShell:

    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}

    $b64 = [Convert]::ToBase64String(
      [Text.Encoding]::ASCII.GetBytes(
        'username:password'
      )
    )

    $headers = @{
      Authorization = "Basic $b64"
      'Content-Type'='application/json'
    }

    $body = @{
      name = 'Test Author'
    } | ConvertTo-Json

    Invoke-RestMethod `
      -Uri 'https://192.168.11.104:3443/authors' `
      -Method Post `
      -Headers $headers `
      -Body $body

Za linux:


    curl -i -X POST http://192.168.11.104:3000/authors \
      -H "Content-Type: application/json" \
      -u username:password \
      -d '{"name":"Test Author from Linux"}'

    curl -i -X DELETE http://192.168.11.104:3000/authors/5 \
      -u username:password

### Potrditev TLS certifikata

Za certifikat:

    openssl s_client -connect 192.168.11.104:3443 -servername 192.168.11.104 -showcerts
    curl -vkI https://192.168.11.104:3443/

Certifikati so self-signed zato če jim želiš zaupat jih rabiš naložiti v napravi:

    openssl s_client -connect 192.168.11.104:3443 -showcerts </dev/null \
      | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /tmp/library-192-168-11-104.crt

    sudo cp /tmp/library-192-168-11-104.crt /usr/local/share/ca-certificates/library-192-168-11-104.crt
    sudo update-ca-certificates

### GraphQL

Primer javnega GraphQL poizvedovanja:

    curl -k -X POST "https://192.168.11.104:32484/graphql" \
      -H "Content-Type: application/json" \
      -d '{"query":"{ authors { id name } }"}'

Primer zaščitene GraphQL mutacije z LDAP uporabnikom:

    $b64 = [Convert]::ToBase64String(
      [Text.Encoding]::ASCII.GetBytes('username:password')
    )

    $body = @{ query = 'mutation { createAuthor(name: "GraphQL Test") { id name } }' } | ConvertTo-Json

    Invoke-RestMethod `
      -Uri 'https://192.168.11.104:32484/graphql' `
      -Method Post `
      -Headers @{ Authorization = "Basic $b64"; 'Content-Type'='application/json' } `
      -Body $body

### Scriptum_kp

Scriptum je dostopen na spletnem mestu <a href="192.168.11.104:8080" class="uri">192.168.11.104:8080</a> ne uporablja LDAP uporabnikov ampak uporabnike na MongoDB bazi. Frontend je Angular,, backend je REST API, Node.js, Express. MongoDB baza ni na tem serverju ampak je na zunanjih mongo DB strežnikih.

# Raft

Raft storitev poteka na treh serverjih 192.168.11.101, 192.168.11.102, 192.168.11.103. Vse spremembe so sihronizirane preko etcd kljucov, vsaka ima svojo lokalno bazo ki se sinhronizira. To je update Rest storitve saj ta sedaj pošilja svojo bazo RAFT podatkovni bazi. Na serverju boste imeli veliko datotek:

- `raft-api-integration.js` - ta datoteka pomaga pri replikaciji in temu da se domenijo o vodji

- `sync-watcher.js` - gleda etcd sync ključe in jih doda v localno library-ha.db za nek razlog etcd se ni znal sam zmenit za ključe

- `query-ha-db.js` - node.js script da bere library-ha.db in sprinta autorje, uporabno za testiranje

- `test-graphql.js` - test samo za lokalno da preveri če je možno POST request narediti na qraphql

- `create-author.js`, `manual-replicate.js` - pomožne skripte za pomoč pri testiranju pisanja in repliciranja

## Branje baze

Če želite manualno prebrati bazo predvsem za testiranje in če se vam zdi da niso sinhornizirane.

    cd ~/library-api
    node query-ha-db.js

To vam bo izpisalo vsebino baze.

---

## Pretvorba med Markdown in LaTeX

Ukazi za pretvorbo (zahteva: `pandoc`):

- LaTeX -> Markdown (GitHub-flavored):

```bash
pandoc -s vyos_documentation.tex -t gfm -o vyos_documentation.md --wrap=none
```

- Markdown -> LaTeX:

```bash
pandoc -s vyos_documentation.md -o vyos_documentation.tex
```

Opomba: pri pretvorbi iz Markdowna v LaTeX lahko pride do manjših razlik v oblikovanju; preverite končni `.tex` in po potrebi prilagodite preambulo (pakete, nastavitve `listings`/`minted`).
