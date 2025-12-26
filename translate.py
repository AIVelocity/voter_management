import pandas as pd
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Load only required column (memory efficient)
df = pd.read_excel(
    r"C:\Users\Nikhil Kanojiya\Downloads\Merge_extracted_Final_ward_37 1.xlsx",
    usecols=["voter_name_marathi"]
)

def marathi_to_english(text):
    if not isinstance(text, str) or not text.strip():
        return ""
    return transliterate(text.strip(), sanscript.DEVANAGARI, sanscript.HK)

# Fast apply (80k is totally fine)
df["name_english_1"] = df["voter_name_marathi"].apply(marathi_to_english)

# Save result
df.to_excel("converted_names.xlsx", index=False)

print("✅ 80,000 names converted successfully")
