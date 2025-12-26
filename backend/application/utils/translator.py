from deep_translator import GoogleTranslator
import time
import logging

logger = logging.getLogger(__name__)

def translate_text(text, target_lang="mr", retries=3):
    if not text:
        return None, False

    for attempt in range(retries):
        try:
            translator = GoogleTranslator(source="auto", target=target_lang)
            translated = translator.translate(text)
            return translated, True

        except Exception as e:
            logger.error(f"Translation failed (attempt {attempt+1}): {e}")
            time.sleep(2)

    return None, False
