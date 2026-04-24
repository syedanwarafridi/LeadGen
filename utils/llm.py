"""
Returns the best available free LLM.
Priority: Groq (fastest) → Google Gemini Flash (1M free tokens/month)
"""
import os
from langchain_core.language_models import BaseChatModel


def get_llm(temperature: float = 0.0, max_tokens: int = 2048) -> BaseChatModel:
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if groq_key:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=groq_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    raise ValueError(
        "\n[ERROR] No free LLM key found. Add one of these to your .env file:\n"
        "  GROQ_API_KEY   — free at https://console.groq.com  (recommended)\n"
        "  GEMINI_API_KEY — free at https://aistudio.google.com\n"
    )
