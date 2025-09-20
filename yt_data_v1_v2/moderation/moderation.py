KUFUR_LISTESI = ["küfür1", "küfür2", "örnek"]

def analyze_text(text: str) -> dict:
    """Metni analiz et: küfür, saldırganlık, hedef tipi"""
    score = 0
    text_lower = text.lower()
    for kelime in KUFUR_LISTESI:
        if kelime in text_lower:
            score += 1

    risk = "negatif" if score > 2 else "orta" if score == 1 else "pozitif"

    # Örnek etiketler (gerçek ML model ile değiştirilebilir)
    tags = {
        "saldırganlık": score > 1,
        "hakaret": score > 0,
        "hedef_tipi": "birey" if score > 0 else "yok"
    }

    return {"risk_score": risk, "tags": tags}
