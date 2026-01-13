# Code Signing Setup Guide

This guide explains how to set up code signing for ScoreForge releases.

## macOS Code Signing & Notarization

### Prerequisites

1. **Apple Developer Account** ($99/year): https://developer.apple.com
2. **Developer ID Application Certificate** (for distributing outside App Store)
3. **App-specific password** for notarization

### Step 1: Create Developer ID Certificate

1. Open **Keychain Access** on your Mac
2. Go to **Keychain Access → Certificate Assistant → Request a Certificate from a Certificate Authority**
3. Enter your email and select "Saved to disk"
4. Go to https://developer.apple.com/account/resources/certificates/list
5. Click **+** to create a new certificate
6. Select **Developer ID Application**
7. Upload your certificate signing request
8. Download and double-click to install the certificate

### Step 2: Export Certificate for GitHub Actions

1. Open **Keychain Access**
2. Find your "Developer ID Application" certificate
3. Right-click → **Export** → Save as `.p12` file
4. Set a strong password (you'll need this for GitHub Secrets)
5. Base64 encode the certificate:
   ```bash
   base64 -i Certificates.p12 -o Certificates.base64.txt
   ```

### Step 3: Create App-Specific Password for Notarization

1. Go to https://appleid.apple.com/account/manage
2. Sign in with your Apple ID
3. Under **Security**, click **App-Specific Passwords**
4. Click **+** to generate a new password
5. Name it "ScoreForge Notarization"
6. Copy the generated password

### Step 4: Get Your Team ID

1. Go to https://developer.apple.com/account
2. Click **Membership** in the sidebar
3. Copy your **Team ID** (10-character alphanumeric)

### Step 5: Add GitHub Secrets

Go to your repository: **Settings → Secrets and variables → Actions**

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `APPLE_CERTIFICATE_BASE64` | Contents of `Certificates.base64.txt` |
| `APPLE_CERTIFICATE_PASSWORD` | Password you set when exporting .p12 |
| `APPLE_ID` | Your Apple ID email |
| `APPLE_ID_PASSWORD` | App-specific password from Step 3 |
| `APPLE_TEAM_ID` | Your Team ID from Step 4 |

### Step 6: Test Locally (Optional)

```bash
# Sign the app
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAMID)" \
  --options runtime \
  dist/ScoreForge.app

# Create DMG
hdiutil create -volname "ScoreForge" -srcfolder dist/dmg -ov -format UDZO dist/ScoreForge.dmg

# Sign the DMG
codesign --sign "Developer ID Application: Your Name (TEAMID)" dist/ScoreForge.dmg

# Submit for notarization
xcrun notarytool submit dist/ScoreForge.dmg \
  --apple-id "your@email.com" \
  --password "app-specific-password" \
  --team-id "TEAMID" \
  --wait

# Staple the notarization ticket
xcrun stapler staple dist/ScoreForge.dmg
```

---

## Windows Code Signing (Optional)

For Windows, you need an EV Code Signing Certificate. Options:

### Cloud-Based Signing (Recommended)
- **SignPath.io** - Free for open source
- **Azure Trusted Signing** - Pay-per-use

### Traditional Certificate
- **DigiCert**, **Sectigo**, **GlobalSign** - $200-500/year
- Requires hardware token for EV certificates

For now, Windows builds will work without signing but may show SmartScreen warnings on first run.

---

## Linux

Linux doesn't require code signing. The tarball/AppImage works as-is.

---

## Verification

After a signed release:

```bash
# Verify macOS signature
codesign --verify --deep --strict --verbose=2 /Applications/ScoreForge.app

# Verify notarization
spctl --assess --type execute --verbose /Applications/ScoreForge.app
```

You should see: `accepted` and `source=Notarized Developer ID`
