#!/usr/bin/env python3
"""Henter villaer til salg i Svenstrup/Godthåb (9230) og Støvring (9530)
fra Boligsiden og Boliga, samler dem og gemmer i docs/data/huse.json.

Kører i GitHub Actions hver morgen. Kun Python-standardbiblioteket bruges.
Husker hvornår hvert hus blev set første gang (så siden kan vise "Ny"),
prisfald, og markerer huse der er forsvundet (solgt/trukket).
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

# 9230 Svenstrup/Godthåb/Ellidshøj, 9530 Støvring + nabopostnumre, så afstandsskyderen
# på siden kan "rykke radius" lidt ud. Selve afstandsfilteret sker på siden.
POSTNUMRE = ["9230", "9530", "9541", "9520", "9240", "9200", "9210", "9260", "9000"]
MAKS_PRIS = 5_000_000          # henter lidt bredt; jeres eget filter (4 mio.) sker på siden
DATAFIL = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "huse.json")
UA = {"User-Agent": "Mozilla/5.0 (husjagt; privat boligoverblik)",
      "Accept": "application/json"}
I_DAG = date.today().isoformat()


def hent_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def tal(v):
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except (TypeError, ValueError):
        return None


def adresse_noegle(vej, nr, postnr):
    s = f"{vej or ''} {nr or ''}".lower().replace(".", "").replace(",", "")
    return " ".join(s.split()) + f"|{postnr}"


# ---------- Boligsiden ----------
def billede_boligsiden(c):
    for kilde in [c.get("defaultImage")] + list(c.get("images") or []):
        if not kilde:
            continue
        srcs = kilde.get("imageSources") or []
        if srcs:
            srcs = sorted(srcs, key=lambda s: (s.get("size") or {}).get("width", 0))
            mellem = [s for s in srcs if (s.get("size") or {}).get("width", 0) >= 400]
            return (mellem or srcs)[0].get("url") if (mellem or srcs) else None
        if kilde.get("url"):
            return kilde["url"]
    return None


def hent_boligsiden():
    huse = []
    for side in range(1, 11):
        q = [("addressTypes", "villa"), ("priceMax", MAKS_PRIS), ("per_page", 100), ("page", side)]
        q += [("zipCodes", p) for p in POSTNUMRE]   # skal gentages, ikke kommasepareres
        data = hent_json("https://api.boligsiden.dk/search/cases?" + urllib.parse.urlencode(q))
        cases = data.get("cases") or []
        for c in cases:
            a = c.get("address") or {}
            postnr = str(a.get("zipCode") or c.get("zipCode") or "")
            vej = a.get("roadName") or ""
            nr = a.get("houseNumber") or ""
            url = ("https://www.boligsiden.dk/adresse/" + a["slug"]) if a.get("slug") else (c.get("caseUrl") or "")
            # BBR-data: hovedbygningen er den med størst boligareal
            bygn = [b for b in (a.get("buildings") or []) if b.get("housingArea")]
            hoved = max(bygn, key=lambda b: b["housingArea"]) if bygn else {}
            huse.append({
                "kilde": "Boligsiden",
                "type": "villa",
                "id": f"bs-{c.get('caseID')}",
                "noegle": adresse_noegle(vej, nr, postnr),
                "adresse": f"{vej} {nr}".strip(),
                "postnr": postnr,
                "by": a.get("cityName") or ((a.get("city") or {}).get("name") if isinstance(a.get("city"), dict) else a.get("city")),
                "pris": tal(c.get("priceCash")),
                "kvm": tal(c.get("housingArea")) or tal(a.get("livingArea")) or tal(hoved.get("housingArea")),
                "grund": tal(c.get("lotArea")),
                "vaerelser": tal(c.get("numberOfRooms")) or tal(hoved.get("numberOfRooms")),
                "bad": tal(c.get("numberOfBathrooms")) if c.get("numberOfBathrooms") is not None else tal(hoved.get("numberOfBathrooms")),
                "toiletter": tal(c.get("numberOfToilets")) if c.get("numberOfToilets") is not None else tal(hoved.get("numberOfToilets")),
                "byggeaar": tal(c.get("yearBuilt")) or tal(hoved.get("yearBuilt")),
                "energi": (c.get("energyLabel") or "").upper() or None,
                "dage": tal(c.get("daysOnMarket")) if not isinstance(c.get("daysOnMarket"), dict) else None,
                "billede": billede_boligsiden(c),
                "url": url,
                "lat": (c.get("coordinates") or {}).get("lat"),
                "lon": (c.get("coordinates") or {}).get("lon"),
            })
        total = data.get("totalHits") or 0
        if not cases or side * 100 >= total:
            break
        time.sleep(1)
    return huse


# ---------- Boliga ----------
def hent_boliga():
    huse = []
    for side in range(1, 11):
        q = {
            "zipCodes": ",".join(POSTNUMRE),
            "propertyType": 1,      # 1 = villa
            "priceMax": MAKS_PRIS,
            "pageSize": 50,
            "page": side,
        }
        data = hent_json("https://api.boliga.dk/api/v2/search/results?" + urllib.parse.urlencode(q))
        res = data.get("results") or []
        for r in res:
            postnr = str(r.get("zipCode") or "")
            gade = (r.get("street") or "").strip()
            dele = gade.rsplit(" ", 1)
            vej, nr = (dele[0], dele[1]) if len(dele) == 2 and any(ch.isdigit() for ch in dele[1]) else (gade, "")
            billeder = r.get("images") or []
            huse.append({
                "kilde": "Boliga",
                "type": "villa",
                "id": f"bl-{r.get('id')}",
                "noegle": adresse_noegle(vej, nr, postnr),
                "adresse": gade,
                "postnr": postnr,
                "by": r.get("city"),
                "pris": tal(r.get("price")),
                "kvm": tal(r.get("size")),
                "grund": tal(r.get("lotSize")),
                "vaerelser": tal(r.get("rooms")),
                "bad": None,
                "toiletter": None,
                "byggeaar": tal(r.get("buildYear")),
                "energi": (r.get("energyClass") or "").upper() or None,
                "dage": tal(r.get("daysForSale")),
                "billede": billeder[0].get("url") if billeder else None,
                "url": f"https://www.boliga.dk/bolig/{r.get('id')}",
                "lat": r.get("latitude"),
                "lon": r.get("longitude"),
            })
        meta = data.get("meta") or {}
        if not res or side >= (meta.get("totalPages") or meta.get("pageCount") or 1):
            break
        time.sleep(1)
    return huse


def flet(lister):
    """Samme adresse fra flere kilder bliver til ét hus; tomme felter udfyldes."""
    samlet = {}
    for h in [h for liste in lister for h in liste]:
        k = h["noegle"]
        if k not in samlet:
            h["links"] = [{"kilde": h["kilde"], "url": h["url"]}]
            samlet[k] = h
            continue
        eks = samlet[k]
        for felt, v in h.items():
            if eks.get(felt) in (None, "") and v not in (None, ""):
                eks[felt] = v
        eks["links"].append({"kilde": h["kilde"], "url": h["url"]})
    return samlet


def main():
    gammel = {"huse": {}}
    if os.path.exists(DATAFIL):
        with open(DATAFIL, encoding="utf-8") as f:
            gammel = json.load(f)
    gamle = gammel.get("huse", {})

    lister, fejl = [], []
    for navn, fn in [("Boligsiden", hent_boligsiden), ("Boliga", hent_boliga)]:
        try:
            l = fn()
            print(f"{navn}: {len(l)} villaer")
            lister.append(l)
        except Exception as e:  # én kilde må gerne fejle
            print(f"{navn} fejlede: {e}", file=sys.stderr)
            fejl.append(f"{navn}: {e}")
    if not lister:
        print("Ingen kilder svarede — beholder gamle data.", file=sys.stderr)
        sys.exit(1)

    nye = flet(lister)
    resultat = {}
    for k, h in nye.items():
        g = gamle.get(k, {})
        h["foerstSet"] = g.get("foerstSet", I_DAG)
        h["sidstSet"] = I_DAG
        h["aktiv"] = True
        hist = g.get("prishistorik", [])
        if h.get("pris") and (not hist or hist[-1]["pris"] != h["pris"]):
            hist.append({"dato": I_DAG, "pris": h["pris"]})
        h["prishistorik"] = hist
        h.pop("noegle", None)
        resultat[k] = h
    # huse der ikke længere er til salg beholdes i 60 dage som "væk"
    for k, g in gamle.items():
        if k in resultat:
            continue
        g["aktiv"] = False
        g.setdefault("vaekSiden", I_DAG)
        if (date.fromisoformat(I_DAG) - date.fromisoformat(g["vaekSiden"])).days <= 60:
            resultat[k] = g

    os.makedirs(os.path.dirname(DATAFIL), exist_ok=True)
    with open(DATAFIL, "w", encoding="utf-8") as f:
        json.dump({"opdateret": I_DAG, "fejl": fejl, "huse": resultat},
                  f, ensure_ascii=False, indent=1)
    print(f"Gemt {len(resultat)} huse ({sum(1 for h in resultat.values() if h['aktiv'])} aktive).")


if __name__ == "__main__":
    main()
