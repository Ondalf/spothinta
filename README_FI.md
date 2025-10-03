# [Spot-hinta](https://spot-hinta.fi) API integraatio Home Assistantiin

HOX: Tää on osakseen "AI slop".

#### Integraatio palauttaa hetkellisen `current_price` arvon. Sensori päivittää itsensä kerran varttiin huolimatta siitä, käytitkö tunnin vai vartin tarkkuutta sensorin teon yhteydessä.

---

#### Ensalkuun iso käsi, eli kiitos tohon suuntaan: https://spot-hinta.fi/

### Idea(t) mitä lähdin hakemaan
- **Tee vain yks juttu, mut tee se hyvin:** hetkellinen hinta sensoridatana
- **Kevyt:** Home Assistant ei tykkää isoista datamääristä, joten tämä tallentaa vain hetkellisen hinnan
- **Vältä turhia API kutsuja:** vain yksi kutsu per sensori lähtee APIa kohti per päivä
- [custom_components/nordpool](https://github.com/custom-components/nordpool) ei tykännyt varttihinnottelusta, koska tallennettava datamäärä oli yli 16kb/pvä ja halusin kuitenkin piirtää käyrän
- Kokeilla pythonia AI avusteisesti: wanhan kansan C/C++ koodaajana, en kokeile toista kertaa.

### Mikä toimii?
- Integraation lisääminen "hub"ina Home Assistantiin
- Sensorin lisääminen "hub"iin WebUI kautta (kyselee alueet, 15/60min ja verollinen/veroton)
  - Sensorit saa nimen "Spot Price {alue} [VAT,NO_VAT]" pohjaa käyttäen
  - Entity ID seuraa tätä nimeämiskäytäntöä, esim. `sensor.spot_price_se4_vat`
- Käytä paikallista kakkua, ellei
  - Kakku ole tyhjä (käynnistyksen yhteydessä)
  - Seuraavan päivän arvot ole saatavilla (14:30 eteenpäin)
- Arvot ovat EUR/kWh kiinteästi, koska tulevat sellaisena APIsta
- Kaikki timestampit ovat UTC:na, jotta ehkä välttäisi sekaannukset aikavyöhykkeiden kanssa
  - Kun arvot haetaan API:sta, ne pyritään kääntämään oikealle aikavyöhykkeille
- Tämän integraation pitäisi olla HACS yhteensopiva, mutten pysty testaamaan

### Esimerkki state data mitä tältä saa
```YAML
state_class: measurement
region: FI
current_price: 0.00365
min_price: 0.00251
max_price: 0.07656
raw_data_entries: 96
unit_of_measurement: EUR/kWh
device_class: monetary
icon: mdi:flash
friendly_name: Spot Price FI VAT
```

### Nämä ovat hyvin mahdollisesti rikki ja voi estää käynnistymisen
- Jos tämä plugari käynnistyessä jää käynnistymättä DNS virheen tjsp takia, se ei käynnisty ja disabloi ittensä
  - Ja aika varmasti sama tapahtuu myös, jos päivittäinen API kutsu antaa virheen

### TODO, ja muita suunnittelukikkareita, jotka eivät ole varsinaisia vikoja, jotka estäisi käynnistyksen
- Outouksia min/max laskussa
  - Arvoihin käytetään koko datasettiä
  - Arvot luetaan vain verollisista hinnoista
- En ole varmaa, osaako kakku tyhjätä itsensä
  - Pitänee varmaan kehittää tapa, jolla tyhjätä wanhat arvot pois
  - Kun huomisen hinnat tuli kakkuun, kakun koko tuplaantui (96 -> 192 arvoa)
- Data race kakun kanssa käynnistyksen yhteydessä
  - Tekee erilliset kutsut, jos valittuna sekä verollinen että veroton samalta alueelta
    - Yksi pitäisi riittää, koska kuitenkin kakutettu data sisältää molemmat, verollisen ja verottoman arvon
  - Luultavasti tapahtuu myös, kun päivittäinen API kutsu lähtee
- En pysty testaan, toimiiko aikavyöhykemuunnokset oikein koneella, joka ei käytä UTC aikavyöhykettä
  - Paiskaa viestiä, avaa issue tai PR jos huomaat jotain tähän suuntaan olevaa!
- Ei tarkistuksia, onko päivittäisessä API kutsussa huomisen data mukana
  - Ei myöskään pakkohakua, jos data puuttuu. Käyttää viimeisintä arvoa, kunnes kokeilee uudestaan seuraavana päivänä 14:30 jälkeen
  - Olisi hyvä olla nappi tai jokin, jolla pakottaa datan päivitys esim WebUI kautta
    - Itse funktio tukee pakkohakua jo valmiiksi
- Ne aikavyöhykemuunnokset...

Löytyy myös logger entryt, eli saat logeihin tekstiä, mitä tapahtuu, jos lisäät nämä configuration.yaml. Yritin parhaani mukaan selostaa myös koodissa itsessään, mitä tapahtuu ja miten.
```yaml
logger:
  logs:
    custom_components.spothinta: debug
    custom_components.spothinta.sensor: debug
    custom_components.spothinta.spothinta_api: debug
```

Jos käytät Home Assistant (Core) tai haluat käsin asentaa tämän, kopioi `custom_components/spothinta` sisältö tänhetkiseen asennukseesi esim. näin:
```bash
cd
git clone https://github.com/Ondalf/spothinta
mkdir -p ~/.homeassistant/custom_components/spothinta
cp spothinta/custom_components/spothinta/* ~/.homeassistant/custom_components/spothinta/
service homeassistant stop && service homeassistant start
```
Testattu ja kirjotettu HACore 2025.9.4 joka ajetaan Debian 13 LXC-kontissa ProxmoxVE 9 x86_64 sisällä (joka jostain syystä käytti UTC:a Europe/Helsinki aikavyöhykkeen sijaan). Sinun setuppisi on aika varmasti erilainen, joten muokkaa noi polut ja käynnistys/sammutus komennot tarpeen mukaan.