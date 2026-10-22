# MailQR — Flask Email QR Generator

## Features
- To, CC, BCC, Subject, Body
- QR code generation and PNG download
- Shareable page URL that restores entered fields
- Android Gmail intent link and standard `mailto:` fallback
- Optional file picker (attachments still need to be added manually in Gmail)

This site does not send emails or store submitted form data.

## Important limitations
- A browser/QR scanner cannot guarantee Gmail opens as the app on every phone. Android settings, scanner behavior, and Gmail installation affect this.
- The QR uses a standard `mailto:` URI for broad compatibility; the separate Gmail button uses an Android intent.
- Files cannot be silently attached to Gmail through a normal QR/link. Users must attach them manually after Gmail opens.
- Share URLs contain To/CC/BCC, subject and body as URL parameters. Anyone with the URL can read those details; do not share confidential content.
- The QR library is loaded from a CDN, so internet is required to generate QR codes.

## Files
```text
MailQR_Flask_Project/
├── app.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── .gitignore
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── app.js
    └── style.css
```

## Run on Windows in VS Code
```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Push to GitHub
Create a repository, then run from this folder:
```bash
git init
git add .
git commit -m "Initial MailQR app"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

## Hosting
GitHub Pages cannot run Flask. Connect the GitHub repository to a Python host such as Render:
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

Check the host's current plan and deployment instructions before publishing.


## Link-open analytics

The dashboard counts visits to generated share links (URLs containing email fields), not ordinary homepage visits. It shows total link opens and unique browser visitors. A random, HTTP-only cookie is used to recognize a browser; the app does not store IP addresses. People who clear cookies or use another browser/device can be counted as new visitors. These numbers do **not** mean emails were sent. For production hosting, configure a persistent disk/volume for `mailqr_stats.sqlite3` so stats survive redeploys.
