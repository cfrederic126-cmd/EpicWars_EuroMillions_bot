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

ANNONCE_
