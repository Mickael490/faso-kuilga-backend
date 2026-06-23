from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from teledetection import analyser_zones_forages_bf, analyser_zones_barrages_bf

app = FastAPI(title="Faso Kuilga - SIG des Points d'Eau du Burkina Faso")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/api/login")
def login(data: dict, db: Session = Depends(get_db)):
    query = text("SELECT id, nom, email, role FROM utilisateurs WHERE email=:email AND mot_de_passe=:mot_de_passe AND actif=TRUE")
    row = db.execute(query, {"email": data.get("email"), "mot_de_passe": data.get("mot_de_passe")}).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    return {"id": row.id, "nom": row.nom, "email": row.email, "role": row.role}

@app.get("/api/points")
def get_points(db: Session = Depends(get_db)):
    query = text("""
        SELECT p.id, p.code, p.nom, p.type, p.etat,
               p.region, p.commune, p.latitude, p.longitude,
               p.pop_desservie, p.observations,
               f.profondeur_m, f.debit_m3h, f.type_pompe, f.qualite_eau,
               b.capacite_m3, b.superficie_ha, b.usage, b.remplissage
        FROM points_eau p
        LEFT JOIN forages f ON f.point_eau_id = p.id
        LEFT JOIN barrages b ON b.point_eau_id = p.id
        ORDER BY p.id
    """)
    return [dict(r._mapping) for r in db.execute(query).fetchall()]

@app.post("/api/points")
def add_point(data: dict, db: Session = Depends(get_db)):
    query = text("""
        INSERT INTO points_eau (code,nom,type,etat,region,commune,latitude,longitude,pop_desservie,observations)
        VALUES (:code,:nom,:type,:etat,:region,:commune,:latitude,:longitude,:pop_desservie,:observations)
        RETURNING id
    """)
    result = db.execute(query, data)
    db.commit()
    return {"id": result.fetchone()[0], "message": "Point ajoute"}

@app.put("/api/points/{point_id}")
def update_point(point_id: int, data: dict, db: Session = Depends(get_db)):
    fields = []
    params = {"id": point_id}
    for key in ["nom","type","etat","region","commune","latitude","longitude","pop_desservie","observations"]:
        if key in data:
            fields.append(f"{key}=:{key}")
            params[key] = data[key]
    if not fields:
        return {"message": "Rien a mettre a jour"}
    db.execute(text(f"UPDATE points_eau SET {','.join(fields)} WHERE id=:id"), params)
    db.commit()
    return {"message": "Point mis a jour"}

@app.delete("/api/points/{point_id}")
def delete_point(point_id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM points_eau WHERE id=:id"), {"id":point_id})
    db.commit()
    return {"message": "Point supprime"}

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    return [dict(r._mapping) for r in db.execute(text("SELECT type,etat,COUNT(*) as nb FROM points_eau GROUP BY type,etat ORDER BY type")).fetchall()]

@app.get("/api/utilisateurs")
def get_utilisateurs(db: Session = Depends(get_db)):
    return [dict(r._mapping) for r in db.execute(text("SELECT id,nom,email,role,actif FROM utilisateurs ORDER BY id")).fetchall()]

@app.post("/api/utilisateurs")
def add_utilisateur(data: dict, db: Session = Depends(get_db)):
    result = db.execute(text("INSERT INTO utilisateurs (nom,email,mot_de_passe,role) VALUES (:nom,:email,:mot_de_passe,:role) RETURNING id"), data)
    db.commit()
    return {"id": result.fetchone()[0], "message": "Utilisateur cree"}

@app.put("/api/utilisateurs/{user_id}")
def update_utilisateur(user_id: int, data: dict, db: Session = Depends(get_db)):
    fields = []
    params = {"id": user_id}
    if "nom" in data:
        fields.append("nom=:nom"); params["nom"] = data["nom"]
    if "email" in data:
        fields.append("email=:email"); params["email"] = data["email"]
    if "role" in data:
        fields.append("role=:role"); params["role"] = data["role"]
    if "actif" in data:
        fields.append("actif=:actif"); params["actif"] = data["actif"]
    if "mot_de_passe" in data and data["mot_de_passe"]:
        fields.append("mot_de_passe=:mot_de_passe"); params["mot_de_passe"] = data["mot_de_passe"]
    if not fields:
        return {"message": "Rien a mettre a jour"}
    db.execute(text(f"UPDATE utilisateurs SET {','.join(fields)} WHERE id=:id"), params)
    db.commit()
    return {"message": "Utilisateur mis a jour"}

@app.delete("/api/utilisateurs/{user_id}")
def delete_utilisateur(user_id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM utilisateurs WHERE id=:id"), {"id": user_id})
    db.commit()
    return {"message": "Utilisateur supprime"}


@app.get("/api/raccordements")
def get_raccordements(db: Session = Depends(get_db)):
    return [dict(r._mapping) for r in db.execute(text("SELECT * FROM raccordements ORDER BY id")).fetchall()]

@app.post("/api/raccordements")
def add_raccordement(data: dict, db: Session = Depends(get_db)):
    # Extraire seulement les champs connus
    params = {
        "numero_compteur": data.get("numero_compteur"),
        "type_abonne": data.get("type_abonne"),
        "nom_abonne": data.get("nom_abonne"),
        "adresse": data.get("adresse"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "region": data.get("region"),
        "commune": data.get("commune"),
        "date_raccordement": data.get("date_raccordement"),
        "etat": data.get("etat", "actif"),
        "index_initial": data.get("index_initial", 0),
        "tarif_type": data.get("tarif_type"),
        "telephone": data.get("telephone"),
    }
    query = text("""
        INSERT INTO raccordements (numero_compteur,type_abonne,nom_abonne,adresse,latitude,longitude,region,commune,date_raccordement,etat,index_initial,tarif_type,telephone)
        VALUES (:numero_compteur,:type_abonne,:nom_abonne,:adresse,:latitude,:longitude,:region,:commune,:date_raccordement,:etat,:index_initial,:tarif_type,:telephone)
        RETURNING id
    """)
    result = db.execute(query, params)
    db.commit()
    return {"id": result.fetchone()[0], "message": "Raccordement ajoute"}

@app.get("/api/consommations/{raccordement_id}")
def get_consommations(raccordement_id: int, db: Session = Depends(get_db)):
    return [dict(r._mapping) for r in db.execute(text("SELECT * FROM consommations WHERE raccordement_id=:id ORDER BY annee DESC,mois DESC"), {"id":raccordement_id}).fetchall()]

@app.post("/api/consommations")
def add_consommation(data: dict, db: Session = Depends(get_db)):
    query = text("INSERT INTO consommations (raccordement_id,mois,annee,consommation_m3,montant_fcfa,statut_paiement,date_releve) VALUES (:raccordement_id,:mois,:annee,:consommation_m3,:montant_fcfa,:statut_paiement,:date_releve) RETURNING id")
    result = db.execute(query, data)
    db.commit()
    return {"id": result.fetchone()[0], "message": "Consommation ajoutee"}

@app.get("/api/alertes")
def get_alertes(db: Session = Depends(get_db)):
    return [dict(r._mapping) for r in db.execute(text("SELECT a.*,p.nom as point_nom,p.commune FROM alertes a JOIN points_eau p ON p.id=a.point_eau_id WHERE a.lue=FALSE ORDER BY a.created_at DESC")).fetchall()]

@app.get("/api/interventions")
def get_interventions(db: Session = Depends(get_db)):
    return [dict(r._mapping) for r in db.execute(text("SELECT i.*,p.nom as point_nom,p.commune FROM interventions i JOIN points_eau p ON p.id=i.point_eau_id ORDER BY i.created_at DESC")).fetchall()]

@app.post("/api/interventions")
def add_intervention(data: dict, db: Session = Depends(get_db)):
    query = text("INSERT INTO interventions (point_eau_id,type_intervention,description,technicien,date_intervention,statut,cout_fcfa) VALUES (:point_eau_id,:type_intervention,:description,:technicien,:date_intervention,:statut,:cout_fcfa) RETURNING id")
    result = db.execute(query, data)
    db.commit()
    return {"id": result.fetchone()[0], "message": "Intervention ajoutee"}

# ── Télédétection / Prospection Sentinel-2 ───────────────────────────────────


@app.get("/api/zones_prospection")
def get_zones_prospection_alias(db: Session = Depends(get_db)):
    """Alias pour compatibilité frontend."""
    rows = db.execute(text("SELECT * FROM zones_prospection ORDER BY score_global DESC")).fetchall()
    return [dict(r._mapping) for r in rows]
@app.get("/api/prospection/zones")
def get_zones_prospection(db: Session = Depends(get_db)):
    """Lit les zones déjà analysées (rapide, depuis la base)."""
    rows = db.execute(text("SELECT * FROM zones_prospection ORDER BY score_global DESC")).fetchall()
    return [dict(r._mapping) for r in rows]

@app.post("/api/prospection/analyser")
def analyser_prospection(payload: dict = {}, db: Session = Depends(get_db)):
    """Lance une vraie analyse Sentinel-2 et sauvegarde les zones.
    Paramètres optionnels : region (str), type_analyse (forages|barrages|tous)"""
    region = payload.get("region", "") if payload else ""
    type_analyse = payload.get("type_analyse", "tous") if payload else "tous"
    # Vider les zones du même type avant insertion
    if type_analyse == "forages":
        db.execute(text("DELETE FROM zones_prospection WHERE type='forage'"))
    elif type_analyse == "barrages":
        db.execute(text("DELETE FROM zones_prospection WHERE type='barrage'"))
    else:
        db.execute(text("DELETE FROM zones_prospection"))
    db.commit()

    try:
        if type_analyse == "forages":
            zones = analyser_zones_forages_bf(region_filtre=region or None)
        elif type_analyse == "barrages":
            zones = analyser_zones_barrages_bf(region_filtre=region or None)
        else:
            # eau_surface, ndwi, ndvi, tous : analyser forages + barrages
            zones = analyser_zones_forages_bf(region_filtre=region or None) + analyser_zones_barrages_bf(region_filtre=region or None)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur télédétection: {e}")

    for z in zones:
        db.execute(text("""
            INSERT INTO zones_prospection
                (type, nom, region, latitude, longitude, ndwi, ndvi,
                 score_ndwi, score_ndvi, score_global,
                 profondeur_estimee_m, debit_estime_m3h, statut, source, date_analyse)
            VALUES
                (:type, :nom, :region, :latitude, :longitude, :ndwi, :ndvi,
                 :score_ndwi, :score_ndvi, :score_global,
                 :profondeur, :debit, :statut, :source, :date_analyse)
            ON CONFLICT (nom) DO UPDATE SET
                type=EXCLUDED.type,
                region=EXCLUDED.region, latitude=EXCLUDED.latitude, longitude=EXCLUDED.longitude,
                ndwi=EXCLUDED.ndwi, ndvi=EXCLUDED.ndvi,
                score_ndwi=EXCLUDED.score_ndwi, score_ndvi=EXCLUDED.score_ndvi,
                score_global=EXCLUDED.score_global,
                profondeur_estimee_m=EXCLUDED.profondeur_estimee_m,
                debit_estime_m3h=EXCLUDED.debit_estime_m3h,
                statut=EXCLUDED.statut, source=EXCLUDED.source, date_analyse=EXCLUDED.date_analyse
        """), {
            "type": z.get("type", "forage"),
            "nom": z["nom"], "region": z["region"],
            "latitude": z["latitude"], "longitude": z["longitude"],
            "ndwi": z["ndwi_reel"], "ndvi": z["ndvi_reel"],
            "score_ndwi": z["score_ndwi"], "score_ndvi": z["score_ndvi"],
            "score_global": z["score_global"],
            "profondeur": z["profondeur_estimee_m"], "debit": z["debit_estime_m3h"],
            "statut": z["statut"], "source": z["source"], "date_analyse": z["date_analyse"],
        })
    db.commit()
    return {"message": f"{len(zones)} zones analysées via Sentinel-2", "zones": zones}


# ── TARIFICATION ONEA BURKINA FASO ────────────────────────────────────────────
def calculer_facture_onea(volume_m3: float, type_abonne: str = "menage") -> float:
    """Calcul automatique facture selon tarification ONEA réelle BF"""
    if volume_m3 <= 0:
        return 1500.0  # redevance fixe uniquement
    
    montant = 1500.0  # redevance fixe mensuelle
    
    if type_abonne in ["menage", "social"]:
        # Tarif ménage
        if volume_m3 <= 8:
            montant += volume_m3 * 296
        elif volume_m3 <= 20:
            montant += 8 * 296 + (volume_m3 - 8) * 480
        elif volume_m3 <= 50:
            montant += 8 * 296 + 12 * 480 + (volume_m3 - 20) * 595
        else:
            montant += 8 * 296 + 12 * 480 + 30 * 595 + (volume_m3 - 50) * 695
    elif type_abonne in ["commerce", "industrie"]:
        # Tarif commercial
        montant += volume_m3 * 695
    else:
        montant += volume_m3 * 480
    
    return round(montant, 0)

@app.post("/api/releve")
def add_releve(data: dict, db: Session = Depends(get_db)):
    """Ajouter un relevé de compteur avec calcul automatique facture"""
    raccordement_id = data.get("raccordement_id")
    index_actuel = float(data.get("index_actuel", 0))
    mois = data.get("mois")
    annee = data.get("annee")
    
    # Récupérer le raccordement
    rac = db.execute(
        text("SELECT * FROM raccordements WHERE id=:id"),
        {"id": raccordement_id}
    ).fetchone()
    if not rac:
        return {"error": "Raccordement non trouvé"}
    
    # Récupérer le dernier relevé pour calculer la consommation
    dernier = db.execute(
        text("SELECT index_actuel FROM consommations WHERE raccordement_id=:id ORDER BY annee DESC, mois DESC LIMIT 1"),
        {"id": raccordement_id}
    ).fetchone()
    
    index_precedent = float(dernier[0]) if dernier else float(rac._mapping.get("index_initial", 0))
    
    # Calculer la consommation
    consommation_m3 = max(0, index_actuel - index_precedent)
    
    # Calculer la facture selon tarification ONEA
    type_abonne = rac._mapping.get("type_abonne", "menage")
    montant_fcfa = calculer_facture_onea(consommation_m3, type_abonne)
    
    # Insérer le relevé
    query = text("""
        INSERT INTO consommations 
        (raccordement_id, mois, annee, index_precedent, index_actuel,
         consommation_m3, montant_fcfa, statut_paiement, date_releve)
        VALUES (:raccordement_id, :mois, :annee, :index_precedent, :index_actuel,
                :consommation_m3, :montant_fcfa, 'impaye', CURRENT_DATE)
        RETURNING id
    """)
    result = db.execute(query, {
        "raccordement_id": raccordement_id,
        "mois": mois,
        "annee": annee,
        "index_precedent": index_precedent,
        "index_actuel": index_actuel,
        "consommation_m3": consommation_m3,
        "montant_fcfa": montant_fcfa
    })
    db.commit()
    
    return {
        "id": result.fetchone()[0],
        "index_precedent": index_precedent,
        "index_actuel": index_actuel,
        "consommation_m3": consommation_m3,
        "montant_fcfa": montant_fcfa,
        "message": "Relevé enregistré avec succès"
    }

@app.put("/api/consommations/{conso_id}/paiement")
def marquer_paye(conso_id: int, db: Session = Depends(get_db)):
    """Marquer une facture comme payée"""
    db.execute(
        text("UPDATE consommations SET statut_paiement='paye' WHERE id=:id"),
        {"id": conso_id}
    )
    db.commit()
    return {"message": "Facture marquée comme payée"}

@app.get("/api/raccordements/{id}/historique")
def get_historique(id: int, db: Session = Depends(get_db)):
    """Historique complet des relevés d'un abonné"""
    rows = db.execute(text("""
        SELECT c.*, r.nom_abonne, r.numero_compteur, r.type_abonne, r.commune
        FROM consommations c
        JOIN raccordements r ON r.id = c.raccordement_id
        WHERE c.raccordement_id = :id
        ORDER BY c.annee DESC, c.mois DESC
    """), {"id": id}).fetchall()
    return [dict(r._mapping) for r in rows]

@app.get("/api/onea/stats")
def get_onea_stats(db: Session = Depends(get_db)):
    """Statistiques globales ONEA"""
    total = db.execute(text("SELECT COUNT(*) FROM raccordements")).scalar()
    actifs = db.execute(text("SELECT COUNT(*) FROM raccordements WHERE etat='actif'")).scalar()
    conso_mois = db.execute(text("""
        SELECT COALESCE(SUM(consommation_m3),0) FROM consommations 
        WHERE mois=EXTRACT(MONTH FROM CURRENT_DATE) 
        AND annee=EXTRACT(YEAR FROM CURRENT_DATE)
    """)).scalar()
    montant_mois = db.execute(text("""
        SELECT COALESCE(SUM(montant_fcfa),0) FROM consommations
        WHERE mois=EXTRACT(MONTH FROM CURRENT_DATE)
        AND annee=EXTRACT(YEAR FROM CURRENT_DATE)
    """)).scalar()
    impaye = db.execute(text("""
        SELECT COALESCE(SUM(montant_fcfa),0) FROM consommations
        WHERE statut_paiement='impaye'
    """)).scalar()
    return {
        "total_abonnes": total,
        "abonnes_actifs": actifs,
        "conso_mois_m3": round(float(conso_mois), 2),
        "montant_mois_fcfa": round(float(montant_mois), 0),
        "montant_impaye_fcfa": round(float(impaye), 0)
    }

# ── NDWI POUR ZONES PRIORITAIRES ONEA ────────────────────────────────────────
@app.get("/api/onea/ndwi/{point_id}")
async def get_ndwi_zone(point_id: int, db: Session = Depends(get_db)):
    """Calcule le NDWI réel Sentinel-2 pour un point d'eau"""
    import requests as req
    from datetime import datetime, timedelta
    
    # Récupérer le point
    point = db.execute(
        text("SELECT * FROM points_eau WHERE id=:id"),
        {"id": point_id}
    ).fetchone()
    if not point:
        return {"error": "Point non trouvé"}
    
    lat = point._mapping["latitude"]
    lng = point._mapping["longitude"]
    
    # Bbox autour du point (±0.05 degrés ≈ 5km)
    bbox = [lng-0.05, lat-0.05, lng+0.05, lat+0.05]
    
    # Token Sentinel Hub
    CLIENT_ID = "sh-fdf1728e-7e1d-4404-8f54-e9799b8dae45"
    CLIENT_SECRET = "7sOoWXGA9UAuPv9jVGSk7LZJxP4iPFCt"
    
    try:
        token_resp = req.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data={"grant_type":"client_credentials","client_id":CLIENT_ID,"client_secret":CLIENT_SECRET},
            timeout=10
        )
        token = token_resp.json()["access_token"]
        
        # Calcul NDWI
        payload = {
            "input": {
                "bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
                "data": [{"type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {"from": "2025-11-01T00:00:00Z", "to": "2026-05-30T23:59:59Z"},
                        "maxCloudCoverage": 30,
                        "mosaickingOrder": "leastCC"
                    }
                }]
            },
            "output": {"width": 256, "height": 256,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}]
            },
            "evalscript": """//VERSION=3
function setup(){return{input:["B03","B08"],output:{bands:1}}}
function evaluatePixel(s){
    var v=(s.B03-s.B08)/(s.B03+s.B08+0.0001);
    return[Math.round((Math.max(-1,Math.min(1,v))+1)*127.5)];
}"""
        }
        
        r = req.post(
            "https://sh.dataspace.copernicus.eu/api/v1/process",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload, timeout=30
        )
        
        if r.status_code == 200:
            from PIL import Image
            import numpy as np
            from io import BytesIO
            img = Image.open(BytesIO(r.content)).convert("L")
            arr = np.array(img, dtype=float)
            ndwi_raw = float(arr.mean())
            ndwi = round((ndwi_raw / 127.5) - 1, 3)
            
            # Score priorité 0-100
            score_ndwi = round(min(100, max(0, (ndwi + 1) * 50)), 1)
            pop = point._mapping.get("pop_desservie") or 0
            score_pop = min(40, pop / 100)
            score_total = round(min(100, score_ndwi * 0.6 + score_pop * 0.4), 1)
            
            return {
                "point_id": point_id,
                "nom": point._mapping["nom"],
                "latitude": lat,
                "longitude": lng,
                "ndwi": ndwi,
                "score_ndwi": score_ndwi,
                "score_population": round(score_pop, 1),
                "score_priorite": score_total,
                "niveau_priorite": "HAUTE" if score_total > 65 else "MOYENNE" if score_total > 40 else "FAIBLE",
                "pop_desservie": pop,
                "source": "Sentinel-2 L2A (Copernicus ESA)",
                "date_analyse": datetime.now().strftime("%Y-%m-%d")
            }
    except Exception as e:
        return {"error": str(e), "point_id": point_id}
    
    return {"error": "Calcul impossible"}

@app.get("/api/onea/zones-prioritaires")
async def get_zones_prioritaires(db: Session = Depends(get_db)):
    """Analyse toutes les zones prioritaires avec NDWI réel"""
    import requests as req
    
    # Points sans raccordement nearby
    points = db.execute(text("""
        SELECT p.* FROM points_eau p
        WHERE p.type IN ('forage','borne')
        AND p.etat = 'fonctionnel'
    """)).fetchall()
    
    raccordements = db.execute(text("SELECT latitude, longitude FROM raccordements WHERE latitude IS NOT NULL")).fetchall()
    
    zones_prioritaires = []
    for p in points:
        lat = p._mapping["latitude"]
        lng = p._mapping["longitude"]
        
        # Vérifier si raccordement nearby (500m)
        has_raccordement = any(
            abs(r._mapping["latitude"]-lat) < 0.005 and abs(r._mapping["longitude"]-lng) < 0.005
            for r in raccordements if r._mapping["latitude"]
        )
        
        if not has_raccordement:
            zones_prioritaires.append({
                "id": p._mapping["id"],
                "nom": p._mapping["nom"],
                "type": p._mapping["type"],
                "region": p._mapping["region"],
                "commune": p._mapping["commune"],
                "latitude": lat,
                "longitude": lng,
                "pop_desservie": p._mapping.get("pop_desservie") or 0
            })
    
    return {
        "total_zones": len(zones_prioritaires),
        "zones": zones_prioritaires[:10]  # Top 10 pour ne pas surcharger l'API
    }

@app.get("/api/onea/ndvi/{point_id}")
async def get_ndvi_zone(point_id: int, db: Session = Depends(get_db)):
    import requests as req
    from datetime import datetime
    point = db.execute(text("SELECT * FROM points_eau WHERE id=:id"), {"id": point_id}).fetchone()
    if not point:
        return {"error": "Point non trouve"}
    lat = point._mapping["latitude"]
    lng = point._mapping["longitude"]
    bbox = [lng-0.05, lat-0.05, lng+0.05, lat+0.05]
    CLIENT_ID = "sh-fdf1728e-7e1d-4404-8f54-e9799b8dae45"
    CLIENT_SECRET = "7sOoWXGA9UAuPv9jVGSk7LZJxP4iPFCt"
    try:
        token_resp = req.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data={"grant_type":"client_credentials","client_id":CLIENT_ID,"client_secret":CLIENT_SECRET},
            timeout=10
        )
        token = token_resp.json()["access_token"]
        payload = {
            "input": {
                "bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
                "data": [{"type": "sentinel-2-l2a", "dataFilter": {
                    "timeRange": {"from": "2025-11-01T00:00:00Z", "to": "2026-05-30T23:59:59Z"},
                    "maxCloudCoverage": 30, "mosaickingOrder": "leastCC"
                }}]
            },
            "output": {"width": 256, "height": 256,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}]},
            "evalscript": """//VERSION=3
function setup(){return{input:["B04","B08"],output:{bands:1}}}
function evaluatePixel(s){
    var v=(s.B08-s.B04)/(s.B08+s.B04+0.0001);
    return[Math.round((Math.max(-1,Math.min(1,v))+1)*127.5)];
}"""
        }
        r = req.post(
            "https://sh.dataspace.copernicus.eu/api/v1/process",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload, timeout=30
        )
        if r.status_code == 200:
            from PIL import Image
            import numpy as np
            from io import BytesIO
            img = Image.open(BytesIO(r.content)).convert("L")
            arr = np.array(img, dtype=float)
            ndvi_raw = float(arr.mean())
            ndvi = round((ndvi_raw / 127.5) - 1, 3)
            score_ndvi = round(min(100, max(0, (ndvi + 1) * 50)), 1)
            saison = "Saison pluies" if ndvi > 0.3 else "Transition" if ndvi > 0 else "Saison seche"
            return {
                "point_id": point_id,
                "nom": point._mapping["nom"],
                "ndvi": ndvi,
                "score_ndvi": score_ndvi,
                "saison": saison,
                "date_analyse": datetime.now().strftime("%Y-%m-%d")
            }
    except Exception as e:
        return {"error": str(e)}
    return {"error": "Calcul impossible"}

@app.put("/api/interventions/{intervention_id}")
def update_intervention(intervention_id: int, data: dict, db: Session = Depends(get_db)):
    fields = []
    params = {"id": intervention_id}
    for key in ["type_intervention","description","technicien","cout_fcfa","statut","date_intervention"]:
        if key in data:
            fields.append(f"{key}=:{key}")
            params[key] = data[key]
    if not fields:
        return {"message": "Rien a mettre a jour"}
    db.execute(text(f"UPDATE interventions SET {','.join(fields)} WHERE id=:id"), params)
    db.commit()
    return {"message": "Intervention mise a jour"}

@app.put("/api/interventions/{intervention_id}/terminer")
def terminer_intervention(intervention_id: int, db: Session = Depends(get_db)):
    db.execute(text("UPDATE interventions SET statut='termine' WHERE id=:id"), {"id": intervention_id})
    db.commit()
    return {"message": "Intervention terminee"}

@app.delete("/api/interventions/{intervention_id}")
def delete_intervention(intervention_id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM interventions WHERE id=:id"), {"id": intervention_id})
    db.commit()
    return {"message": "Intervention supprimee"}

import os
if os.path.exists("../frontend"):
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
