def build_messages(context: str, question: str) -> list[dict]:
    """Builds the message array for the LLM"""
    return [
        {
            "role"   : "system",
            "content": (
                "You are a helpful assistant. "
                "Answer the question using ONLY the context provided below. "
                "If the answer is not in the context, say "
                "'I don't have enough information to answer this.' "
                "Be concise and accurate."
            ),
        },
        {
            "role"   : "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}",
        },
    ]