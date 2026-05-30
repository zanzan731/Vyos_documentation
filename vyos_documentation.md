---
date: 2026-05-30
title: Dokumentacija VyOS usmerjevalnika - startup11
---

# Naloga in zasnova omrežja

V tej dokumentaciji opišemo nalogo podjetja in predlagano omrežno zasnovo. Podjetje je start-up brez obstoječe IT infrastrukture; cilj je postaviti ločena omrežna segmenta za uporabnike in za strežnike, zagotoviti varen dostop do interneta in izpostaviti le izbrane javne storitve.

## Cilji naloge

- Postaviti omrežje z ločenimi segmenti za **uporabnike** in **strežnike** (strogo ločeno prometno okolje).

- Vsi strežniki so gostovani v DMZ (po zahtevah naloge) — javne in interne storitve bodo fizično v DMZ, vendar z omejitvami dostopa.

- Izpostaviti navzven le izbrane storitve: WireGuard, `wg-portal` (HTTPS) in REST frontend (HTTPS).

- Kritične administrativne in imenik storitve (AD, DNS, SNMP) dostopne samo znotraj omrežja in preko VPN (ni direktnega WAN dostopa).

- Ohranjati poseben **ipv6only** segment za eksperimentalne/izobraževalne potrebe z NPTv6 preslikavo za odhodni promet.

## Opredelitev segmentov

- **DMZ (eth1, 192.168.X.0/24)**: vsi strežniki (REST, wg-portal, WireGuard endpoint, AD/DNS, SNMP, ostali). Fizicni lokaciji strežnikov sta v DMZ, vendar dostopi do nekaterih storitev omejeni z omrežnimi ACL.

- **INTERNAL (eth2, 10.X.0.0/24)**: uporabniške delovne postaje, administrativne postaje in monitoring hosti. Od tu je dovoljen nadzorovan dostop do AD/DNS/SNMP v DMZ.

- **IPV6ONLY (eth3, ULA + NPTv6)**: eksperimentalni IPv6-only segment; omogoča učenje in testiranje IPv6 funkcionalnosti. Izhodni promet je preko NPTv6 preslikave na javni IPv6.

## Izolacija segmentov

Segmenti se izolirajo z naslednjimi ukrepi:

- **Layer-3 ločitev (VyOS routing + ACL)**: vsak segment ima ločen subnet in VyOS izvaja routing ter aplikacijo politk (default-deny ter strog seznam izjem).

- **VLAN/PortGroup** na hipervizorju: DMZ, INTERNAL in IPV6ONLY so v ločenih PortGroup/VLANih, management port group pa ločen in omejen.

- **Host-firewall** (vsak strežnik in vsaka delovna postaja): default-deny inbound, dovoljenje samo za nujne storitve; admin dostop omejen na internal in VPN izvore.

- **Split DNS / conditional forward**: notranji klienti uporabljajo AD DNS za ‘startup11.local‘, zunanji resolverji pa javne strežnike — prepreči izpostavitev notranjih zapisov.

- **Monitoring in logging**: monitoring host ima izključno dovoljenje za SNMP/agent promet; centralizirano beleženje (syslog) in netflow/sflow za analizo.

## Načrt požarnega zidu (visoka raven)

Osnovna politika: *default deny* za vse vhodne in posredovane povezave, dovoli le eksplicitno definirane poti.

- **WAN (eth0) -\> VyOS**: dovoli `established, related`; dovoli DNAT za:

  - UDP 51820 -\> WireGuard endpoint v DMZ

  - TCP 443 -\> reverse-proxy ali neposredno na `wg-portal`/REST frontend (DMZ)

- **WAN -\> DMZ (direktni)**: ne dovoli neposrednega dostopa do AD/DNS/SNMP; dovoli samo zgoraj navedene DNAT pravila.

- **INTERNAL -\> DMZ**: dovoli le potrebne storitve:

  - DNS (53) do AD/DNS

  - LDAP/LDAPS (389/636), Kerberos (88), Global Catalog (3268/3269) do AD

  - HTTP/HTTPS do REST frontend

  - SSH/RDP samo iz administrativne podmreže ali VPN

- **DMZ -\> INTERNAL**: privzeto blokiraj; dovoli le potrebno (npr. monitoring/reporting na notranji monitoring host), definirano z virnim IP-jem.

- **INTERNAL -\> INTERNET**: dovoli outbound HTTP/HTTPS/DNS z NAT/masquerade na VyOS.

- **VPN (WireGuard)**: uporabniški VPN ima omejen dostop; administrativni VPN ima dostop do DMZ in internal za upravljanje.

- **Host-firewall pravila**: na vsakem strežniku implementiraj default-deny inbound; dovoli le servise, ki jih strežnik ponuja, z omejitvijo vira na internal/VPN ali specificirane monitoring host-e.

V nadaljevanju dokumentacije so podrobnosti konfiguracij in primeri ukazov za VyOS in predloge za host-firewall.

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

| **Ime strežnika** | **IP naslov** | **IPv6 naslov** | **Namen** |
|:---|:---|:---|:---|
| raft1 | 192.168.11.101 | 2001:1470:fffd:a9::124 | Raft (cluster node) |
| raft2 | 192.168.11.102 | 2001:1470:fffd:a9::114 | Raft (cluster node) |
| raft3 | 192.168.11.103 | 2001:1470:fffd:a9::16b | Raft (cluster node) |
| rest | 192.168.11.104 | 2001:1470:fffd:a9::115 | REST API / ostali servisi |
| dns-srv | 192.168.11.105 | \- | DNS strežnik (lokalni) |
| wireguard | 192.168.11.106 | 2001:1470:fffd:a9::1c8 | WireGuard VPN končna točka |
| snmp | 192.168.11.107 | 2001:1470:fffd:a9::17a | SNMP / monitoring cilj |
| new_wg | 192.168.11.108 | 2001:1470:fffd:a9::18d | New WireGuard-related host |
| AD (dmz windows 1) | 192.168.11.201 | 2001:1470:fffd:a9::201 | Active Directory (Domain Controller) |

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

IPv6 ima podobna vhodna pravila (dovoli `established/related` in SSH na `eth0`), forward pravilo za WireGuard (UDP port 51820 na vhodnem vmesniku `eth0`) in pravila 210-241 za dostop do AD strežnika na `2001:1470:fffd:a9::201`.

# Storitve

## DHCPv4

DHCP server ima dve skupini: **SERVERS** (192.168.11.0/24) z navedenimi statičnimi mapami in **USERS** (10.11.0.0/24) za uporabniške naprave z avtomatskim razponom.

| **Skupina** | **Subnet / opomba**                            |
|:------------|:-----------------------------------------------|
| SERVERS     | 192.168.11.0/24 (statične mape)                |
| USERS       | 10.11.0.0/24 (dinamični range 10.11.0.100-200) |

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
| snmp               | 00:0c:29:69:75:09 | 192.168.11.107 |
| new_wg             | 00:0c:29:f9:2a:a8 | 192.168.11.108 |
| AD (dmz windows 1) | 00:0c:29:07:cf:1c | 192.168.11.201 |

## DHCPv6

DHCPv6 podeljuje naslove v subnetu `2001:1470:fffd:a9::/64` z range `::100` - `::1ff`. Ime strežnika za DHCPv6 je `2001:1470:fffd:a9::1`.

#### Statične DHCPv6 mape

Spodaj so navedene statične DHCPv6 mape z DUID/identifikatorji, ki se uporabljajo v konfiguraciji VyOS:

| **Host** | **DHCPv6 naslov** | **DUID / identifier** |
|:---|:---|:---|
| dmz-windows-AD | 2001:1470:fffd:a9::201 | 00:01:00:01:31:86:a4:b0:00:0c:29:07:cf:26 |
| raft1 | 2001:1470:fffd:a9::124 | 00:02:00:00:ab:11:2b:e2:d4:90:70:f3:b3:37 |
| raft2 | 2001:1470:fffd:a9::114 | 00:02:00:00:ab:11:e1:94:d4:8a:18:52:ad:98 |
| raft3 | 2001:1470:fffd:a9::16b | 00:02:00:00:ab:11:92:37:c8:9a:00:b8:67:77 |
| rest | 2001:1470:fffd:a9::115 | 00:02:00:00:ab:11:5a:9d:49:65:ce:4a:b2:48 |
| snmp | 2001:1470:fffd:a9::17a | 00:02:00:00:ab:11:b8:b7:97:e3:eb:3c:a5:52 |
| wg | 2001:1470:fffd:a9::1c8 | 00:02:00:00:ab:11:80:f9:48:e8:e6:e2:12:59 |
| new_wg | 2001:1470:fffd:a9::18d | 00:02:00:00:ab:11:dd:e2:8d:62:21:b3:d9:00 |

## DNS (posredovanje in split DNS)

DNS posredovanje na VyOS sprejema poizvedbe iz notranjih omrežij in uporablja conditional forward za AD domeno.

**Ključna split-DNS logika:**

- poizvedbe za `startup11.local` se na VyOS preusmerijo na AD DNS `192.168.11.201`;

- vse ostale poizvedbe gredo na javne upstream DNS strežnike (ARNES + Cloudflare).

**AD DNS server (authoritative):** `192.168.11.201` / `2001:1470:fffd:a9::201`

### Trenutno stanje AD DNS

Trenutna AD zona `startup11.local` vsebuje ključne notranje zapise za domeno, DC in DMZ strežnike:

- korenski zapis `@` vsebuje A zapis `192.168.11.201` in AAAA zapis `2001:1470:fffd:a9::201`;

- NS in SOA na vrhu cone kažeta na `win-sgi52j8519e.startup11.local.`;

- standardni AD SRV zapisi so prisotni za `_gc._tcp`, `_kerberos._tcp`, `_kerberos._udp`, `_ldap._tcp` in `_kpasswd._tcp` ter ustrezne `Default-First-Site-Name` in `ForestDnsZones` / `DomainDnsZones` podcone;

- glavni DC gostitelj `win-sgi52j8519e` ima A zapis `192.168.11.201` in AAAA zapis\
  `2001:1470:fffd:a9::201`;

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

- `startup11.local` se posreduje na AD DNS: `192.168.11.201` in `2001:1470:fffd:a9::201`

- Konfiguracija: `/etc/dnsmasq.d/startup11.conf`

**Pomembno za AD prijavo:** notranji odjemalci morajo za `startup11.local` dobiti SRV zapise iz AD DNS, ne samo A/AAAA zapisov. Zato je v VyOS nastavljen:

    set service dns forwarding domain startup11.local name-server 192.168.11.201
  set service dns forwarding domain startup11.local name-server 2001:1470:fffd:a9::201
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
    server=/startup11.local/2001:1470:fffd:a9::201

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

Pri novem Ubuntu Desktop 26.04 na `ipv6only` je bil dejanski problem enak: DHCPv6 je sicer dostavil DNS strežnik `fd11:11:11::1`, vendar je `systemd-resolved` za `.local` še vedno uporabljal lokalni stub na `127.0.0.1` in brez routing domene `~startup11.local` ni pošiljal poizvedb na unicast DNS.

    # Nastavi routing domain (tilde pomeni routing domain)
    sudo resolvectl domain ens160 ~startup11.local

    # Onemogoci mdns na vmesniku
    sudo resolvectl mdns ens160 no

    # Pocisti predpomnilnik, ce je potrebno
    sudo resolvectl flush-caches

    # Preizkus
    resolvectl query startup11.local
    dig +short _ldap._tcp.dc._msdcs.startup11.local @192.168.11.1 SRV

  Za trajno nastavitev v NetworkManager profilu:

    nmcli connection show
    nmcli connection modify "<connection-name>" ipv6.dns "fd11:11:11::1"
    nmcli connection modify "<connection-name>" ipv6.dns-search "~startup11.local"
    nmcli connection modify "<connection-name>" ipv6.ignore-auto-dns yes
    nmcli connection up "<connection-name>"

Ta rešitev ohranja mDNS obnašanje za druge gostitelje, hkrati pa zagotavlja, da poizvedbe za `startup11.local` dosežejo avtoritativni AD DNS.

## NTP

NTP sinhronizacija uporablja naslednje strežnike:

| **NTP strežnik** |
|:-----------------|
| ntp.arnes.si     |
| time1.vyos.net   |
| time2.vyos.net   |
| time3.vyos.net   |

# Monitoring in SNMP

Za spremljanje metrik v DMZ uporabljamo preprost monitoring stack: Prometheus (scrape in shranjevanje), `snmp_exporter` (pretvornik SNMP→Prometheus) in Grafana (vizualizacija). `snmp_exporter` pobira metrike z naprave VyOS prek SNMP v2c in jih izpostavi na svojem HTTP vmesniku, ki ga nato pobira Prometheus.

## Komponente in porti

- **snmp_exporter**: 192.168.11.107:9116 (TCP) - endpoint exporterja, npr.\
  `http://192.168.11.107:9116/snmp`

- **Prometheus**: 192.168.11.107:9090 (TCP) - scrape cilj in uporabniški vmesnik

- **Grafana**: 192.168.11.107:3000 (TCP) - nadzorne plošče in vizualizacija

- **VyOS SNMP**: 192.168.11.1:161 (UDP) - SNMP agent na usmerjevalniku (v2c community)

## VyOS SNMP (primer)

Omogočite SNMP na VyOS in ga vežite na DMZ naslov:

    set service snmp community startup11 authorization 'ro'
    set service snmp contact 'ops@startup11.local'
    set service snmp listen-address 192.168.11.1
    commit
    save

## Docker Compose primer (snmp_exporter + Prometheus + Grafana)

Namestite to na monitoring gostitelja (192.168.11.107) in prilagodite poti/volumne po potrebi.

    version: '3'
    services:
      snmp\_exporter:
        image: prom/snmp-exporter:latest
        ports:
          - "9116:9116"
        volumes:
          - ./snmp.yml:/etc/snmp\_exporter/snmp.yml

      prometheus:
        image: prom/prometheus:latest
        ports:
          - "9090:9090"
        volumes:
          - ./prometheus.yml:/etc/prometheus/prometheus.yml
        depends_on:
          - snmp\_exporter

      grafana:
        image: grafana/grafana:latest
        ports:
          - "3000:3000"
        depends_on:
          - prometheus

## Konfiguracija Prometheusa (primer scrape job)

Dodajte ‘scrape‘ nalogo, da Prometheus pobira metrike od exporterja (če ne uporabljate Docker Compose DNS, zamenjajte ‘snmp_exporter:9116‘ z ‘192.168.11.107:9116‘):

    scrape_configs:
      - job_name: 'snmp'
        static_configs:
          - targets: ['192.168.11.1']
        metrics_path: /snmp
        params:
          module: [vyos]
          auth: [vyos_auth]
        relabel_configs:
          - source_labels: [__address__]
            target_label: __param_target
          - source_labels: [__param_target']
            target_label: instance
          - target_label: __address__
            replacement: 192.168.11.107:9116

## Generator in snmp.yml

Uporabite uradni generator za ‘snmp_exporter‘, da ustvarite prilagojen ‘snmp.yml‘ za VyOS. Postopek v grobem:

- Naredite ‘generator.yml‘ z ‘auth‘ sekcijo (community ‘startup11‘) in modulom ‘vyos‘, ki naredi ‘walk‘ za ‘1.3.6.1.2.1.1.3‘ (sysUpTime), ‘1.3.6.1.2.1.2‘ (ifTable) in ‘1.3.6.1.2.1.31.1.1‘ (ifXTable).

- Zaženite generator (kot container ali binarko) in dobljeni ‘snmp.yml‘ kopirajte na exporter gostitelja v ‘/etc/snmp_exporter/snmp.yml‘.

## Testiranje

    curl "http://192.168.11.107:9116/snmp?module=vyos&target=192.168.11.1"
    snmpwalk -v2c -c startup11 192.168.11.1 1.3.6.1.2.1.1.3.0

## Router Advertisements (RA)

RA so omogočeni na:

- `eth1`: prefix `2001:1470:fffd:a9::/64` (managed flag, no-autonomous)

- `eth2`: prefix `2001:1470:fffd:aa::/64`

- `eth3`: prefix `fd11:11:11::/64`, name-server `fd11:11:11::1`

## SSH

SSH je konfiguriran za prijavo prek ključev (avtentikacija z geslom je onemogočena) na privzetem portu 22. Če želite začasno omogočiti prijavo z geslom, uredite datoteko\
`/etc/ssh/sshd_config.d/50-cloud-init.conf` in nastavite `PasswordAuthentication yes`, nato ponovno zaženite `sshd`.

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

## Priključitev računalnikov v domeno

Vsi računalniki, ki bodo uporabljali storitve domene `startup11.local`, morajo biti ustrezno pridruženi domeni Active Directory. Postopek se nekoliko razlikuje glede na operacijski sistem.

### Linux

Pri novejših različicah Ubuntu Linuxa je med grafično namestitvijo sistema na voljo možnost *Use Active Directory*. Ta se nahaja v koraku *Create your account*. V tem primeru:

1.  Označite možnost *Use Active Directory*.

2.  Vnesite ime domene: `startup11.local`.

3.  Za pridružitev uporabite uporabniški račun z ustreznimi pravicami v domeni.

Če sistem med namestitvijo ni bil priključen v domeno, je to mogoče storiti naknadno z uporabo naslednjih orodij.

Najprej namestimo vse potrebne pakete:

    sudo apt install sssd sssd-ad realmd adcli krb5-user

Preverimo, ali je domena dosegljiva:

    sudo realm discover startup11.local

Nato računalnik priključimo v domeno:

    sudo realm join startup11.local

Po uspešni prijavi je priporočljiv ponovni zagon sistema.

### Windows

V operacijskem sistemu Windows lahko računalnik pridružimo domeni prek grafičnega vmesnika:

1.  Odprite **Nastavitve** (*Settings*).

2.  Izberite **Sistem** (*System*).

3.  Odprite **Informacije o sistemu** (*About*).

4.  Kliknite **Preimenuj ta računalnik (napredno)** (*Rename this PC (advanced)*).

5.  Izberite možnost **ID omrežja** (*Network ID*).

6.  Sledite čarovniku za pridružitev domeni.

7.  Kot ime domene vnesite `startup11.local`.

8.  Ob pozivu vnesite poverilnice uporabniškega računa, ki ima pravico dodajati računalnike v domeno.

Po uspešni pridružitvi bo sistem zahteval ponovni zagon. Po ponovnem zagonu se lahko uporabniki prijavijo z domenimi računi.

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

# WireGuard

## Splošne informacije

WireGuard VPN je nastavljeno na napravi na IP naslovu `192.168.11.106` v DMZ omrežju. Konfiguracija je bila avtomatsko generirana s **pivpn** skripto, ki poenostavi upravljanje in vzpostavitev WireGuard VPN strežnika.

Trenutna postavitev ostane nespremenjena v prvi fazi. Podroben fazni načrt, ki ohrani obstoječi PiVPN/NAT in nato v drugi fazi preseli dual WireGuard stack na novo VM z `wg-portal`, je opisan v `phased-firewall-plan.md`. Ta novi načrt nadomešča prejšnje pomožne predloge za `wg-client`.

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
    New-ADUser -Name "wgportal_bind" -SamAccountName wgportal_bind -AccountPassword
    (ConvertTo-SecureString 'StrongP@ssw0rd' -AsPlainText -Force) -Enabled $true

    # Po potrebi dodaj uporabnike v administratorsko skupino
    Add-ADGroupMember -Identity "Domain Admins" -Members "zanadmin","pavlogal"

**Preizkusi in dnevniški pregledi:**

- Testirajte LDAP poizvedbe z orodjem `ldapsearch` kjer je na voljo.

- Preverjajte dnevniške datoteke aplikacije za napake pri bindanju ali iskanju uporabnika.

- Če uporabniki ne vidijo konfiguracij, preverite, da so vklopljene nastavitve\
  `create_default_peer_on_login` in `self_provisioning_allowed`.

**Opomba:** Po vsaki spremembi preveri sintakso in ponovno zaženi storitev, da se spremembe uveljavijo.

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

Scriptum je dostopen na spletnem mestu <a href="192.168.11.104:8080" class="uri">192.168.11.104:8080</a> in <a href="88.200.24.241:8080" class="uri">88.200.24.241:8080</a> ne uporablja LDAP uporabnikov ampak uporabnike na MongoDB bazi. Frontend je Angular,, backend je REST API, Node.js, Express. MongoDB baza ni na tem serverju ampak je na zunanjih mongo DB strežnikih.

# Raft

Raft storitev poteka na treh serverjih 192.168.11.101, 192.168.11.102, 192.168.11.103. Vse spremembe so sihronizirane preko etcd kljucov, vsaka ima svojo lokalno bazo ki se sinhronizira. To je update Rest storitve saj ta sedaj pošilja svojo bazo RAFT podatkovni bazi. Na serverju boste imeli veliko datotek:

- `raft-api-integration.js` - ta datoteka pomaga pri replikaciji in temu da se domenijo o vodji

- `sync-watcher.js` - gleda etcd sync ključe in jih doda v localno library-ha.db za nek razlog etcd se ni znal sam zmenit za ključe

- `query-ha-db.js` - node.js script da bere library-ha.db in sprinta autorje, uporabno za testiranje

- `test-graphql.js` - test samo za lokalno da preveri če je možno POST request narediti na qraphql

- `create-author.js`, `manual-replicate.js` - pomožne skripte za pomoč pri testiranju pisanja in repliciranja

## Pregled in preverjanje baze podatkov

Za namene testiranja ali preverjanja pravilne sinhronizacije podatkov med vozlišči lahko vsebino baze podatkov preberete neposredno iz ukazne vrstice.

    cd ~/library-api
    node query-ha-db.js

Skript privzeto izvede poizvedbo:

``` sql
SELECT id, name FROM authors;
```

Rezultat poizvedbe se izpiše v terminalu, kar omogoča hitro preverjanje vsebine baze podatkov.

Če želite izvesti druge SQL poizvedbe, lahko ustrezno prilagodite datoteko `query-ha-db.js` in vanjo vnesete želen SQL stavek.

Podatkovna baza se nahaja v datoteki:

    library-ha.db

Priporočljivo je, da se pred posegi v podatkovno bazo ustvari varnostna kopija, zlasti v produkcijskem okolju.

# Pretvorba med Markdown in LaTeX

- LaTeX Markdown (GitHub-flavored):

      pandoc -s vyos_documentation.tex -t gfm -o vyos_documentation.md --wrap=none

- Markdown LaTeX:

      pandoc -s vyos_documentation.md -o vyos_documentation.tex
