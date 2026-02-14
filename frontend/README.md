# PATMASTER Frontend - Document Extraction UI

Simple, beautiful frontend for the PATMASTER document extraction pipeline.

## 🚀 Quick Deploy

### Deploy to Netlify (Easiest)

1. **Install Netlify CLI:**
   ```bash
   npm install -g netlify-cli
   ```

2. **Deploy:**
   ```bash
   cd frontend
   netlify deploy --prod
   ```

3. **Update API URL:**
   - After deploying backend, update the default API URL in `index.html`
   - Or users can enter it in the UI

### Deploy to Vercel

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Deploy:**
   ```bash
   cd frontend
   vercel
   ```

### Deploy to GitHub Pages

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Frontend"
   git branch -M main
   git remote add origin YOUR_REPO_URL
   git push -u origin main
   ```

2. **Enable GitHub Pages:**
   - Go to repo Settings → Pages
   - Source: Deploy from branch
   - Branch: main
   - Folder: /frontend
   - Save

3. **Access:** `https://yourusername.github.io/repo-name/`

## 🖥️ Local Development

Simply open `index.html` in your browser:

```bash
# Windows
start index.html

# Mac
open index.html

# Linux
xdg-open index.html
```

Or use a simple HTTP server:

```bash
python -m http.server 8080
# Visit http://localhost:8080
```

## ⚙️ Configuration

Update the default API URL in the input field or edit line 245 in `index.html`:

```javascript
<input type="text" id="apiUrl" value="https://your-backend-api.com">
```

## 🎨 Features

- ✅ Drag & drop file upload
- ✅ Real-time progress tracking
- ✅ Beautiful result display
- ✅ View full results in new tab
- ✅ Download JSON results
- ✅ Mobile responsive
- ✅ Works with any backend URL

## 📱 Mobile Support

Fully responsive and works on mobile devices.

## 🔗 Connecting to Backend

Make sure your backend has CORS enabled (already configured in `main.py`).

## 🆘 Troubleshooting

**CORS Error:** Ensure backend CORS settings allow your frontend domain

**Connection Refused:** Check backend URL is correct and API is running

**Upload Fails:** Check file size (max 100MB) and format (PDF/DOCX only)
