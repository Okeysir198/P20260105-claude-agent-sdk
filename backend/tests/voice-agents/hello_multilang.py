#!/usr/bin/env python3
"""
Multi-language Hello World
A simple script that prints "Hello" in multiple languages.
"""

def say_hello(language: str = "all") -> None:
    """
    Print hello in various languages.

    Args:
        language: Specific language code or 'all' for all languages
    """
    greetings = {
        "en": "Hello",
        "es": "Hola",
        "fr": "Bonjour",
        "de": "Hallo",
        "it": "Ciao",
        "pt": "Olá",
        "ru": "Привет (Privet)",
        "zh": "你好 (Nǐ hǎo)",
        "ja": "こんにちは (Konnichiwa)",
        "ko": "안녕하세요 (Annyeonghaseyo)",
        "ar": "مرحبا (Marhaba)",
        "hi": "नमस्ते (Namaste)",
        "sv": "Hej",
        "nl": "Hallo",
        "pl": "Cześć",
        "tr": "Merhaba",
        "vi": "Xin chào",
        "th": "สวัสดี (Sawasdee)",
        "el": "Γεια σου (Yia sou)",
        "he": "שלום (Shalom)",
    }

    if language.lower() == "all":
        print("Hello in multiple languages:\n")
        for code, greeting in greetings.items():
            print(f"{code:3s}: {greeting}")
    else:
        if language in greetings:
            print(f"{greetings[language]}!")
        else:
            print(f"Language '{language}' not found. Available: {', '.join(greetings.keys())}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Say hello in multiple languages")
    parser.add_argument(
        "-l", "--lang",
        default="all",
        help="Specific language code (e.g., en, es, fr, zh, ja) or 'all' for all languages"
    )

    args = parser.parse_args()
    say_hello(args.lang)
