def query_model_stub(text: str) -> str:
    """Gerçek model yerine stub dönüş"""
    return f"[STUB] Bu metin için model cevabı hazırlanacak: {text[:50]}..."
