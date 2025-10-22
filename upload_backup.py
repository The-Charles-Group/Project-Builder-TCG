
import requests
from replit.object_storage import Client

# Download the ZIP file from your cloud storage
print("Downloading backup ZIP...")
url = "YOUR_DOWNLOAD_URL"  # Replace with actual URL
response = requests.get(url, stream=True)

# Upload to Object Storage
print("Uploading to Object Storage...")
client = Client()
client.upload_from_bytes("backup-oct16.zip", response.content)
print("✅ Backup uploaded successfully!")
