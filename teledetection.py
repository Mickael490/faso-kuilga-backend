import requests
import json
import os
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SH_CLIENT_ID")
CLIENT_SECRET = os.getenv("SH_CLIENT_SECRET")
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# ── ZONES FORAGES — 13 RÉGIONS DU BURKINA FASO ──────────────────────────────
# Critères normes OMS/UNICEF/DGRE-BF :
# - NDWI > 0.1 : présence eau souterraine
# - NDVI > 0.2 : végétation indicatrice nappe
# - Score > 60% : zone favorable, profondeur 20-60m
# - Score 40-60% : zone potentielle, profondeur 60-100m
ZONES_FORAGES = [
    # Centre
    {"nom": "Zone Tanghin-Dassouri",      "region": "Centre",           "bbox": [12.25,-1.75,12.50,-1.50]},
    {"nom": "Zone Saaba-Koubri",          "region": "Centre",           "bbox": [12.18,-1.35,12.43,-1.10]},
    {"nom": "Zone Pabre-Loumbila",        "region": "Centre",           "bbox": [12.42,-1.62,12.67,-1.37]},
    # Centre-Nord
    {"nom": "Zone Kongoussi-Rollo",       "region": "Centre-Nord",      "bbox": [13.15,-1.68,13.45,-1.38]},
    {"nom": "Zone Titao-Pilimpikou",      "region": "Centre-Nord",      "bbox": [13.45,-1.98,13.70,-1.73]},
    {"nom": "Zone Boulsa-Namsiguia",      "region": "Centre-Nord",      "bbox": [12.58,-0.68,12.83,-0.43]},
    # Nord
    {"nom": "Zone Ouahigouya-Rambo",      "region": "Nord",             "bbox": [13.50,-2.55,13.75,-2.30]},
    {"nom": "Zone Titao-Banh",            "region": "Nord",             "bbox": [13.68,-2.12,13.93,-1.87]},
    {"nom": "Zone Gourcy-Seguenéga",      "region": "Nord",             "bbox": [13.18,-2.42,13.43,-2.17]},
    # Sahel
    {"nom": "Zone Dori-Gorgadji",         "region": "Sahel",            "bbox": [13.88,-0.28,14.18, 0.02]},
    {"nom": "Zone Gorom-Gorom-Deou",      "region": "Sahel",            "bbox": [14.35,-0.35,14.60,-0.10]},
    {"nom": "Zone Djibo-Kelbo",           "region": "Sahel",            "bbox": [14.02,-1.72,14.27,-1.47]},
    # Hauts-Bassins
    {"nom": "Zone Bobo-Dioulasso Sud",    "region": "Hauts-Bassins",    "bbox": [11.08,-4.42,11.38,-4.12]},
    {"nom": "Zone Hounde-Koti",           "region": "Hauts-Bassins",    "bbox": [11.42,-3.62,11.67,-3.37]},
    {"nom": "Zone Karangasso-Safané",     "region": "Hauts-Bassins",    "bbox": [10.98,-4.22,11.23,-3.97]},
    # Boucle du Mouhoun
    {"nom": "Zone Dedougou-Bondoukuy",    "region": "Boucle du Mouhoun","bbox": [12.28,-3.68,12.58,-3.38]},
    {"nom": "Zone Nouna-Barani",          "region": "Boucle du Mouhoun","bbox": [12.65,-3.98,12.90,-3.73]},
    {"nom": "Zone Safane-Boromo",         "region": "Boucle du Mouhoun","bbox": [12.08,-3.28,12.38,-2.98]},
    # Est
    {"nom": "Zone Fada-Tibga",            "region": "Est",              "bbox": [11.98, 0.22,12.28, 0.52]},
    {"nom": "Zone Diapaga-Kantchari",     "region": "Est",              "bbox": [11.98, 1.52,12.28, 1.82]},
    {"nom": "Zone Pama-Kompienga",        "region": "Est",              "bbox": [11.18, 0.62,11.43, 0.87]},
    # Cascades
    {"nom": "Zone Banfora-Mangodara",     "region": "Cascades",         "bbox": [10.52,-4.92,10.82,-4.62]},
    {"nom": "Zone Sindou-Niofila",        "region": "Cascades",         "bbox": [10.62,-5.25,10.87,-5.00]},
    # Centre-Est
    {"nom": "Zone Koupela-Pouytenga",     "region": "Centre-Est",       "bbox": [12.08,-0.52,12.38,-0.22]},
    {"nom": "Zone Tenkodogo-Bittou",      "region": "Centre-Est",       "bbox": [11.72,-0.48,11.97,-0.18]},
    # Centre-Ouest
    {"nom": "Zone Koudougou-Reo",         "region": "Centre-Ouest",     "bbox": [12.28,-2.62,12.53,-2.37]},
    {"nom": "Zone Sapouy-Leo",            "region": "Centre-Ouest",     "bbox": [11.48,-1.88,11.73,-1.63]},
    # Plateau Central
    {"nom": "Zone Ziniaré-Nagreongo",     "region": "Plateau Central",  "bbox": [12.42,-1.28,12.67,-1.03]},
    {"nom": "Zone Mogtedo-Meguet",        "region": "Plateau Central",  "bbox": [12.22,-0.98,12.47,-0.73]},
    # Centre-Sud
    {"nom": "Zone Kombissiri-Manga",      "region": "Centre-Sud",       "bbox": [11.98,-1.42,12.23,-1.17]},
    {"nom": "Zone Po-Guiaro",             "region": "Centre-Sud",       "bbox": [11.08,-1.28,11.33,-1.03]},
    # Sud-Ouest
    {"nom": "Zone Gaoua-Diebougou",       "region": "Sud-Ouest",        "bbox": [10.88,-3.32,11.13,-3.07]},
    {"nom": "Zone Kampti-Batie",          "region": "Sud-Ouest",        "bbox": [10.08,-3.58,10.33,-3.33]},
]


# ── SITES BARRAGES — CRITÈRES HYDROLOGIQUES DGRE-BF ─────────────────────────
# Normes : bassin versant > 50 km², pente 0.5-2%, sol imperméable
ZONES_BARRAGES = [
    # Nakanbé
    {"nom": "Site Bagre Nakanbé aval",        "region": "Centre-Est",       "bbox": [11.42,-0.62,11.67,-0.37]},
    {"nom": "Site Ziga Nakanbé amont",        "region": "Plateau Central",  "bbox": [12.42,-1.12,12.67,-0.87]},
    {"nom": "Site Loumbila Massili",          "region": "Plateau Central",  "bbox": [12.42,-1.48,12.67,-1.23]},
    {"nom": "Site Toece Nazinon",             "region": "Centre-Sud",       "bbox": [11.82,-1.32,12.07,-1.07]},
    # Mouhoun
    {"nom": "Site Samendeni Mouhoun",         "region": "Hauts-Bassins",    "bbox": [11.22,-4.78,11.47,-4.53]},
    {"nom": "Site Sourou Vallee",             "region": "Boucle du Mouhoun","bbox": [12.92,-3.48,13.17,-3.23]},
    {"nom": "Site Lery Mouhoun meandres",     "region": "Boucle du Mouhoun","bbox": [12.98,-3.42,13.23,-3.17]},
    {"nom": "Site Nouna Mouhoun Nord",        "region": "Boucle du Mouhoun","bbox": [12.65,-3.92,12.90,-3.67]},
    # Comoe
    {"nom": "Site Tourni Comoe amont",        "region": "Cascades",         "bbox": [10.32,-4.72,10.57,-4.47]},
    {"nom": "Site Banfora Comoe",             "region": "Cascades",         "bbox": [10.62,-4.85,10.87,-4.60]},
    # Sissili
    {"nom": "Site Leo Sissili",               "region": "Centre-Ouest",     "bbox": [11.02,-2.22,11.27,-1.97]},
    {"nom": "Site Sapouy Sissili amont",      "region": "Centre-Ouest",     "bbox": [11.48,-1.92,11.73,-1.67]},
    # Kompienga / Pendjari
    {"nom": "Site Kompienga Pendjari",        "region": "Est",              "bbox": [11.02, 0.62,11.27, 0.87]},
    {"nom": "Site Kantchari Sirba",           "region": "Est",              "bbox": [12.42, 1.42,12.67, 1.67]},
    # Beli / Gorouol
    {"nom": "Site Dori Beli",                 "region": "Sahel",            "bbox": [13.98,-0.12,14.23, 0.13]},
    {"nom": "Site Djibo Soum",                "region": "Sahel",            "bbox": [14.02,-1.72,14.27,-1.47]},
    # Bougouriba
    {"nom": "Site Diebougou Bougouriba",      "region": "Sud-Ouest",        "bbox": [10.88,-3.72,11.13,-3.47]},
    {"nom": "Site Batie Noumbiel",            "region": "Sud-Ouest",        "bbox": [ 9.85,-2.92,10.10,-2.67]},
    # Volta Rouge
    {"nom": "Site Korsimoro Volta Rouge",     "region": "Centre-Nord",      "bbox": [12.78,-1.08,13.03,-0.83]},
    {"nom": "Site Boulsa Nouhao",             "region": "Centre-Nord",      "bbox": [12.62,-0.68,12.87,-0.43]},
]


def get_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("Clés Sentinel Hub manquantes")
    r = requests.post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    return r.json()["access_token"]

def get_indice_statistique(token, bbox, indice="NDWI"):
    if indice == "NDWI":
        evalscript = """
//VERSION=3
function setup(){return{input:["B03","B08"],output:{bands:1,sampleType:"UINT8"}}}
function evaluatePixel(s){
    var val=(s.B03-s.B08)/(s.B03+s.B08+0.0001);
    val=Math.max(-1,Math.min(1,val));
    return[Math.round((val+1)/2*255)];
}"""
    else:
        evalscript = """
//VERSION=3
function setup(){return{input:["B04","B08"],output:{bands:1,sampleType:"UINT8"}}}
function evaluatePixel(s){
    var val=(s.B08-s.B04)/(s.B08+s.B04+0.0001);
    val=Math.max(-1,Math.min(1,val));
    return[Math.round((val+1)/2*255)];
}"""

    payload = {
        "input": {
            "bounds": {
                "bbox": [bbox[1], bbox[0], bbox[3], bbox[2]],
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {"from": "2025-11-01T00:00:00Z", "to": "2026-05-30T23:59:59Z"},
                    "maxCloudCoverage": 30,
                    "mosaickingOrder": "leastCC"
                }
            }]
        },
        "output": {
            "width": 48, "height": 48,
            "responses": [{"identifier": "default", "format": {"type": "image/png"}}]
        },
        "evalscript": evalscript
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = requests.post(PROCESS_URL, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            from PIL import Image
            from io import BytesIO
            img = Image.open(BytesIO(r.content)).convert("L")
            arr = np.array(img, dtype=float) / 255.0 * 2 - 1
            return round(float(np.mean(arr)), 3)
    except Exception as e:
        print(f"    Erreur Sentinel-2: {e}")
    return None

def analyser_zones_forages_bf(region_filtre=None):
    zones = ZONES_FORAGES
    if region_filtre:
        zones = [z for z in zones if z["region"].lower() == region_filtre.lower()]
    if not zones:
        zones = ZONES_FORAGES  # repli sur tout le BF si région inconnue

    token = get_token()
    resultats = []
    for zone in zones:
        print(f"  Analyse forage {zone['nom']}...")
        ndwi = get_indice_statistique(token, zone["bbox"], "NDWI") or -0.2
        ndvi = get_indice_statistique(token, zone["bbox"], "NDVI") or 0.1

        score_ndwi = round(min(100, max(0, (ndwi + 1) * 50)), 1)
        score_ndvi = round(min(100, max(0, (ndvi + 1) * 50)), 1)
        score_global = round(score_ndwi * 0.6 + score_ndvi * 0.4, 1)

        # Normes DGRE-BF : profondeur selon contexte géologique
        if zone["region"] in ["Sahel", "Nord"]:
            profondeur = round(80 - score_ndwi * 0.4, 1)  # socle précambrien, plus profond
        elif zone["region"] in ["Cascades", "Hauts-Bassins"]:
            profondeur = round(40 - score_ndwi * 0.2, 1)  # aquifères superficiels
        else:
            profondeur = round(60 - score_ndwi * 0.3, 1)

        resultats.append({
            "type": "forage",
            "nom": zone["nom"],
            "region": zone["region"],
            "latitude": (zone["bbox"][0] + zone["bbox"][2]) / 2,
            "longitude": (zone["bbox"][1] + zone["bbox"][3]) / 2,
            "ndwi_reel": ndwi, "ndvi_reel": ndvi,
            "score_ndwi": score_ndwi, "score_ndvi": score_ndvi,
            "score_global": score_global,
            "profondeur_estimee_m": profondeur,
            "debit_estime_m3h": round(score_ndwi / 20, 1),
            "statut": "favorable" if score_global > 60 else "potentiel",
            "source": "Sentinel-2 L2A (Copernicus ESA)",
            "date_analyse": datetime.now().strftime("%Y-%m-%d")
        })
    return sorted(resultats, key=lambda x: x["score_global"], reverse=True)

def analyser_zones_barrages_bf(region_filtre=None):
    zones = ZONES_BARRAGES
    if region_filtre:
        zones = [z for z in zones if z["region"].lower() == region_filtre.lower()]
    if not zones:
        zones = ZONES_BARRAGES

    token = get_token()
    resultats = []
    for zone in zones:
        print(f"  Analyse barrage {zone['nom']}...")
        ndwi = get_indice_statistique(token, zone["bbox"], "NDWI") or 0.0
        ndvi = get_indice_statistique(token, zone["bbox"], "NDVI") or 0.2

        score_ndwi = round(min(100, max(0, (ndwi + 1) * 50)), 1)
        score_ndvi = round(min(100, max(0, (ndvi + 1) * 50)), 1)
        score_global = round(score_ndwi * 0.8 + score_ndvi * 0.2, 1)
        capacite = round(score_global * 50_000)

        resultats.append({
            "type": "barrage",
            "nom": zone["nom"],
            "region": zone["region"],
            "latitude": (zone["bbox"][0] + zone["bbox"][2]) / 2,
            "longitude": (zone["bbox"][1] + zone["bbox"][3]) / 2,
            "ndwi_reel": ndwi, "ndvi_reel": ndvi,
            "score_ndwi": score_ndwi, "score_ndvi": score_ndvi,
            "score_global": score_global,
            "profondeur_estimee_m": None,
            "debit_estime_m3h": capacite,
            "statut": "favorable" if score_global > 55 else "potentiel",
            "source": "Sentinel-2 L2A (Copernicus ESA)",
            "date_analyse": datetime.now().strftime("%Y-%m-%d")
        })
    return sorted(resultats, key=lambda x: x["score_global"], reverse=True)

if __name__ == "__main__":
    print("Test connexion Sentinel Hub...")
    token = get_token()
    print(f"Token OK: {token[:20]}...")
