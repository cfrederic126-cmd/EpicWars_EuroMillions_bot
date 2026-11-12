#!/usr/bin/env python3
"""Bot Telegram EuroMillions — EpicWars Studio"""

import csv
import io
import json
import os
import random
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

URL_HISTORIQUE = "https://www.mes-resultats-fdj.fr/api/telecharger/euromillions"
FICHIER_ETAT = Path(__file__).parent / "signal_precedent.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

N_MAX, N_TIRES = 50, 5
E_MAX, E_TIRES = 12, 2

MOIS_FR = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
           "aout", "septembre", "octobre", "novembre", "decembre"]

ANNONCE_SECOURS = {
    1: 49, 2: 19, 3: 28, 4: 30, 5: 48, 6: 10, 7: 17, 8: 25, 9: 24, 10: 44,
    11: 44, 12: 42, 13: 19, 14: 19, 15: 41, 16: 21, 17: 27, 18: 29, 19: 24,
    20: 21, 21: 15, 22: 20, 23: 5, 24: 10, 25: 39, 26: 19, 27: 30, 28: 13,
    29: 6, 30: 31, 31: 13, 32: 7, 33: 18, 34: 35, 35: 18, 36: 29, 37: 42,
    38: 44, 39: 27, 40: 29, 41: 7, 42: 35, 43: 26, 44: 45, 45: 16, 46: 17,
    47: 3, 48: 26, 49: 8, 50: 44,
}

ANNONCE_ETOILES_SECOURS = {
    1: 2, 2: 11, 3: 7, 4: 2, 5: 2, 6: 2,
    7: 6, 8: 1, 9: 3, 10: 6, 11: 9, 12: 2,
}

AFFINITE_SECOURS = {
    1: 48, 2: 19, 3: 50, 4: 23, 5: 25, 6: 9, 7: 34, 8: 5, 9: 6, 10: 45,
    11: 13, 12: 44, 13: 11, 14: 4, 15: 28, 16: 18, 17: 35, 18: 16, 19: 37,
    20: 45, 21: 14, 22: 10, 23: 4, 24: 23, 25: 5, 26: 24, 27: 39, 28: 15,
    29: 11, 30: 23, 31: 5, 32: 23, 33: 12, 34: 7, 35: 17, 36: 42, 37: 23,
    38: 30, 39: 44, 40: 43, 41: 25, 42: 13, 43: 3, 44: 39, 45: 10, 46: 27,
    47: 29, 48: 1, 49: 26, 50: 44,
}


def env(*noms):
    for n in noms:
        v = os.getenv(n)
        if v:
            return v.strip()
    return None


TOKEN = env("TELEGRAM_TOKEN", "BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
CHAT_ID = env("TELEGRAM_CHAT_ID", "CHANNEL_ID", "CHAT_ID")


def charger_historique():
    req = urllib.request.Request(URL_HISTORIQUE, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        brut = r.read().decode("utf-8")

    tirages = []
    for row in csv.DictReader(io.StringIO(brut), delimiter=";"):
        try:
            nums = {int(row[f"boule_{i}"]) for i in range(1, 6)}
            etoiles = {int(row[f"etoile_{i}"]) for i in range(1, 3)}
        except (KeyError, ValueError, TypeError):
            continue
        if len(nums) != N_TIRES or len(etoiles) != E_TIRES:
            continue
        tirages.append({"date": row["date"], "nums": nums, "etoiles": etoiles})

    tirages.reverse()
    if len(tirages) < 100:
        raise RuntimeError(f"Historique trop court : {len(tirages)} tirages")
    return tirages


def matrice_affinite(tirages):
    m = defaultdict(Counter)
    for t in tirages:
        for x in t["nums"]:
            for y in t["nums"]:
                if x != y:
                    m[x][y] += 1
    return m


def matrice_annonciateur(tirages, cle="nums"):
    m = defaultdict(Counter)
    for prec, suiv in zip(tirages, tirages[1:]):
        for x in prec[cle]:
            for y in suiv[cle]:
                m[x][y] += 1
    return m


def frequences_recentes(tirages, n=36):
    fn, fe = Counter(), Counter()
    for t in tirages[-n:]:
        fn.update(t["nums"])
        fe.update(t["etoiles"])
    return fn, fe


def score_popularite(num, freq_recente):
    s = 0.0
    if num <= 31:
        s += 40
    if num <= 12:
        s += 25
    if num == 7:
        s += 20
    s += freq_recente.get(num, 0) * 6
    return s


def score_annonce(num, derniers_nums, annonce):
    total = sum(annonce[x].get(num, 0) for x in derniers_nums)
    attendu = len(derniers_nums) * (N_TIRES / N_MAX) * 100
    return total / attendu if attendu else 0.0


def meilleure_affinite(num, affinite):
    c = affinite.get(num)
    if c:
        return max(c, key=lambda y: (c[y], -y))
    return AFFINITE_SECOURS.get(num)


def annonces_du_tirage(derniers, annonce):
    res = {}
    for x in sorted(derniers):
        compte = annonce.get(x)
        if compte:
            res[x] = max(compte, key=lambda y: (compte[y], -y))
        else:
            res[x] = ANNONCE_SECOURS.get(x)
    return res


def construire_grille(tirages, affinite, annonce, freq_n, freq_e, graine):
    rng = random.Random(graine)
    derniers = tirages[-1]["nums"]

    scores = {}
    for n in range(1, N_MAX + 1):
        a = score_annonce(n, derniers, annonce)
        p = score_popularite(n, freq_n)
        scores[n] = a * 100 - p

    annonces = set(v for v in annonces_du_tirage(derniers, annonce).values() if v)
    for n in annonces:
        scores[n] += 120

    for n in annonces:
        partenaire = meilleure_affinite(n, affinite)
        if partenaire and partenaire not in annonces:
            scores[partenaire] += 50

    vivier = sorted(scores, key=scores.get, reverse=True)[:18]
    poids = [max(scores[n] - scores[vivier[-1]] + 1, 1) for n in vivier]

    meilleure, meilleur_score = None, -1e9
    for _ in range(4000):
        grille = set()
        v, w = list(vivier), list(poids)
        while len(grille) < N_TIRES and v:
            choix = rng.choices(v, weights=w, k=1)[0]
            i = v.index(choix)
            v.pop(i)
            w.pop(i)
            grille.add(choix)
        if len(grille) != N_TIRES:
            continue

        g = sorted(grille)
        if not 95 <= sum(g) <= 160:
            continue
        if sum(1 for x in g if x % 2 == 0) not in (2, 3):
            continue
        if any(g[i] == g[i - 1] + 1 for i in range(1, N_TIRES)):
            continue
        if sum(1 for x in g if x >= 32) < 2:
            continue

        aff = sum(affinite[x].get(y, 0) for x in g for y in g if x < y)
        s = sum(scores[x] for x in g) + aff * 0.3
        if s > meilleur_score:
            meilleur_score, meilleure = s, g

    if meilleure is None:
        meilleure = sorted(rng.sample(vivier, N_TIRES))

    return meilleure, derniers


def construire_etoiles(tirages, annonce_e, freq_e, graine):
    rng = random.Random(graine + 7)
    dernieres = tirages[-1]["etoiles"]

    scores = {}
    for e in range(1, E_MAX + 1):
        total = sum(annonce_e[x].get(e, 0) for x in dernieres)
        attendu = len(dernieres) * (E_TIRES / E_MAX) * 100
        scores[e] = (total / attendu if attendu else 0) * 100
        scores[e] -= freq_e.get(e, 0) * 4

    for x in dernieres:
        c = annonce_e.get(x)
        if c:
            scores[max(c, key=lambda y: (c[y], -y))] += 60

    vivier = sorted(scores, key=scores.get, reverse=True)[:5]
    poids = [max(scores[e] - scores[vivier[-1]] + 1, 1) for e in vivier]
    choix = set()
    while len(choix) < E_TIRES and vivier:
        e = rng.choices(vivier, weights=poids, k=1)[0]
        i = vivier.index(e)
        vivier.pop(i)
        poids.pop(i)
        choix.add(e)
    return sorted(choix)


def annonces_etoiles(dernieres, annonce_e):
    res = {}
    for x in sorted(dernieres):
        c = annonce_e.get(x)
        if c:
            res[x] = max(c, key=lambda y: (c[y], -y))
        else:
            res[x] = ANNONCE_ETOILES_SECOURS.get(x)
    return {k: v for k, v in res.items() if v}


def lire_etat():
    if FICHIER_ETAT.exists():
        try:
            return json.loads(FICHIER_ETAT.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def ecrire_etat(nums, etoiles, date_tirage):
    FICHIER_ETAT.write_text(json.dumps({
        "nums": nums, "etoiles": etoiles,
        "pour_tirage_apres": date_tirage,
        "genere_le": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def bilan(etat, dernier):
    if not etat:
        return None
    return {
        "signal": etat["nums"], "etoiles_signal": etat["etoiles"],
        "bons": sorted(set(etat["nums"]) & dernier["nums"]),
        "bonnes_etoiles": sorted(set(etat["etoiles"]) & dernier["etoiles"]),
    }


def fmt(nums):
    return " · ".join(f"{n:02d}" for n in nums)


def construire_message(grille, etoiles, dernier, b, annonce, annonce_e, affinite):
    d = datetime.now()
    lignes = [
        "🎰 <b>SIGNAL EUROMILLIONS</b>",
        f"<i>{d.day} {MOIS_FR[d.month-1]} {d.year}</i>",
        "",
        "📊 <b>Tirage précédent</b>",
        f"<code>{fmt(sorted(dernier['nums']))}</code>  ⭐ "
        f"<code>{fmt(sorted(dernier['etoiles']))}</code>",
        f"<i>{dernier['date']}</i>",
    ]

    if b:
        n_ok, e_ok = len(b["bons"]), len(b["bonnes_etoiles"])
        lignes += ["", "🎯 <b>Bilan de notre signal précédent</b>",
                   f"<code>{fmt(sorted(b['signal']))}</code>  ⭐ "
                   f"<code>{fmt(sorted(b['etoiles_signal']))}</code>"]
        if n_ok or e_ok:
            detail = []
            if b["bons"]:
                detail.append(f"numéros : {fmt(b['bons'])}")
            if b["bonnes_etoiles"]:
                detail.append(f"étoiles : {fmt(b['bonnes_etoiles'])}")
            lignes.append(f"✅ <b>{n_ok} bon(s) numéro(s)</b>"
                          + (f" — {', '.join(detail)}" if detail else ""))
        else:
            lignes.append("❌ Aucune correspondance sur ce tirage")

    paires = annonces_du_tirage(dernier["nums"], annonce)
    paires_e = annonces_etoiles(dernier["etoiles"], annonce_e)

    lignes += [
        "", "🔮 <b>SIGNAL DU JOUR</b>",
        f"<code>{fmt(grille)}</code>",
        f"⭐ <code>{fmt(etoiles)}</code>",
        "",
        "🔗 <b>Chaîne d'annonce</b>",
        "   " + "\n   ".join(
            f"{x:02d} ➜ {y:02d}" + (f"  (affinité {a:02d})" if a else "")
            for x, y, a in (
                (x, y, meilleure_affinite(y, affinite) if y else None)
                for x, y in sorted(paires.items()) if y)),
        "   ⭐ " + " · ".join(f"{x:02d} ➜ {y:02d}"
                             for x, y in sorted(paires_e.items())),
        "",
        "<i>EuroMillions est un jeu de hasard : chaque combinaison a "
        "exactement la même probabilité. Ce signal est proposé pour le "
        "plaisir du jeu, sans garantie de gain.</i>",
        "<i>Interdit aux mineurs. Jouer comporte des risques — "
        "09 74 75 13 13 (appel non surtaxé).</i>",
    ]
    return "\n".join(lignes)


def envoyer(texte):
    if not TOKEN or not CHAT_ID:
        print("⚠️  Secrets Telegram absents — message non envoyé.\n")
        print(texte)
        return False
    data = json.dumps({
        "chat_id": CHAT_ID, "text": texte,
        "parse_mode": "HTML", "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        rep = json.loads(r.read())
    if not rep.get("ok"):
        raise RuntimeError(f"Telegram : {rep}")
    print("✅ Message envoyé.")
    return True


def main():
    print("→ Téléchargement de l'historique…")
    tirages = charger_historique()
    dernier = tirages[-1]
    print(f"  {len(tirages)} tirages, dernier le {dernier['date']}")

    affinite = matrice_affinite(tirages)
    annonce = matrice_annonciateur(tirages, "nums")
    annonce_e = matrice_annonciateur(tirages, "etoiles")
    freq_n, freq_e = frequences_recentes(tirages)

    etat = lire_etat()
    b = bilan(etat, dernier) if etat else None

    graine = int(datetime.now().strftime("%Y%m%d")) + len(tirages)
    grille, _ = construire_grille(
        tirages, affinite, annonce, freq_n, freq_e, graine)
    etoiles = construire_etoiles(tirages, annonce_e, freq_e, graine)
    print(f"  Grille : {grille}  étoiles : {etoiles}")

    msg = construire_message(grille, etoiles, dernier, b, annonce, annonce_e, affinite)
    envoyer(msg)
    ecrire_etat(grille, etoiles, dernier["date"])
    print("→ État sauvegardé.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Erreur : {e}", file=sys.stderr)
        sys.exit(1)
