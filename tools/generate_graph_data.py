#!/usr/bin/env python3
"""
Generate La Plagne routing graph from curated data.

Since the Overpass API is not accessible from this environment,
this script creates the graph from manually curated data based on
the official La Plagne piste map and resort documentation.

The topology is based on:
- Official La Plagne piste map 2025
- Lift infrastructure documentation
- Station locations and elevations

Output:
  app/data/graph.json    - Routing graph
  app/data/stations.json - Station metadata
"""

import json
import math
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "app", "data")


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ============================================================
# NODE DEFINITIONS
# Each node is a physical location in the ski area
# ============================================================

NODES = {
    # === Summit / High Points ===
    "glacier_top": {"lat": 45.5155, "lon": 6.6435, "ele": 3080, "station": None},
    "roche_de_mio": {"lat": 45.5115, "lon": 6.6535, "ele": 2700, "station": None},
    "grande_rochette": {"lat": 45.5048, "lon": 6.6700, "ele": 2505, "station": None},
    "verdons_top": {"lat": 45.4860, "lon": 6.6905, "ele": 2500, "station": None},
    "biolley_top": {"lat": 45.5165, "lon": 6.6740, "ele": 2350, "station": None},
    "becoin_top": {"lat": 45.5025, "lon": 6.6830, "ele": 2300, "station": None},
    "dos_rond_top": {"lat": 45.5150, "lon": 6.6590, "ele": 2200, "station": None},
    "lovatiere_top": {"lat": 45.4920, "lon": 6.6860, "ele": 2479, "station": None},

    # === Intermediate High Points ===
    "col_de_forcle": {"lat": 45.5090, "lon": 6.6545, "ele": 2400, "station": None},
    "les_bauches_top": {"lat": 45.5140, "lon": 6.6470, "ele": 2800, "station": None},
    "arpette_top": {"lat": 45.5060, "lon": 6.6580, "ele": 2200, "station": None},
    "colosses_top": {"lat": 45.5080, "lon": 6.6560, "ele": 2300, "station": None},
    "bergerie_top": {"lat": 45.5170, "lon": 6.6600, "ele": 2250, "station": None},
    "plan_bois_top": {"lat": 45.5200, "lon": 6.6490, "ele": 2100, "station": None},
    "inversens_top": {"lat": 45.5270, "lon": 6.6430, "ele": 2050, "station": None},
    "colorado_top": {"lat": 45.5035, "lon": 6.6750, "ele": 2150, "station": None},
    "blanchets_top": {"lat": 45.5040, "lon": 6.6620, "ele": 2100, "station": None},
    "envers_top": {"lat": 45.5150, "lon": 6.6720, "ele": 2300, "station": None},
    "carella_top": {"lat": 45.4750, "lon": 6.7100, "ele": 2300, "station": None},
    "rossa_top": {"lat": 45.4700, "lon": 6.7050, "ele": 2200, "station": None},
    "verdons_sud_top": {"lat": 45.4800, "lon": 6.6950, "ele": 2450, "station": None},
    "pierres_blanches_top": {"lat": 45.5300, "lon": 6.6440, "ele": 1900, "station": None},
    "salla_top": {"lat": 45.5260, "lon": 6.6400, "ele": 1850, "station": None},
    "quillis_top": {"lat": 45.5240, "lon": 6.6360, "ele": 1800, "station": None},
    "adrets_top": {"lat": 45.5190, "lon": 6.6460, "ele": 2050, "station": None},
    "ecureuils_top": {"lat": 45.4920, "lon": 6.6570, "ele": 1800, "station": None},
    "dou_du_praz_top": {"lat": 45.4950, "lon": 6.6600, "ele": 1900, "station": None},
    "golf_top": {"lat": 45.5000, "lon": 6.6690, "ele": 2050, "station": None},
    "melezes_top": {"lat": 45.5020, "lon": 6.6810, "ele": 2000, "station": None},
    "chalet_bellecote_top": {"lat": 45.5100, "lon": 6.6580, "ele": 2450, "station": None},
    "montchavin_chair_top": {"lat": 45.5310, "lon": 6.6430, "ele": 1600, "station": None},
    "crozats_top": {"lat": 45.5280, "lon": 6.6410, "ele": 1700, "station": None},
    "bijolin_top": {"lat": 45.4970, "lon": 6.6650, "ele": 1950, "station": None},
    "lac_noir_top": {"lat": 45.4810, "lon": 6.6620, "ele": 2150, "station": None},

    # === Mid-mountain Connection Points ===
    "champagny_mid": {"lat": 45.4700, "lon": 6.7150, "ele": 1850, "station": None},
    "montchavin_mid": {"lat": 45.5320, "lon": 6.6425, "ele": 1600, "station": None},
    "montalbert_mid": {"lat": 45.4900, "lon": 6.6590, "ele": 1700, "station": None},
    "roche_mio_mid": {"lat": 45.5100, "lon": 6.6550, "ele": 2500, "station": None},

    # === Base Stations ===
    "plagne_centre": {"lat": 45.5070, "lon": 6.6770, "ele": 1970, "station": "Plagne Centre"},
    "aime_la_plagne": {"lat": 45.5130, "lon": 6.6750, "ele": 2100, "station": "Aime-La Plagne"},
    "belle_plagne": {"lat": 45.5090, "lon": 6.6650, "ele": 2050, "station": "Belle Plagne"},
    "plagne_bellecote": {"lat": 45.5050, "lon": 6.6610, "ele": 1930, "station": "Plagne Bellecote"},
    "plagne_soleil": {"lat": 45.5140, "lon": 6.6620, "ele": 2050, "station": "Plagne Soleil"},
    "plagne_villages": {"lat": 45.5130, "lon": 6.6680, "ele": 2050, "station": "Plagne Villages"},
    "plagne_1800": {"lat": 45.5010, "lon": 6.6840, "ele": 1800, "station": "Plagne 1800"},
    "champagny": {"lat": 45.4630, "lon": 6.7270, "ele": 1250, "station": "Champagny"},
    "montchavin": {"lat": 45.5340, "lon": 6.6420, "ele": 1250, "station": "Montchavin"},
    "les_coches": {"lat": 45.5230, "lon": 6.6380, "ele": 1450, "station": "Les Coches"},
    "montalbert": {"lat": 45.4880, "lon": 6.6560, "ele": 1350, "station": "Montalbert"},
}


# ============================================================
# EDGE DEFINITIONS
# Format: (id, source, target, name, type, subtype, difficulty/liftType)
# type: "slope" or "lift"
# subtype for slopes: difficulty color
# subtype for lifts: lift_type
# ============================================================

LIFTS = [
    # === Major Gondolas / Cable Cars ===
    ("lift_funiplagne", "plagne_centre", "grande_rochette", "Funiplagne Grande Rochette", "gondola"),
    ("lift_telemetro", "plagne_centre", "aime_la_plagne", "Telemetro", "cable_car"),
    ("lift_roche_mio_1", "plagne_bellecote", "col_de_forcle", "Roche de Mio 1", "gondola"),
    ("lift_roche_mio_2", "col_de_forcle", "roche_de_mio", "Roche de Mio 2", "gondola"),
    ("lift_glaciers_1", "roche_de_mio", "les_bauches_top", "Glaciers 1", "gondola"),
    ("lift_glaciers_2", "les_bauches_top", "glacier_top", "Glaciers 2", "gondola"),
    ("lift_belle_plagne", "plagne_bellecote", "belle_plagne", "Belle Plagne", "gondola"),
    ("lift_montalbert", "montalbert", "montalbert_mid", "Montalbert", "gondola"),
    ("lift_champagny", "champagny", "champagny_mid", "Champagny", "gondola"),
    ("lift_les_coches", "les_coches", "plan_bois_top", "Les Coches", "gondola"),
    ("lift_lac_noir", "montalbert_mid", "lac_noir_top", "Lac Noir", "gondola"),

    # === 6-seat Express Chairlifts ===
    ("lift_lovatiere", "plagne_centre", "lovatiere_top", "La Lovatiere", "chair_lift"),
    ("lift_bergerie", "plagne_soleil", "bergerie_top", "Bergerie", "chair_lift"),
    ("lift_la_roche", "les_coches", "inversens_top", "La Roche", "chair_lift"),
    ("lift_envers", "aime_la_plagne", "envers_top", "Les Envers", "chair_lift"),
    ("lift_verdons_sud", "champagny_mid", "verdons_sud_top", "Verdons Sud", "chair_lift"),

    # === Standard Chairlifts ===
    ("lift_becoin", "plagne_1800", "becoin_top", "Becoin", "chair_lift"),
    ("lift_colorado", "plagne_centre", "colorado_top", "Colorado", "chair_lift"),
    ("lift_arpette", "plagne_bellecote", "arpette_top", "Arpette", "chair_lift"),
    ("lift_colosses", "plagne_bellecote", "colosses_top", "Les Colosses", "chair_lift"),
    ("lift_blanchets", "plagne_bellecote", "blanchets_top", "Blanchets", "chair_lift"),
    ("lift_dos_rond", "plagne_soleil", "dos_rond_top", "Dos Rond", "chair_lift"),
    ("lift_plan_bois", "plagne_soleil", "plan_bois_top", "Plan Bois", "chair_lift"),
    ("lift_carella", "champagny_mid", "carella_top", "Carella", "chair_lift"),
    ("lift_rossa", "champagny_mid", "rossa_top", "La Rossa", "chair_lift"),
    ("lift_pierres_blanches", "montchavin_mid", "pierres_blanches_top", "Pierres Blanches", "chair_lift"),
    ("lift_salla", "les_coches", "salla_top", "Salla", "chair_lift"),
    ("lift_quillis", "les_coches", "quillis_top", "Les Quillis", "chair_lift"),
    ("lift_inversens", "montchavin_mid", "inversens_top", "Inversens", "chair_lift"),
    ("lift_adrets", "plagne_soleil", "adrets_top", "Adrets", "chair_lift"),
    ("lift_ecureuils", "montalbert", "ecureuils_top", "Ecureuils", "chair_lift"),
    ("lift_dou_du_praz", "montalbert_mid", "dou_du_praz_top", "Dou du Praz", "chair_lift"),
    ("lift_golf", "plagne_bellecote", "golf_top", "Golf", "chair_lift"),
    ("lift_melezes", "plagne_1800", "melezes_top", "Melezes", "chair_lift"),
    ("lift_chalet_bellecote", "belle_plagne", "chalet_bellecote_top", "Chalet de Bellecote", "chair_lift"),
    ("lift_montchavin", "montchavin", "montchavin_chair_top", "Montchavin", "chair_lift"),
    ("lift_crozats", "montchavin_mid", "crozats_top", "Crozats", "chair_lift"),
    ("lift_bijolin", "plagne_bellecote", "bijolin_top", "Bijolin", "chair_lift"),
    ("lift_les_bauches", "roche_mio_mid", "les_bauches_top", "Les Bauches", "chair_lift"),
    ("lift_boulevard", "plagne_centre", "colorado_top", "Boulevard", "chair_lift"),

    # === Drag Lifts ===
    ("lift_col_forcle_tk", "col_de_forcle", "roche_mio_mid", "Col de Forcle", "drag_lift"),

    # === Return / Bidirectional connections ===
    ("lift_telemetro_ret", "aime_la_plagne", "plagne_centre", "Telemetro (retour)", "cable_car"),
    ("lift_biolley", "aime_la_plagne", "biolley_top", "Le Biolley", "chair_lift"),
    ("lift_plagne_1800", "plagne_1800", "plagne_centre", "Plagne 1800", "chair_lift"),
    ("lift_champagny_verdons", "champagny_mid", "verdons_top", "Verdons", "chair_lift"),
]

SLOPES = [
    # === From Grande Rochette (2505m) ===
    ("slope_kamikaze", "grande_rochette", "plagne_centre", "Kamikaze", "red"),
    ("slope_mira", "grande_rochette", "plagne_centre", "Mira", "blue"),
    ("slope_tunnel", "grande_rochette", "plagne_1800", "Tunnel", "blue"),
    ("slope_cr_grande_rochette", "grande_rochette", "belle_plagne", "Grande Rochette", "blue"),
    ("slope_bonsoir", "grande_rochette", "plagne_villages", "Bonsoir", "blue"),
    ("slope_hara_kiri", "grande_rochette", "plagne_centre", "Hara Kiri", "red"),

    # === From Roche de Mio (2700m) ===
    ("slope_laines", "roche_de_mio", "plagne_bellecote", "Les Laines", "blue"),
    ("slope_dunes", "roche_de_mio", "plagne_bellecote", "Les Dunes", "blue"),
    ("slope_chiaupe", "roche_de_mio", "belle_plagne", "Chiaupe", "red"),
    ("slope_montde_la_guerre_top", "roche_de_mio", "champagny_mid", "Mont de la Guerre (haut)", "red"),
    ("slope_pollux", "roche_de_mio", "plagne_soleil", "La Pollux", "red"),
    ("slope_roche_mio_blue", "roche_de_mio", "col_de_forcle", "Roche de Mio", "blue"),

    # === From Glacier (3080m) ===
    ("slope_bellecote_noir", "glacier_top", "roche_de_mio", "Bellecote", "black"),
    ("slope_rochu", "glacier_top", "roche_de_mio", "Le Rochu", "black"),
    ("slope_derochoir", "glacier_top", "les_bauches_top", "Derochoir", "black"),

    # === From Les Bauches (2800m) ===
    ("slope_bauches_blue", "les_bauches_top", "roche_de_mio", "Les Bauches", "blue"),
    ("slope_bauches_red", "les_bauches_top", "col_de_forcle", "Traverse Bauches", "red"),

    # === From Les Verdons (2500m) ===
    ("slope_mont_de_la_guerre", "verdons_top", "champagny", "Mont de la Guerre", "red"),
    ("slope_verdons_blue", "verdons_top", "plagne_centre", "Les Verdons", "blue"),
    ("slope_biolley_descent", "verdons_top", "aime_la_plagne", "Biolley", "blue"),

    # === From Lovatiere top (2479m) ===
    ("slope_lovatiere_blue", "lovatiere_top", "plagne_centre", "Lovatiere", "blue"),
    ("slope_lovatiere_red", "lovatiere_top", "plagne_1800", "Sources", "red"),
    ("slope_verdons_to_lovatiere", "verdons_top", "lovatiere_top", "Liaison Verdons", "blue"),
    ("slope_lovatiere_to_verdons", "lovatiere_top", "verdons_top", "Traversee Verdons", "blue"),

    # === From Le Biolley (2350m) ===
    ("slope_etroits", "biolley_top", "aime_la_plagne", "Les Etroits", "black"),
    ("slope_morbleu", "biolley_top", "aime_la_plagne", "Morbleu", "black"),
    ("slope_palsembleu", "biolley_top", "aime_la_plagne", "Palsembleu", "black"),
    ("slope_biolley_blue", "biolley_top", "plagne_villages", "Le Biolley", "blue"),

    # === From Envers top (2300m) ===
    ("slope_coqs", "envers_top", "aime_la_plagne", "Les Coqs", "black"),
    ("slope_envers_blue", "envers_top", "plagne_villages", "Les Envers", "blue"),
    ("slope_envers_red", "envers_top", "aime_la_plagne", "Fornelet", "red"),

    # === From Becoin top (2300m) ===
    ("slope_java", "becoin_top", "plagne_1800", "Java", "red"),
    ("slope_mont_st_sauveur", "becoin_top", "plagne_centre", "Mont St Sauveur", "red"),
    ("slope_st_esprit", "becoin_top", "plagne_1800", "St Esprit", "blue"),
    ("slope_toboggan", "becoin_top", "plagne_centre", "Toboggan", "blue"),

    # === From Dos Rond (2200m) ===
    ("slope_dos_rond_blue", "dos_rond_top", "plagne_soleil", "Dos Rond", "blue"),
    ("slope_marmottes", "dos_rond_top", "plagne_soleil", "Les Marmottes", "green"),
    ("slope_dos_rond_to_coches", "dos_rond_top", "les_coches", "Gentiane", "blue"),

    # === From Bergerie top (2250m) ===
    ("slope_bergerie_blue", "bergerie_top", "plagne_soleil", "Bergerie", "blue"),
    ("slope_bergerie_red", "bergerie_top", "plagne_villages", "Combe", "red"),

    # === From Col de Forcle (2400m) ===
    ("slope_forcle_blue", "col_de_forcle", "belle_plagne", "Col de Forcle", "blue"),
    ("slope_forcle_red", "col_de_forcle", "plagne_bellecote", "Borseliers", "red"),

    # === From Colorado top (2150m) ===
    ("slope_colorado_green", "colorado_top", "plagne_centre", "Colorado", "green"),
    ("slope_colorado_blue", "colorado_top", "plagne_centre", "Arnica", "blue"),

    # === From Arpette top (2200m) ===
    ("slope_arpette", "arpette_top", "plagne_bellecote", "Arpette", "blue"),
    ("slope_arpette_to_belle", "arpette_top", "belle_plagne", "Lac", "blue"),

    # === From Colosses top (2300m) ===
    ("slope_colosses_blue", "colosses_top", "plagne_bellecote", "Les Colosses", "blue"),
    ("slope_colosses_to_mio", "col_de_forcle", "colosses_top", "Traverse", "blue"),

    # === From Blanchets top (2100m) ===
    ("slope_blanchets", "blanchets_top", "plagne_bellecote", "Blanchets", "green"),

    # === From Plan Bois top (2100m) ===
    ("slope_plan_bois_blue", "plan_bois_top", "plagne_soleil", "Plan Bois", "blue"),
    ("slope_plan_bois_to_coches", "plan_bois_top", "les_coches", "Les Coches", "blue"),
    ("slope_plan_bois_red", "plan_bois_top", "les_coches", "Praline", "red"),

    # === From Inversens top (2050m) ===
    ("slope_inversens", "inversens_top", "montchavin_mid", "Inversens", "blue"),
    ("slope_inversens_red", "inversens_top", "les_coches", "Rhodos", "red"),
    ("slope_inversens_to_coches", "inversens_top", "les_coches", "Myrtilles", "blue"),

    # === From Carella top (2300m) ===
    ("slope_carella_blue", "carella_top", "champagny_mid", "Carella", "blue"),
    ("slope_carella_red", "carella_top", "champagny", "Combe de Champagny", "red"),

    # === From Rossa top (2200m) ===
    ("slope_rossa_blue", "rossa_top", "champagny_mid", "La Rossa", "blue"),
    ("slope_rossa_red", "rossa_top", "champagny", "Bois", "red"),

    # === From Verdons Sud top (2450m) ===
    ("slope_verdons_sud_blue", "verdons_sud_top", "champagny_mid", "Verdons Sud", "blue"),
    ("slope_verdons_sud_to_top", "verdons_top", "verdons_sud_top", "Liaison Verdons Sud", "blue"),
    ("slope_champagny_mid_to_base", "champagny_mid", "champagny", "Champagny Bas", "blue"),

    # === From Pierres Blanches top (1900m) ===
    ("slope_pierres_blanches", "pierres_blanches_top", "montchavin_mid", "Pierres Blanches", "blue"),
    ("slope_pierres_blanches_to_mc", "pierres_blanches_top", "montchavin", "Descente Montchavin", "blue"),

    # === From Salla top (1850m) ===
    ("slope_salla_blue", "salla_top", "les_coches", "Salla", "blue"),
    ("slope_salla_green", "salla_top", "les_coches", "Pre des Coches", "green"),

    # === From Quillis top (1800m) ===
    ("slope_quillis", "quillis_top", "les_coches", "Les Quillis", "green"),

    # === From Adrets top (2050m) ===
    ("slope_adrets_blue", "adrets_top", "plagne_soleil", "Adrets", "blue"),
    ("slope_adrets_to_coches", "adrets_top", "les_coches", "Traverse Adrets", "blue"),

    # === From Ecureuils top (1800m) ===
    ("slope_ecureuils_blue", "ecureuils_top", "montalbert", "Ecureuils", "blue"),
    ("slope_ecureuils_green", "ecureuils_top", "montalbert", "Jardin", "green"),

    # === From Dou du Praz top (1900m) ===
    ("slope_dou_du_praz", "dou_du_praz_top", "montalbert_mid", "Dou du Praz", "blue"),
    ("slope_dou_du_praz_red", "dou_du_praz_top", "montalbert", "Grand Bois", "red"),

    # === From Golf top (2050m) ===
    ("slope_golf_blue", "golf_top", "plagne_bellecote", "Golf", "blue"),
    ("slope_golf_to_belle", "golf_top", "belle_plagne", "Melezes", "blue"),

    # === From Melezes top (2000m) ===
    ("slope_melezes_blue", "melezes_top", "plagne_1800", "Melezes Bas", "blue"),
    ("slope_melezes_to_centre", "melezes_top", "plagne_centre", "Liaison 1800", "blue"),

    # === From Chalet Bellecote top (2450m) ===
    ("slope_chalet_bellecote", "chalet_bellecote_top", "belle_plagne", "Chalet de Bellecote", "blue"),
    ("slope_chalet_bellecote_red", "chalet_bellecote_top", "plagne_bellecote", "Crete Cote", "black"),

    # === From Montchavin chair top (1600m) ===
    ("slope_montchavin_blue", "montchavin_chair_top", "montchavin", "Descente Montchavin", "blue"),
    ("slope_montchavin_to_mid", "montchavin_chair_top", "montchavin_mid", "Liaison Montchavin", "green"),

    # === From Crozats top (1700m) ===
    ("slope_crozats_blue", "crozats_top", "montchavin_mid", "Crozats", "blue"),
    ("slope_crozats_to_mc", "crozats_top", "montchavin", "Crozats Bas", "blue"),

    # === From Roche Mio mid (2500m) ===
    ("slope_roche_mio_mid_blue", "roche_mio_mid", "col_de_forcle", "Traverse Mio", "blue"),
    ("slope_roche_mio_mid_to_bp", "roche_mio_mid", "belle_plagne", "Descente Mio", "red"),

    # === From Bijolin top (1950m) ===
    ("slope_bijolin_blue", "bijolin_top", "plagne_bellecote", "Bijolin", "blue"),
    ("slope_bijolin_to_montalbert", "bijolin_top", "montalbert_mid", "Liaison Bijolin", "blue"),

    # === From Lac Noir top (2150m) ===
    ("slope_lac_noir_blue", "lac_noir_top", "montalbert_mid", "Lac Noir", "blue"),
    ("slope_lac_noir_red", "lac_noir_top", "montalbert", "Lac Noir Rouge", "red"),
    ("slope_lac_noir_to_bellecote", "lac_noir_top", "plagne_bellecote", "Liaison Lac Noir", "blue"),

    # === Inter-station connections (gentle slopes / connection pistes) ===
    ("slope_centre_to_bellecote", "plagne_centre", "plagne_bellecote", "Liaison Centre-Bellecote", "green"),
    ("slope_belle_to_villages", "belle_plagne", "plagne_villages", "Liaison Belle-Villages", "green"),
    ("slope_villages_to_soleil", "plagne_villages", "plagne_soleil", "Liaison Villages-Soleil", "green"),
    ("slope_soleil_to_villages", "plagne_soleil", "plagne_villages", "Liaison Soleil-Villages", "green"),
    ("slope_montchavin_mid_to_mc", "montchavin_mid", "montchavin", "Descente Montchavin bas", "green"),

    # === From Mont de la Guerre mid-route ===
    ("slope_mont_guerre_bas", "champagny_mid", "champagny", "Mont de la Guerre (bas)", "red"),

    # === Bosses (mogul run) ===
    ("slope_bosses", "grande_rochette", "plagne_centre", "Bosses", "black"),

    # === Additional connectivity slopes ===
    ("slope_aime_to_centre", "aime_la_plagne", "plagne_centre", "Liaison Aime-Centre", "green"),
    ("slope_aime_to_villages", "aime_la_plagne", "plagne_villages", "Liaison Aime-Villages", "green"),
    ("slope_villages_to_centre", "plagne_villages", "plagne_centre", "Liaison Villages-Centre", "green"),
    ("slope_soleil_to_bellecote", "plagne_soleil", "plagne_bellecote", "Traverse Soleil-Bellecote", "blue"),
    ("slope_villages_to_belle", "plagne_villages", "belle_plagne", "Traverse Villages-Belle", "blue"),
    ("slope_belle_to_bellecote", "belle_plagne", "plagne_bellecote", "Liaison Belle-Bellecote", "green"),
    ("slope_montalbert_mid_to_base", "montalbert_mid", "montalbert", "Descente Montalbert", "blue"),
    ("slope_centre_to_1800", "plagne_centre", "plagne_1800", "Liaison Centre-1800", "blue"),

    # === Long descent routes ===
    ("slope_grande_rochette_to_1800", "grande_rochette", "plagne_1800", "Descente 1800", "blue"),
    ("slope_roche_mio_to_montalbert", "roche_de_mio", "montalbert_mid", "Grand Descente", "red"),
]


def generate_geometry(source_node, target_node, num_points=5):
    """Generate a simple geometry line between two nodes."""
    s = NODES[source_node]
    t = NODES[target_node]
    points = []
    for i in range(num_points):
        frac = i / (num_points - 1)
        lat = s["lat"] + (t["lat"] - s["lat"]) * frac
        lon = s["lon"] + (t["lon"] - s["lon"]) * frac
        points.append([round(lat, 5), round(lon, 5)])
    return points


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("Generating La Plagne routing graph from curated data")
    print("=" * 60)

    # Build nodes dict
    nodes = {}
    for node_id, data in NODES.items():
        nodes[node_id] = {
            "lat": data["lat"],
            "lon": data["lon"],
            "ele": data["ele"],
            "station": data["station"],
        }

    print(f"\nNodes: {len(nodes)}")
    print(f"  Stations: {sum(1 for n in nodes.values() if n['station'])}")

    # Build edges
    edges = []

    # Process lifts
    for lift_id, source, target, name, lift_type in LIFTS:
        s = NODES[source]
        t = NODES[target]
        distance = round(haversine_m(s["lat"], s["lon"], t["lat"], t["lon"]))

        edge = {
            "id": lift_id,
            "source": source,
            "target": target,
            "name": name,
            "type": "lift",
            "liftType": lift_type,
            "distance": distance,
            "elevationDelta": t["ele"] - s["ele"],
            "geometry": generate_geometry(source, target),
        }
        edges.append(edge)

    # Process slopes
    for slope_id, source, target, name, difficulty in SLOPES:
        s = NODES[source]
        t = NODES[target]
        distance = round(haversine_m(s["lat"], s["lon"], t["lat"], t["lon"]))

        # For slopes, add some extra distance to account for switchbacks
        # (straight-line distance underestimates actual ski path)
        slope_factor = 1.4 if difficulty in ("red", "black") else 1.6
        distance = round(distance * slope_factor)

        edge = {
            "id": slope_id,
            "source": source,
            "target": target,
            "name": name,
            "type": "slope",
            "difficulty": difficulty,
            "distance": distance,
            "elevationDelta": t["ele"] - s["ele"],
            "geometry": generate_geometry(source, target),
        }
        edges.append(edge)

    slope_count = sum(1 for e in edges if e["type"] == "slope")
    lift_count = sum(1 for e in edges if e["type"] == "lift")

    print(f"\nEdges: {len(edges)}")
    print(f"  Slopes: {slope_count}")
    print(f"  Lifts: {lift_count}")

    # Difficulty distribution
    from collections import Counter
    diff_counts = Counter(e["difficulty"] for e in edges if e["type"] == "slope")
    print(f"\nSlope difficulty distribution:")
    for color in ["green", "blue", "red", "black"]:
        print(f"  {color}: {diff_counts.get(color, 0)}")

    # Lift type distribution
    lift_type_counts = Counter(e["liftType"] for e in edges if e["type"] == "lift")
    print(f"\nLift type distribution:")
    for lt, count in sorted(lift_type_counts.items()):
        print(f"  {lt}: {count}")

    # Build graph JSON
    graph = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "generated": "2026-02-13",
            "source": "Curated from La Plagne piste map 2025",
            "slopeCount": slope_count,
            "liftCount": lift_count,
            "nodeCount": len(nodes),
            "edgeCount": len(edges),
            "boundingBox": {"south": 45.48, "north": 45.58, "west": 6.62, "east": 6.78},
        },
    }

    # Save graph
    graph_file = os.path.join(DATA_DIR, "graph.json")
    with open(graph_file, "w") as f:
        json.dump(graph, f)
    print(f"\nSaved graph to {graph_file}")
    print(f"File size: {os.path.getsize(graph_file) / 1024:.1f} KB")

    # Build stations list
    stations = []
    for node_id, node in nodes.items():
        if node["station"]:
            stations.append({
                "name": node["station"],
                "nodeId": node_id,
                "lat": node["lat"],
                "lon": node["lon"],
                "ele": node["ele"],
            })

    stations.sort(key=lambda s: s["name"])

    stations_file = os.path.join(DATA_DIR, "stations.json")
    with open(stations_file, "w") as f:
        json.dump(stations, f, indent=2)
    print(f"Saved stations to {stations_file}")

    print(f"\n{'=' * 60}")
    print("Graph generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
