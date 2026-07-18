"""Static reference data for Tunisia: governorates, ATC classes, medications, suppliers."""
from __future__ import annotations

# ── 24 governorates: (code, name_fr, name_ar, population, centroid_lat, centroid_lon) ──
GOVERNORATES = [
    ("11", "Tunis", "تونس", 1056000, 36.8065, 10.1815),
    ("12", "Ariana", "أريانة", 576000, 36.8625, 10.1956),
    ("13", "Ben Arous", "بن عروس", 631000, 36.7533, 10.2283),
    ("14", "Manouba", "منوبة", 379000, 36.8078, 10.0972),
    ("21", "Nabeul", "نابل", 787000, 36.4560, 10.7376),
    ("22", "Zaghouan", "زغوان", 176000, 36.4028, 10.1425),
    ("23", "Bizerte", "بنزرت", 568000, 37.2746, 9.8739),
    ("31", "Béja", "باجة", 303000, 36.7256, 9.1817),
    ("32", "Jendouba", "جندوبة", 401000, 36.5011, 8.7803),
    ("33", "Le Kef", "الكاف", 243000, 36.1742, 8.7049),
    ("34", "Siliana", "سليانة", 223000, 36.0849, 9.3708),
    ("41", "Kairouan", "القيروان", 570000, 35.6781, 10.0963),
    ("42", "Kasserine", "القصرين", 439000, 35.1676, 8.8365),
    ("43", "Sidi Bouzid", "سيدي بوزيد", 429000, 35.0382, 9.4849),
    ("51", "Sousse", "سوسة", 674000, 35.8256, 10.6084),
    ("52", "Monastir", "المنستير", 548000, 35.7643, 10.8113),
    ("53", "Mahdia", "المهدية", 410000, 35.5047, 11.0622),
    ("61", "Sfax", "صفاقس", 955000, 34.7406, 10.7603),
    ("71", "Gafsa", "قفصة", 337000, 34.4250, 8.7842),
    ("72", "Tozeur", "توزر", 107000, 33.9197, 8.1335),
    ("73", "Kébili", "قبلي", 156000, 33.7047, 8.9690),
    ("81", "Gabès", "قابس", 374000, 33.8815, 10.0982),
    ("82", "Médenine", "مدنين", 479000, 33.3549, 10.5055),
    ("83", "Tataouine", "تطاوين", 149000, 32.9297, 10.4518),
]

# ── ATC anatomical/therapeutic groups referenced by the catalogue ──
# (code, level, label_fr, label_ar, parent_code)
ATC_CLASSES = [
    ("A", 1, "Voies digestives et métabolisme", "الجهاز الهضمي والأيض", None),
    ("A02", 3, "Antiacides / anti-ulcéreux", "مضادات الحموضة", "A"),
    ("A02BC", 4, "Inhibiteurs de la pompe à protons", "مثبطات مضخة البروتون", "A02"),
    ("A10", 3, "Antidiabétiques", "أدوية السكري", "A"),
    ("A10BA", 4, "Biguanides", "بيغوانيد", "A10"),
    ("A10AE", 4, "Insulines lentes", "أنسولين طويل المفعول", "A10"),
    ("C", 1, "Système cardiovasculaire", "الجهاز القلبي الوعائي", None),
    ("C07", 3, "Bêta-bloquants", "حاصرات بيتا", "C"),
    ("C08", 3, "Inhibiteurs calciques", "حاصرات الكالسيوم", "C"),
    ("C09", 3, "Système rénine-angiotensine", "الجهاز الريني", "C"),
    ("C09AA", 4, "Inhibiteurs de l'ECA", "مثبطات الإنزيم المحول", "C09"),
    ("C10", 3, "Hypolipémiants", "خافضات الدهون", "C"),
    ("C10AA", 4, "Statines", "ستاتين", "C10"),
    ("J", 1, "Anti-infectieux généraux", "مضادات العدوى", None),
    ("J01", 3, "Antibactériens", "مضادات الجراثيم", "J"),
    ("J01CA", 4, "Pénicillines à large spectre", "بنسلين واسع الطيف", "J01"),
    ("J01CR", 4, "Pénicillines + inhibiteurs", "بنسلين + مثبطات", "J01"),
    ("J01DD", 4, "Céphalosporines 3e génération", "سيفالوسبورين الجيل الثالث", "J01"),
    ("J01FA", 4, "Macrolides", "ماكروليد", "J01"),
    ("J01MA", 4, "Fluoroquinolones", "فلوروكينولون", "J01"),
    ("M", 1, "Muscle et squelette", "العضلات والهيكل العظمي", None),
    ("M01A", 3, "Anti-inflammatoires non stéroïdiens", "مضادات الالتهاب", "M"),
    ("N", 1, "Système nerveux", "الجهاز العصبي", None),
    ("N02BE", 4, "Anilides (paracétamol)", "أنيليد", "N"),
    ("N02BA", 4, "Salicylés", "ساليسيلات", "N"),
    ("N05", 3, "Psycholeptiques", "مهدئات", "N"),
    ("N06AB", 4, "Antidépresseurs ISRS", "مضادات الاكتئاب", "N"),
    ("R", 1, "Système respiratoire", "الجهاز التنفسي", None),
    ("R03AC", 4, "Bêta-2 agonistes inhalés", "ناهضات بيتا 2", "R"),
    ("R03BA", 4, "Corticoïdes inhalés", "كورتيكويد استنشاقي", "R"),
    ("R06A", 3, "Antihistaminiques", "مضادات الهيستامين", "R"),
    ("H", 1, "Hormones systémiques", "الهرمونات", None),
    ("H03AA", 4, "Hormones thyroïdiennes", "هرمونات الغدة الدرقية", "H"),
    ("B", 1, "Sang et organes hématopoïétiques", "الدم", None),
    ("B01AC", 4, "Antiagrégants plaquettaires", "مضادات التخثر الصفيحية", "B"),
]

# ── Medications catalogue ──
# (brand, dci, atc, form, dosage, ddd_value, ddd_unit, price_tnd, essential, rx)
MEDICATIONS = [
    # Antibiotics (J01) — high shortage sensitivity
    ("Clamoxyl 500", "Amoxicilline", "J01CA04", "gélule", "500 mg", 1.5, "g", 6.500, True, True),
    ("Clamoxyl 1g", "Amoxicilline", "J01CA04", "comprimé", "1 g", 1.5, "g", 9.200, True, True),
    ("Hiconcil 250", "Amoxicilline", "J01CA04", "sirop", "250 mg/5ml", 1.5, "g", 4.800, True, True),
    ("Augmentin 1g", "Amoxicilline/Ac. clavulanique", "J01CR02", "comprimé", "1 g", 1.5, "g",
     12.400, True, True),
    ("Augmentin 500", "Amoxicilline/Ac. clavulanique", "J01CR02", "sachet", "500 mg", 1.5, "g",
     9.900, True, True),
    ("Rocéphine 1g", "Ceftriaxone", "J01DD04", "injectable", "1 g", 2.0, "g", 15.300, True, True),
    ("Claforan 1g", "Céfotaxime", "J01DD01", "injectable", "1 g", 4.0, "g", 14.100, True, True),
    ("Zinnat 500", "Céfuroxime", "J01DC02", "comprimé", "500 mg", 0.5, "g", 11.700, False, True),
    ("Zithromax 500", "Azithromycine", "J01FA10", "comprimé", "500 mg", 0.3, "g", 13.500, False, True),
    ("Rulid 150", "Roxithromycine", "J01FA06", "comprimé", "150 mg", 0.3, "g", 8.900, False, True),
    ("Ciflox 500", "Ciprofloxacine", "J01MA02", "comprimé", "500 mg", 1.0, "g", 9.600, True, True),
    ("Tavanic 500", "Lévofloxacine", "J01MA12", "comprimé", "500 mg", 0.5, "g", 16.200, False, True),
    ("Flagyl 500", "Métronidazole", "J01XD01", "comprimé", "500 mg", 1.5, "g", 4.300, True, True),

    # Analgesics / NSAID (N02, M01A)
    ("Doliprane 1000", "Paracétamol", "N02BE01", "comprimé", "1000 mg", 3.0, "g", 2.100, True, False),
    ("Doliprane 500", "Paracétamol", "N02BE01", "comprimé", "500 mg", 3.0, "g", 1.500, True, False),
    ("Efferalgan 500", "Paracétamol", "N02BE01", "comprimé eff.", "500 mg", 3.0, "g", 2.400, True,
     False),
    ("Panadol Sirop", "Paracétamol", "N02BE01", "sirop", "120 mg/5ml", 3.0, "g", 3.200, True, False),
    ("Aspégic 1000", "Acide acétylsalicylique", "N02BA01", "sachet", "1000 mg", 3.0, "g", 2.800,
     False, False),
    ("Brufen 400", "Ibuprofène", "M01AE01", "comprimé", "400 mg", 1.2, "g", 3.600, True, False),
    ("Brufen 600", "Ibuprofène", "M01AE01", "comprimé", "600 mg", 1.2, "g", 4.500, True, False),
    ("Voltarène 50", "Diclofénac", "M01AB05", "comprimé", "50 mg", 0.1, "g", 3.900, False, True),
    ("Feldène 20", "Piroxicam", "M01AC01", "comprimé", "20 mg", 0.02, "g", 5.100, False, True),
    ("Mobic 15", "Méloxicam", "M01AC06", "comprimé", "15 mg", 0.015, "g", 6.200, False, True),

    # Diabetes (A10)
    ("Glucophage 500", "Metformine", "A10BA02", "comprimé", "500 mg", 2.0, "g", 3.400, True, True),
    ("Glucophage 850", "Metformine", "A10BA02", "comprimé", "850 mg", 2.0, "g", 4.100, True, True),
    ("Glucophage 1000", "Metformine", "A10BA02", "comprimé", "1000 mg", 2.0, "g", 5.000, True, True),
    ("Lantus SoloStar", "Insuline glargine", "A10AE04", "stylo", "100 UI/ml", 40.0, "UI", 42.500,
     True, True),
    ("Levemir", "Insuline détémir", "A10AE05", "stylo", "100 UI/ml", 40.0, "UI", 44.000, True, True),
    ("Novorapid", "Insuline asparte", "A10AB05", "stylo", "100 UI/ml", 40.0, "UI", 39.800, True,
     True),
    ("Amarel 2", "Glimépiride", "A10BB12", "comprimé", "2 mg", 0.002, "g", 5.700, False, True),
    ("Diamicron 60", "Gliclazide", "A10BB09", "comprimé LM", "60 mg", 0.06, "g", 7.300, False, True),

    # Cardiovascular (C)
    ("Amlor 5", "Amlodipine", "C08CA01", "comprimé", "5 mg", 0.005, "g", 4.900, True, True),
    ("Amlor 10", "Amlodipine", "C08CA01", "comprimé", "10 mg", 0.005, "g", 6.400, True, True),
    ("Triatec 5", "Ramipril", "C09AA05", "comprimé", "5 mg", 0.0025, "g", 6.800, True, True),
    ("Triatec 10", "Ramipril", "C09AA05", "comprimé", "10 mg", 0.0025, "g", 8.100, True, True),
    ("Rénitec 20", "Énalapril", "C09AA02", "comprimé", "20 mg", 0.01, "g", 5.500, True, True),
    ("Coversyl 5", "Périndopril", "C09AA04", "comprimé", "5 mg", 0.004, "g", 9.200, False, True),
    ("Ténormine 100", "Aténolol", "C07AB03", "comprimé", "100 mg", 0.075, "g", 4.200, True, True),
    ("Sectral 200", "Acébutolol", "C07AB04", "comprimé", "200 mg", 0.4, "g", 5.300, False, True),
    ("Tahor 20", "Atorvastatine", "C10AA05", "comprimé", "20 mg", 0.02, "g", 11.400, False, True),
    ("Tahor 40", "Atorvastatine", "C10AA05", "comprimé", "40 mg", 0.02, "g", 15.900, False, True),
    ("Crestor 10", "Rosuvastatine", "C10AA07", "comprimé", "10 mg", 0.01, "g", 13.200, False, True),
    ("Zocor 20", "Simvastatine", "C10AA01", "comprimé", "20 mg", 0.03, "g", 8.700, False, True),

    # Blood (B01)
    ("Plavix 75", "Clopidogrel", "B01AC04", "comprimé", "75 mg", 0.075, "g", 18.600, True, True),
    ("Kardégic 75", "Acide acétylsalicylique", "B01AC06", "sachet", "75 mg", 1.0, "TU", 3.100,
     True, False),

    # Digestive (A02)
    ("Mopral 20", "Oméprazole", "A02BC01", "gélule", "20 mg", 0.02, "g", 6.900, True, True),
    ("Inexium 40", "Ésoméprazole", "A02BC05", "comprimé", "40 mg", 0.03, "g", 12.500, False, True),
    ("Lanzor 30", "Lansoprazole", "A02BC03", "gélule", "30 mg", 0.03, "g", 8.400, False, True),

    # Respiratory (R)
    ("Ventoline", "Salbutamol", "R03AC02", "aérosol", "100 µg/dose", 0.8, "mg", 7.200, True, True),
    ("Bricanyl", "Terbutaline", "R03AC03", "aérosol", "500 µg/dose", 2.0, "mg", 8.100, False, True),
    ("Séretide 250", "Fluticasone/Salmétérol", "R03AK06", "aérosol", "250/25 µg", 0.6, "mg", 34.700,
     False, True),
    ("Flixotide 250", "Fluticasone", "R03BA05", "aérosol", "250 µg", 0.6, "mg", 22.300, False, True),
    ("Aerius 5", "Desloratadine", "R06AX27", "comprimé", "5 mg", 0.005, "g", 6.600, False, False),
    ("Clarityne 10", "Loratadine", "R06AX13", "comprimé", "10 mg", 0.01, "g", 5.400, False, False),
    ("Zyrtec 10", "Cétirizine", "R06AE07", "comprimé", "10 mg", 0.01, "g", 5.900, False, False),

    # Thyroid (H03)
    ("Lévothyrox 50", "Lévothyroxine", "H03AA01", "comprimé", "50 µg", 0.15, "mg", 3.800, True, True),
    ("Lévothyrox 100", "Lévothyroxine", "H03AA01", "comprimé", "100 µg", 0.15, "mg", 4.200, True,
     True),

    # CNS (N)
    ("Seroplex 10", "Escitalopram", "N06AB10", "comprimé", "10 mg", 0.01, "g", 14.800, False, True),
    ("Deroxat 20", "Paroxétine", "N06AB05", "comprimé", "20 mg", 0.02, "g", 12.100, False, True),
    ("Lexomil 6", "Bromazépam", "N05BA08", "comprimé", "6 mg", 0.01, "g", 3.300, False, True),
    ("Lyrica 75", "Prégabaline", "N03AX16", "gélule", "75 mg", 0.3, "g", 21.500, False, True),
    ("Depakine 500", "Valproate de sodium", "N03AG01", "comprimé", "500 mg", 1.5, "g", 7.800, True,
     True),

    # Corticoids / others
    ("Solupred 20", "Prednisolone", "H02AB06", "comprimé", "20 mg", 0.01, "g", 4.600, True, True),
    ("Célestène", "Bétaméthasone", "H02AB01", "sirop", "0.05%", 0.0015, "g", 5.200, False, True),

    # Essential vaccines-adjacent / emergency
    ("Adrénaline 1mg", "Épinéphrine", "C01CA24", "injectable", "1 mg/ml", 0.5, "mg", 3.900, True,
     True),
    ("Lasilix 40", "Furosémide", "C03CA01", "comprimé", "40 mg", 0.04, "g", 3.100, True, True),
    ("Spasfon", "Phloroglucinol", "A03AX12", "comprimé", "80 mg", 0.24, "g", 4.000, False, False),
    ("Smecta", "Diosmectite", "A07BC05", "sachet", "3 g", 9.0, "g", 5.500, False, False),
]

# ── Suppliers: (name, country, type, reliability, avg_lead_time_days) ──
SUPPLIERS = [
    ("MEDIS", "Tunisie", "local_manufacturer", 0.94, 12),
    ("SAIPH", "Tunisie", "local_manufacturer", 0.92, 14),
    ("Adwya", "Tunisie", "local_manufacturer", 0.90, 15),
    ("Sanofi Aventis", "France", "importer", 0.88, 28),
    ("Novo Nordisk", "Danemark", "importer", 0.85, 35),
    ("Pfizer", "USA", "importer", 0.83, 40),
    ("GSK", "Royaume-Uni", "importer", 0.86, 32),
    ("Hikma", "Jordanie", "importer", 0.89, 22),
]
