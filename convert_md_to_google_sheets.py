
#!/usr/bin/env python3
"""
Convert MASTER_CONTROL_ROOM.md to live Google Sheets with real-time sync
"""

import re
import os
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def parse_markdown_to_sheets_data(md_file: str):
    """Parse markdown file and prepare data for Google Sheets"""
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sheets_data = {}
    
    # Split by main sections (## headers)
    sections = re.split(r'\n## ', content)
    
    # Process each section
    for section in sections[1:]:  # Skip first empty split
        lines = section.split('\n')
        section_title = lines[0].strip()
        section_content = '\n'.join(lines[1:])
        
        # Create safe sheet name (Google Sheets limit: 100 chars)
        sheet_name = section_title[:100].replace('/', '-').replace('\\', '-').replace(':', '-')
        
        sheet_rows = []
        
        # Add section title as header
        sheet_rows.append([section_title])
        sheet_rows.append([])  # Empty row
        
        # Parse subsections
        subsections = re.split(r'\n### ', section_content)
        
        for subsection in subsections:
            if not subsection.strip():
                continue
                
            sub_lines = subsection.split('\n')
            sub_title = sub_lines[0].strip()
            sub_content = '\n'.join(sub_lines[1:])
            
            # Add subsection header
            sheet_rows.append([sub_title])
            
            # Check for tables (markdown tables with | separators)
            table_pattern = r'\|(.+)\|'
            table_matches = re.findall(table_pattern, sub_content, re.MULTILINE)
            
            if table_matches and len(table_matches) > 1:
                # Parse markdown table
                headers = [h.strip() for h in table_matches[0].split('|') if h.strip()]
                sheet_rows.append(headers)
                
                # Skip separator row (---|----|----)
                data_rows = [r for r in table_matches[2:] if not re.match(r'^[-:\s|]+$', r)]
                
                # Write data rows
                for row_data in data_rows:
                    values = [v.strip() for v in row_data.split('|') if v.strip()]
                    sheet_rows.append(values)
                
                sheet_rows.append([])  # Add spacing after table
                
            else:
                # Regular text content
                lines = sub_content.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('│') and not line.startswith('┌'):
                        sheet_rows.append([line])
                
                sheet_rows.append([])  # Add spacing
        
        sheets_data[sheet_name] = sheet_rows
    
    return sheets_data

def create_or_update_google_sheet(sheets_data: dict, spreadsheet_id: str = None):
    """Create or update Google Sheet with parsed data"""
    
    # Use service account credentials from Replit Secrets
    creds = None
    
    # Check if credentials are in environment (Replit Secrets)
    if os.getenv('GOOGLE_SHEETS_CREDENTIALS'):
        import json
        creds_dict = json.loads(os.getenv('GOOGLE_SHEETS_CREDENTIALS'))
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
    else:
        print("⚠️  GOOGLE_SHEETS_CREDENTIALS not found in Replit Secrets")
        print("📋 Setup Instructions:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Google Sheets API")
        print("4. Create Service Account credentials")
        print("5. Download JSON key file")
        print("6. Add the JSON content to Replit Secrets as GOOGLE_SHEETS_CREDENTIALS")
        print("7. Share your Google Sheet with the service account email")
        return None
    
    try:
        service = build('sheets', 'v4', credentials=creds)
        
        # Create new spreadsheet if no ID provided
        if not spreadsheet_id:
            spreadsheet = {
                'properties': {
                    'title': 'MASTER_CONTROL_ROOM - Live Documentation'
                }
            }
            spreadsheet = service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            print(f"✅ Created new Google Sheet: {spreadsheet_id}")
            print(f"🔗 URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        
        # Get existing sheets
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        existing_sheets = {sheet['properties']['title']: sheet['properties']['sheetId'] 
                          for sheet in spreadsheet.get('sheets', [])}
        
        requests = []
        
        # Create new sheets or clear existing ones
        for sheet_name in sheets_data.keys():
            if sheet_name not in existing_sheets:
                # Create new sheet
                requests.append({
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                })
        
        # Execute batch update for new sheets
        if requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
            print(f"✅ Created {len(requests)} new sheets")
        
        # Update data for each sheet
        for sheet_name, rows in sheets_data.items():
            # Clear existing data
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A1:ZZ"
            ).execute()
            
            # Write new data
            body = {
                'values': rows
            }
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A1",
                valueInputOption='RAW',
                body=body
            ).execute()
        
        # Apply formatting
        format_requests = []
        
        # Get updated sheet info
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_id_map = {sheet['properties']['title']: sheet['properties']['sheetId'] 
                       for sheet in spreadsheet.get('sheets', [])}
        
        for sheet_name in sheets_data.keys():
            sheet_id = sheet_id_map[sheet_name]
            
            # Format header row (row 0)
            format_requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.2, 'green': 0.38, 'blue': 0.57},
                            'textFormat': {
                                'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                                'fontSize': 16,
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            })
            
            # Auto-resize columns
            format_requests.append({
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 26
                    }
                }
            })
        
        # Apply formatting
        if format_requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': format_requests}
            ).execute()
        
        print(f"✅ Updated {len(sheets_data)} sheets with formatting")
        print(f"🔗 Live Google Sheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        
        # Save spreadsheet ID for future updates
        with open('.google_sheet_id', 'w') as f:
            f.write(spreadsheet_id)
        
        return spreadsheet_id
        
    except HttpError as error:
        print(f"❌ An error occurred: {error}")
        return None

def auto_sync_on_changes():
    """Watch for changes to MASTER_CONTROL_ROOM.md and auto-sync"""
    import time
    from pathlib import Path
    
    md_file = "MASTER_CONTROL_ROOM.md"
    last_modified = os.path.getmtime(md_file) if os.path.exists(md_file) else 0
    
    # Get saved spreadsheet ID
    spreadsheet_id = None
    if os.path.exists('.google_sheet_id'):
        with open('.google_sheet_id', 'r') as f:
            spreadsheet_id = f.read().strip()
    
    print("🔄 Auto-sync enabled - watching for changes...")
    print(f"📄 Monitoring: {md_file}")
    
    while True:
        try:
            if os.path.exists(md_file):
                current_modified = os.path.getmtime(md_file)
                
                if current_modified > last_modified:
                    print(f"\n🔔 Change detected at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print("⚡ Syncing to Google Sheets...")
                    
                    sheets_data = parse_markdown_to_sheets_data(md_file)
                    new_id = create_or_update_google_sheet(sheets_data, spreadsheet_id)
                    
                    if new_id:
                        spreadsheet_id = new_id
                        last_modified = current_modified
                        print("✅ Sync complete!")
                    
            time.sleep(5)  # Check every 5 seconds
            
        except KeyboardInterrupt:
            print("\n⏹️  Auto-sync stopped")
            break
        except Exception as e:
            print(f"⚠️  Error during sync: {e}")
            time.sleep(5)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--watch':
        # Auto-sync mode
        auto_sync_on_changes()
    else:
        # One-time sync
        print("🔄 Converting MASTER_CONTROL_ROOM.md to Google Sheets...")
        sheets_data = parse_markdown_to_sheets_data("MASTER_CONTROL_ROOM.md")
        
        # Check for existing spreadsheet ID
        spreadsheet_id = None
        if os.path.exists('.google_sheet_id'):
            with open('.google_sheet_id', 'r') as f:
                spreadsheet_id = f.read().strip()
        
        create_or_update_google_sheet(sheets_data, spreadsheet_id)
        print("\n💡 Tip: Run with --watch flag to enable auto-sync on file changes")
