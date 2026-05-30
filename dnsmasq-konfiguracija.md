# Trenutna dnsmasq konfiguracija

Preverjena konfiguracija trenutno teče na strežniku in posluša na naslovu `192.168.11.105:53`.

Opomba: `dnsmasq` je v trenutni postavitvi opcijski notranji resolver. AD prijava deluje tudi brez njega, dokler VyOS in AD DNS ostaneta pravilno nastavljena.

## Aktivna konfiguracija

Datoteka: `/etc/dnsmasq.d/startup11.conf`

```conf
# Bind only to the DMZ address to avoid conflicts with systemd-resolved on localhost
listen-address=192.168.11.105
bind-interfaces

# Forward AD zone to AD DNS (preserves SRV records)
server=/startup11.local/192.168.11.201
server=/startup11.local/2001:1470:fffd:a9::201

# Upstream resolvers for non-local names
server=1.1.1.1
server=193.2.1.66
server=2001:1470:8000::66
server=2606:4700:4700::1111
```

## Kaj konfiguracija dela

- dnsmasq posluša samo na `192.168.11.105`.
- Vključeno je `bind-interfaces`, zato se veže le na izbrani vmesnik/naslov.
- Zahteve za `startup11.local` posreduje na AD DNS (`192.168.11.201` in `2001:1470:fffd:a9::201`).
- S tem se ohranijo AD SRV zapisi (npr. `_ldap._tcp.dc._msdcs.startup11.local`).
- Zahteve za ostale domene posreduje na javne upstream DNS strežnike.

## Trenutno stanje sistema

- Storitev: `dnsmasq` je aktivna.
- Poslušanje: vrata `53` so odprta na `192.168.11.105`.
- Gostitelj ima naslov `ens160 = 192.168.11.105/24` in IPv6 prefiks na istem vmesniku.

## Kako jo rekreirati

1. Namesti pakete:

   ```bash
   sudo apt update
   sudo apt install -y dnsmasq dnsutils
   ```

2. Ustvari konfiguracijsko datoteko:

   ```bash
   sudo tee /etc/dnsmasq.d/startup11.conf > /dev/null << 'EOF'
   # Bind only to the DMZ address to avoid conflicts with systemd-resolved on localhost
   listen-address=192.168.11.105
   bind-interfaces

   # Forward AD zone to AD DNS (preserves SRV records)
   server=/startup11.local/192.168.11.201
   server=/startup11.local/2001:1470:fffd:a9::201

   # Upstream resolvers for non-local names
   server=1.1.1.1
   server=193.2.1.66
   server=2001:1470:8000::66
   server=2606:4700:4700::1111
   EOF
   ```

3. Preveri sintakso:

   ```bash
   sudo dnsmasq --test
   ```

4. Ponovno zaženi storitev in omogoči samodejni zagon:

   ```bash
   sudo systemctl restart dnsmasq
   sudo systemctl enable dnsmasq
   ```

5. Preveri delovanje:

   ```bash
   systemctl status dnsmasq --no-pager
   ss -ltnup '( sport = :53 )'
   dig +short _ldap._tcp.dc._msdcs.startup11.local @192.168.11.105 SRV
   dig +short startup11.local @192.168.11.105 A
   dig +short startup11.local @192.168.11.105 AAAA
   dig +short example.com @192.168.11.105
   ```

## Kako jo spremeniš

- Če želiš, da dnsmasq posluša na drugem IP-ju, spremeni `listen-address`.
- Če želiš dodati novo interno domeno, dodaj novo vrstico `server=/domena.local/IP_DNS_streznika`.
- Za AD domeno ne uporabljaj `address=` zapisa, ker to skrije SRV zapise.
- Po vsaki spremembi izvedi `sudo dnsmasq --test` in nato `sudo systemctl restart dnsmasq`.

## Opomba

Ta zapis odraža trenutno preverjeno stanje in je namenjen ponovni postavitvi istega DNS vedenja na isti napravi ali na napravi z enakim naslovom `192.168.11.105`.

## mDNS / systemd-resolved - opomba

Na nekaterih Linux gostiteljih je domena `.local` rezervirana za mDNS (Avahi) in `systemd-resolved` lahko zavrne običajne DNS poizvedbe za takšne domene. To je posebej pogosto na novih `ipv6only` odjemalcih. Če imate težave z reševanjem `startup11.local` na gostitelju, uporabite naslednje ukaze, da usmerite to domeno k omrežnemu resolverju:

```bash
# Nastavi routing domain na vmesniku (primer: ens160)
sudo resolvectl domain ens160 ~startup11.local

# Po potrebi ročno nastavi DNS strežnik za ta vmesnik (VyOS DNS v ipv6only omrežju)
sudo resolvectl dns ens160 fd11:11:11::1

# Onemogoči mdns na vmesniku
sudo resolvectl mdns ens160 no

# Počisti predpomnilnik
sudo resolvectl flush-caches

# Preizkusi
resolvectl query startup11.local
dig +short _ldap._tcp.dc._msdcs.startup11.local @192.168.11.1 SRV
```

## Ubuntu Desktop 26.04 na ipv6only

Če `nslookup startup11.local` ne deluje, `nslookup startup11.local fd11:11:11::1` pa deluje, potem je problem v privzetem resolverju na odjemalcu, ne v AD DNS.

Na Ubuntu Desktop 26.04 privzeti lookup pogosto gre prek lokalnega stub resolverja na `127.0.0.1`. Preveri, da ima ta resolver ali vmesnik nastavljeni DNS strežnik `fd11:11:11::1` prek `systemd-resolved` ali NetworkManager. Če DHCPv6 ne dostavlja DNS strežnika pravilno, ga nastavi ročno na vmesniku, nato očisti predpomnilnik in ponovno testiraj.

To je bil tudi dejanski vzrok pri novem Ubuntu Desktop 26.04 na `ipv6only`: DHCPv6 je DNS naslov sicer dostavil, vendar je `systemd-resolved` za domeno `.local` še vedno uporabljal lokalni stub na `127.0.0.1` in poizvedbe za `startup11.local` ni usmerjal na unicast DNS.

### Trajna nastavitev po rebootu

Ukaz `resolvectl domain ens160 ~startup11.local` je začasen in velja samo do naslednjega reboot-a ali ponovne konfiguracije omrežja. Za trajno nastavitev ga zapiši v NetworkManager profil povezave:

```bash
nmcli connection show
nmcli connection modify "<connection-name>" ipv6.dns "fd11:11:11::1"
nmcli connection modify "<connection-name>" ipv6.dns-search "~startup11.local"
nmcli connection modify "<connection-name>" ipv6.ignore-auto-dns yes
nmcli connection up "<connection-name>"
```

Če uporabljaš `systemd-networkd`, postavi isto v `.network` datoteko za vmesnik:

```ini
[Match]
Name=ens160

[Network]
DNS=fd11:11:11::1
Domains=~startup11.local
```

Po spremembi ponovno zaženi omrežno storitev ali odklopi/priklopi povezavo.

Ta popravek smo uporabili pri konfiguraciji gostitelja, kjer teče `wg-portal`, da so DNS poizvedbe za `startup11.local` pravilno posredovane na AD DNS preko omrežnega resolverja (VyOS / DHCP-provided DNS).

## Opomba o korenski domeni

Če `startup11.local` razreši pravilno, vendar `ping startup11.local` ali `ping -6 startup11.local` še vedno ne deluje, uporabi gostiteljsko ime pod cono, npr. `ad.startup11.local`.

Na nekaterih Linux odjemalcih je bare apex domene bolj občutljiv na lokalno resolver politiko kot običajni host zapisi, zato je za testiranje in vsakodnevno rabo bolj zanesljivo uporabiti eksplicitni host zapis kot pa sam korenski zapis cone.