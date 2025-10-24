
# Google Sheets Live Documentation Setup

This guide will help you set up live Google Sheets integration for your MASTER_CONTROL_ROOM.md file.

## Setup Steps

### 1. Create Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Sheets API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

### 2. Create Service Account Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Fill in the service account details and click "Create"
4. Skip the optional steps and click "Done"
5. Click on the created service account
6. Go to "Keys" tab → "Add Key" → "Create New Key"
7. Select "JSON" and click "Create"
8. Save the downloaded JSON file

### 3. Add Credentials to Replit Secrets

1. In your Replit workspace, open the **Secrets** tool (🔐 in the Tools panel)
2. Create a new secret:
   - **Key**: `GOOGLE_SHEETS_CREDENTIALS`
   - **Value**: Paste the entire contents of your downloaded JSON file
3. Click "Add Secret"

### 4. Run the Sync

One-time sync:
```bash
python convert_md_to_google_sheets.py
```

Auto-sync mode (watches for file changes):
```bash
python convert_md_to_google_sheets.py --watch
```

### 5. Share the Google Sheet

After the first run, you'll get a Google Sheet URL. To make it accessible:

1. Open the Google Sheet using the provided URL
2. Click "Share" in the top-right
3. Add the service account email (found in your JSON credentials as `client_email`)
4. Give it "Editor" permissions
5. Now the script can update it automatically!

## Features

✅ **Live Updates**: Automatically syncs when MASTER_CONTROL_ROOM.md changes  
✅ **Multi-Sheet Organization**: Each section becomes a separate sheet  
✅ **Table Formatting**: Markdown tables are preserved  
✅ **Professional Styling**: Automatic header formatting and column sizing  
✅ **Persistent ID**: Reuses the same spreadsheet for updates  

## Usage

### Manual Sync
```bash
python convert_md_to_google_sheets.py
```

### Auto-Sync (Recommended)
```bash
python convert_md_to_google_sheets.py --watch
```

This will run in the background and automatically sync any changes to your Google Sheet every 5 seconds.

## Troubleshooting

**"GOOGLE_SHEETS_CREDENTIALS not found"**
- Make sure you added the secret in Replit Secrets tool
- Verify the key name is exactly: `GOOGLE_SHEETS_CREDENTIALS`

**"Permission denied" error**
- Make sure you shared the Google Sheet with your service account email
- The email looks like: `your-service-account@your-project.iam.gserviceaccount.com`

**Sheet not updating**
- Check that the `.google_sheet_id` file exists with your spreadsheet ID
- Verify the service account has "Editor" permissions on the sheet

## Integration with Workflows

You can run auto-sync as a background workflow. The script will keep your Google Sheet updated automatically whenever the markdown file changes.
