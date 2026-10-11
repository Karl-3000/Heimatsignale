#!/usr/bin/env python3
"""Erzeugt gemeinden.csv (AGS, Name, Kreis, Land, Koordinate) fuer die places-Tabelle.

Quelle: https://github.com/aproeger/german-municipalities
        (Auszug aus dem DESTATIS-Gemeindeverzeichnis GV-ISys, Datei AuszugGV3QAktuell.xlsx,
        Satzart 60 = Gemeinden).

Eingaben (liegen als Kopie unter ./source/):
  * german_municipalities_42d2a1d_unstripped.csv
      `git show 42d2a1d:german_municipalities.csv` - erster Commit, amtliche Namen noch
      MIT Zusaetzen (", Stadt" usw.). Massgeblich fuer ARS, Namen, Koordinaten.
  * german_municipalities_aa8c081.csv
      Stand HEAD (aa8c081) - identische Datensaetze, zusaetzlich Spalte `type`
      (City / Municipality / Unincorporated area), abgeleitet aus dem Textkennzeichen.

Aufruf:  python3 convert.py [--out gemeinden.csv]
"""
import argparse
import csv
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_RAW = os.path.join(HERE, "source", "german_municipalities_42d2a1d_unstripped.csv")
SRC_HEAD = os.path.join(HERE, "source", "german_municipalities_aa8c081.csv")

HEADER = ["ags", "name", "district_ags", "district_name", "state_code", "lat", "lon"]

# Stadtstaaten: amtlicher Zusatz steht hier ohne Komma davor bzw. als Kreisname
CITY_STATES = {"02": "Hamburg", "11": "Berlin"}


def strip_suffix(name: str) -> str:
    """Entfernt amtliche Zusaetze nach dem ersten Komma (", Stadt", ", Hansestadt", ", M" ...).

    Im GV-ISys folgt nach dem ersten Komma ausschliesslich ein Titel/Statuszusatz
    (geprueft: alle vorkommenden Zusaetze sind Bezeichnungen wie Stadt, Markt (M),
    Flecken, Kreisstadt, Ostseebad, "Stadt der FernUniversitaet" ...). Unterscheidende
    Namensteile wie "(Oder)" oder "an der Weinstrasse" stehen nie hinter einem Komma.
    """
    return name.split(",", 1)[0].strip()


def ars_to_ags(ars: str) -> str:
    # ARS = Land(2) RB(1) Kreis(2) Verband(4) Gemeinde(3); AGS = ARS ohne Verband
    return ars[:5] + ars[9:12]


def build() -> pd.DataFrame:
    raw = pd.read_csv(SRC_RAW, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    head = pd.read_csv(SRC_HEAD, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    if list(raw["ars"]) != list(head["ars"]):
        sys.exit("ARS-Listen der beiden Quellstaende weichen ab")
    raw["type"] = head["type"].values
    raw["population"] = pd.to_numeric(raw["population"], errors="coerce").fillna(0).astype(int)

    # unbewohnte gemeindefreie Gebiete (als solche gekennzeichnet UND 0 Einwohner) entfernen
    drop = (raw["type"] == "Unincorporated area") & (raw["population"] == 0)
    df = raw[~drop].copy()

    df["ags"] = df["ars"].map(ars_to_ags)
    df["district_ags"] = df["ags"].str[:5]
    df["state_code"] = df["ags"].str[:2]
    df["name"] = df["name"].map(strip_suffix)
    df["district_name"] = df["district"].map(strip_suffix)
    for code, city in CITY_STATES.items():
        m = df["state_code"] == code
        df.loc[m, "district_name"] = city

    df["lat"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["lon"] = pd.to_numeric(df["longitude"], errors="coerce")
    missing = df[df["lat"].isna() | df["lon"].isna()]
    if len(missing):
        sys.exit("Gemeinden ohne Koordinate:\n" + missing[["ags", "name"]].to_string())

    df = df.sort_values("ags")
    if df["ags"].duplicated().any():
        sys.exit("doppelte AGS: " + ", ".join(df.loc[df["ags"].duplicated(), "ags"]))
    df["lat"] = df["lat"].map(lambda v: f"{v:.5f}")
    df["lon"] = df["lon"].map(lambda v: f"{v:.5f}")
    return df[HEADER], raw[drop]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "gemeinden.csv"))
    args = ap.parse_args()
    out, dropped = build()
    out.to_csv(args.out, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    print(f"{len(out)} Gemeinden geschrieben nach {args.out}; "
          f"{len(dropped)} unbewohnte gemeindefreie Gebiete ausgelassen")


if __name__ == "__main__":
    main()
