import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not all([BOT_TOKEN, API_ID, API_HASH]):
    print("\n" + "="*50)
    print("❌ ERROR: Missing environment variables!")
    print("="*50)
    if not BOT_TOKEN:
        print("  - BOT_TOKEN is missing")
    if not API_ID:
        print("  - API_ID is missing")
    if not API_HASH:
        print("  - API_HASH is missing")
    print("="*50 + "\n")
    exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    print("\n❌ ERROR: API_ID must be a number!\n")
    exit(1)

print("\n" + "="*50)
print("✅ All environment variables loaded successfully!")
print("="*50 + "\n")
