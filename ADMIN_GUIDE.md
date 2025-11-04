# Admin Authentication Guide

## Overview
The Learning Brain feature requires admin authentication to ensure secure management of the AI learning system.

## Default Admin Token
**Development Token**: `dev_token_f4SFYeTc4Xorv2Gu7nkG-PSG0wgKcyZt`

This token is automatically generated when no ADMIN_TOKEN environment variable is set.

## How to Authenticate

### First-Time Authentication
1. Click the **"Learn"** button after selecting deliverables
2. Enter the admin token when prompted
3. The token will be saved locally for future sessions

### Visual Indicators
- **🔐 Admin Mode** badge appears in the top-right corner when authenticated
- Click the badge to log out

### Authentication Persistence
- The token is stored in browser localStorage
- You remain authenticated across browser refreshes
- Clear browser data or click the Admin Mode badge to log out

## Setting a Custom Token

### Environment Variable Method
To use a custom admin token, set the `ADMIN_TOKEN` environment variable:

```bash
export ADMIN_TOKEN="your-secure-token-here"
```

Then restart the FastAPI server.

### Security Best Practices
1. **Production Environment**: Always set a strong, unique ADMIN_TOKEN
2. **Token Complexity**: Use at least 32 characters with mixed alphanumeric
3. **Token Rotation**: Change the token periodically
4. **Access Control**: Limit token distribution to authorized administrators only

## Features Protected by Admin Authentication

### Learning Brain Operations
- **Learn from RFP selections** - Train the AI on deliverable selections
- **Change operating mode** - Switch between learning, calibration, and inference modes
- **Adjust confidence scores** - Fine-tune AI confidence for specific deliverables
- **View audit logs** - Track all admin actions and changes
- **Export brain state** - Backup the complete learning state

### API Endpoints
All `/api/brain/*` endpoints require admin authentication:
- `POST /api/brain/learn` - Submit learning data
- `POST /api/brain/mode` - Change operating mode
- `POST /api/brain/feedback` - Submit confidence adjustments
- `GET /api/brain/audit` - View audit logs
- `GET /api/brain/export` - Export brain state

## Troubleshooting

### "Admin token not configured" Error
- Ensure the server has started and loaded the default token
- Check server logs for the generated token

### "Invalid admin token" Error
- Verify you're using the correct token
- Check for extra spaces when copying/pasting
- Ensure the token matches what's configured on the server

### Lost Admin Access
1. Check server logs for the current token
2. Clear browser localStorage to reset authentication
3. Re-enter the correct token when prompted

## Admin Panel Access
Visit `/admin/brain` to access the Learning Brain admin interface (requires authentication).