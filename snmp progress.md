Grafični prikaz podatkov v oblačnih aplikacijah: Prometheus + Grafana
Cacti je precej staro orodje za nadzor, v zadnjem času se je predvsem s pohodom Docker kontejnerjev in t.i. cloud-native aplikacij precej bolj razširil prikaz podatkov z drugimi orodji. Eno najbolj uporabljanih in tudi "najlepših" je v zadnjem času ravno Grafana (grafana.org). Grafana je samo komponenta, ki vizualizira podatke, le-te pa moramo zbirati z drugim orodjem. Tu se je kot precej uspešno odprtokodno orodje uveljavil projekt Prometheus (prometheus.io), ki ga vodi Cloud-Native Computing Foundation (cncf.io).

Instalirati morate tri komponente:

Prometheus (prometheus.io)
Prometheus snmp_exporter (https://github.com/prometheus/snmp_exporter): le-ta zbira preko SNMP protokola vrednosti števcev na strežnikih, ki so dostopni preko SNMP (v našem primeru bo to npr. VyOS, vizualizirali bomo trenutno zasedeno pasovno širino na vmesnikih)
Grafana (http://docs.grafana.org/)
Vse tri komponente instalirajmo na strežnik v vaši DMZ coni. Predvidevamo, da je v VyOSu vklopljen in dostopen SNMP (preverite s snmpwalk!).

Najprej namestimo Prometheus snmp_exporter (https://github.com/prometheus/snmp_exporter - sam sem uporabil verzijo 0.1.0). Kot /etc/snmp_exporter/snmp.yml konfiguracijo mu bomo dodali prilagojeno konfiguracijo za Vyatto (glej https://raw.githubusercontent.com/cagiti/snmp_exporter/0575970a84eee04bd4a0118693ebb3fd0d61ba2c/snmp.yml), ki ji bomo dodali verzijo in SNMP community string (spodaj označen s public, le tega spremenite v tistega, ki ste ga nastavili na VyOSu!):

# Vyatta module: interface stats and uptime.
vyatta:
  version: 2
  auth:
    community: public
  walk:
    - 1.3.6.1.2.1.1.3
    - 1.3.6.1.2.1.2
    - 1.3.6.1.2.1.31.1.1
  metrics:
    - name: sysUpTime
      oid: 1.3.6.1.2.1.1.3
    - name: ifNumber
      oid: 1.3.6.1.2.1.2.1
    - name: ifMtu
      oid: 1.3.6.1.2.1.2.2.1.4
      indexes:
        - labelname: ifMtu
          type: Integer32
      lookups:
        - labels: [ifMtu]
          labelname: ifDescr
          oid: 1.3.6.1.2.1.2.2.1.2
    - name: ifSpeed
      oid: 1.3.6.1.2.1.2.2.1.5
      indexes:
        - labelname: ifSpeed
          type: Integer32
      lookups:
        - labels: [ifSpeed]
          labelname: ifDescr
          oid: 1.3.6.1.2.1.2.2.1.2
    - name: ifAdminStatus
      oid: 1.3.6.1.2.1.2.2.1.7
      indexes:
        - labelname: ifAdminStatus
          type: Integer32
      lookups:
        - labels: [ifAdminStatus]
          labelname: ifDescr
          oid: 1.3.6.1.2.1.2.2.1.2
    - name: ifOperStatus
      oid: 1.3.6.1.2.1.2.2.1.8
      indexes:
        - labelname: ifOperStatus
          type: Integer32
      lookups:
        - labels: [ifOperStatus]
          labelname: ifDescr
          oid: 1.3.6.1.2.1.2.2.1.2
    - name: ifInOctets
      oid: 1.3.6.1.2.1.2.2.1.10
      indexes:
        - labelname: ifInOctets
          type: Integer32
      lookups:
        - labels: [ifInOctets]
          labelname: ifDescr
          oid: 1.3.6.1.2.1.2.2.1.2
    - name: ifInUcastPkts
      oid: 1.3.6.1.2.1.2.2.1.11
      indexes:
        - labelname: ifInUcastPkts
          type: Integer32
      lookups:
        - labels: [ifInUcastPkts]
          labelname: ifDescr
          oid: 1.3.6.1.2.1.2.2.1.2
    - name: ifInNUcastPkts
      oid: 1.3.6.1.2.1.2.2.1.12
      indexes:
        - labelname: ifInNUcastPkts
          type: Integer32
      lookups:
        - labels: [ifInNUcastPkts]
          labelname: ifDescr
          oid: 1.3.6.1.2.1.2.2.1.2
    - name: ifInDiscards
      oid: 1.3.6.1.2.1.2.2.1.13
      indexes:
        - labelname: ifInDiscards
          type: Integer32
      lookups:
        - labels: [ifInDiscards]
          labelname: ifDescr
          oid: 1.3.6.1.2.1.2.2.1.2
    - name: ifInErrors
      oid: 1.3.6.1.2.1.2.2.1.14
      indexes:
        - labelname: ifInErrors
          type: Integer32
      lookups:
        - labels: [ifInErrors]
          labelname: ifDescr
          oid: 1.3.6.1.2.1.2.2.1.2
    - name: ifInUnknownProtos
      oid: 1.3.6.1.2.1.2.2.1.15
      indexes:
        - labelname: ifInUnknownProtos
          type: Integer32
      lookups:
        - labels: [ifInUnknownProtos]
          labelname: ifDescr
          oid: 1.3.6.1.2.1.2.2.1.2
    - name: ifOutOctets
      oid: 1.3.6.1.2.1.2.2.1.16
      indexes:
        - labelname: ifOutOctets
          type: Integer32
        - labelname: ifOutOctets
```


# SNMP Exporter Setup for VyOS + Prometheus

## Cilj
Vzpostaviti `snmp_exporter` konfiguracijo za **VyOS**, da Prometheus lahko bere interface metrike (sysUpTime, ifTable, ifXTable, HC counters, errors, discards, multicast/broadcast).

---

## 1. Konfiguracija SNMP na VyOS

Na VyOS omogoči SNMP v2c z ustreznim community stringom (primer tvoje konfiguracije):

```bash
set service snmp community startup11 authorization 'ro'
set service snmp contact 'pd43760@student.uni-lj.si'
set service snmp listen-address 192.168.11.1
set service snmp location 'FRI'
commit
save
```

Preveri dostop:

```bash
snmpwalk -v2c -c startup11 192.168.11.1 1.3.6.1.2.1.1.3.0
```

Rezultat:

```
SNMPv2-MIB::sysUpTime.0 = Timeticks: (20642982) 2 days, 9:20:29.82
```

---

## 2. Postavitev Docker okolja

Ustvari `docker-compose.yml` za `snmp_exporter` in `prometheus`:

```yaml
services:
  snmp_exporter:
    image: prom/snmp-exporter:latest
    container_name: snmp_exporter
    volumes:
      - ./snmp.yml:/etc/snmp_exporter/snmp.yml
    ports:
      - "9116:9116"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped
    depends_on:
      - snmp_exporter

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:
```

Zaženi:

```bash
docker compose up -d
```

---

## 3. Priprava generator.yml

Ustvari `generator.yml` (uporabi community `startup11`, kot je nastavljen na VyOS):

```yaml
auths:
  vyos_auth:
    version: 2
    community: startup11

modules:
  vyos:
    auth: vyos_auth
    walk:
      - 1.3.6.1.2.1.1.3    # sysUpTime
      - 1.3.6.1.2.1.2      # ifTable
      - 1.3.6.1.2.1.31.1.1 # ifXTable
    lookups:
      - source_indexes: [ifIndex]
        lookup: ifDescr
    overrides:
      ifDescr:
        type: DisplayString
```

Primer generator orodja in dokumentacijo najdeš tukaj: https://github.com/prometheus/snmp_exporter/tree/main/generator

---

## 4. MIB datoteke

Namesti MIB‑e:

```bash
sudo apt install snmp-mibs-downloader
```

Uporabi `/var/lib/mibs/ietf` kot mount point. Če pride do napak, uporabi `--no-fail-on-parse-errors` ali ustvari `mibs_clean` mapo z osnovnimi MIB‑i (`SNMPv2-MIB`, `IF-MIB`, `IP-MIB`, `TCP-MIB`, `UDP-MIB`).

---

## 5. Generiranje snmp.yml

Zaženi generator:

```bash
docker run --rm \
  -v $(pwd):/opt \
  -v /var/lib/mibs/ietf:/opt/mibs \
  prom/snmp-generator generate --no-fail-on-parse-errors
```

Rezultat: `snmp.yml` z modulom `vyos` in auth blokom `vyos_auth`.

---

## 6. Odpravljanje napak

- **Problem:** `Unknown auth 'public_v2'`  
  - V nekaterih primerih generator ustvari auth blok, a modul nima `auth` reference, ali pa se imenuje drugače kot tisti, ki ga kliče exporter.  
  - Rešitev: zagotovite, da `generator.yml` vsebuje auth z imenom, ki ga želite uporabiti (npr. `public_v2`) in da modul to auth referencira. Vzorec (`generator.yml`) zgoraj uporablja `public_v2` (community `public`) in modul `vyos` z `auth: public_v2`.
  - Po spremembi ponovno zaženite generator, da se ustvari `snmp.yml`, ali pa ročno v `snmp.yml` dodajte ustrezno `auth:` vrstico pod modulom.

---

## 7. Testiranje exporterja

Preveri z curl:

```bash
curl "http://192.168.11.107:9116/snmp?module=vyos&target=192.168.11.1"
```

Če je auth pravilno povezan, exporter vrne SNMP metrike.

---

## 8. Prometheus konfiguracija

Dodaj scrape job v `prometheus.yml`:

```yaml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: 'snmp'
    static_configs:
      - targets:
        - 192.168.11.1   # IP tvojega VyOS routerja
    metrics_path: /snmp
    params:
      module: [vyos]
      auth: [vyos_auth]
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: snmp_exporter:9116
```

Restartaj Prometheus:

```bash
docker compose restart prometheus
```

---

## 9. Grafana konfiguracija

- Dostop: Grafana teče na portu `3000` (v Docker Compose stacku kot `grafana`). Odpri v brskalniku: `http://<grafana_host>:3000` (ali `http://localhost:3000`/VPN). Privzeto: `admin` / `admin` — ob prvem prijavljanju spremeni geslo.

- Dodaj Prometheus datasource:
  - Name: `Prometheus`
  - Type: `Prometheus`
  - URL: `http://prometheus:9090` (če uporabljaš Docker Compose z imeni servisov) ali `http://<prometheus_host>:9090`.
  - Access: `Server (default)`.
  - Save & Test: preveri, da se poveže.

- Uvoz dashboarda za SNMP interface throughput:
  - GUI: Dashboards → Import → uporabi Dashboard ID `21962` (1124 je outdated) ali prilepi URL `https://grafana.com/api/dashboards/21962/revisions/1/download`.
  - Pri uvozu izberi `Prometheus` datasource (ali ga preslikaj na `Prometheus`, če ima drugačno ime).
  - Dashboard 21962 uporablja spremenljivko `Job`; če so splošni paneli `N/A`, preveri, da je izbran `Job=snmp`.
  - Če Grafana pokaže `Datasource ${DS_PROMETHEUS} was not found`, pomeni, da je dashboard ostal z nepreslikanim placeholderjem. V Settings/Import ali pri uvozu preslikaj `${DS_PROMETHEUS}` na dejanski datasource, npr. `Prometheus`.
  - Končno stanje: datasource je preslikan na `Prometheus` in metrike zdaj delajo.
  - Če `DS_PROMETHEUS` ni v `Variables`, ampak je v JSON modelu, popravi dashboard JSON. Poišči `"datasource": "${DS_PROMETHEUS}"` in ga zamenjaj z dejanskim datasource imenom ali UID-jem, npr. `Prometheus`.
  - Končni fix v Grafani: v `Variables > Job` sem izbral datasource, kar je samodejno posodobilo JSON model in odpravilo napako.
  - Kaj pomeni `Job`: v Prometheusu je `job` label ime scrape naloge, torej logična skupina metrik, ki jih Prometheus pobira iz istega vira. Pri nas je to SNMP scrape job iz `prometheus.yml`, zato dashboard uporablja `job="snmp"`.
  - Zakaj `job=snmp`: v našem `prometheus.yml` je job definiran kot `snmp`, zato morajo dashboard poizvedbe iskati metrike z istim labelom. Če bi bil job imenovan drugače, bi bilo treba v dashboardu izbrati to drugo ime.

- Hitri CLI/HTTP (opcijsko): uporabi Grafana HTTP API za avtomatiziran uvoz, če želiš neinteraktivno namestitev (zahteva API ključ).

- Nasvet: če grafi ne prikazujejo vrednosti, preveri najprej v Prometheus UI (`http://<prometheus_host>:9090/targets`) da je cilj v statusu UP in da Grafana uporablja pravilen datasource URL.
- Nasvet: če throughput deluje, ampak povzetek prikazuje `N/A`, je najpogosteje kriva napačno nastavljena spremenljivka `Job` v dashboardu ali neujemanje med imenom Prometheus joba in poizvedbami na dashboardu.

