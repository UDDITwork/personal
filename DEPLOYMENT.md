# 🚀 DEPLOYMENT GUIDE - PATMASTER Extraction Pipeline

## Quick Start Deployment Options

### 1. 🌩️ Render (Easiest - Recommended for Beginners)

**Pros:** Free tier available, auto-scaling, managed Redis, zero config
**Time:** ~10 minutes

#### Steps:

1. **Push code to GitHub:**
   ```bash
   cd patmaster-extraction
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy to Render:**
   - Go to [render.com](https://render.com)
   - Click "New" → "Blueprint"
   - Connect your GitHub repo
   - Render will auto-detect `render.yaml` and deploy all services
   - Add your API keys in the Render dashboard:
     - `LLAMA_CLOUD_API_KEY`
     - `GEMINI_API_KEY`

3. **Access your API:**
   - Render will provide a URL like: `https://patmaster-extraction-api.onrender.com`
   - API docs: `https://your-url.onrender.com/docs`

**Cost:** Free tier available, paid plans start at $7/month

---

### 2. ☁️ Google Cloud Run (Best for Scale)

**Pros:** Auto-scaling to 10,000+ users, pay-per-use, enterprise-grade
**Time:** ~15 minutes

#### Steps:

1. **Install Google Cloud SDK:**
   ```bash
   # Follow: https://cloud.google.com/sdk/docs/install
   gcloud init
   ```

2. **Set project:**
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Build and deploy:**
   ```bash
   cd patmaster-extraction

   # Build container
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/patmaster-extraction

   # Deploy to Cloud Run
   gcloud run deploy patmaster-extraction \
     --image gcr.io/YOUR_PROJECT_ID/patmaster-extraction \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 4Gi \
     --cpu 2 \
     --timeout 600 \
     --max-instances 100 \
     --set-env-vars LLAMA_CLOUD_API_KEY=your_key,GEMINI_API_KEY=your_key,REDIS_URL=redis://your-redis-ip:6379
   ```

4. **Setup Redis (Cloud Memorystore):**
   ```bash
   gcloud redis instances create patmaster-redis \
     --size=1 \
     --region=us-central1
   ```

**Cost:** Pay per request, ~$0.0000024 per request, first 2 million free

---

### 3. 🟣 Heroku (Simple & Fast)

**Pros:** Simple, one-command deploy, built-in Redis
**Time:** ~5 minutes

#### Steps:

1. **Install Heroku CLI:**
   ```bash
   # Download from: https://devcenter.heroku.com/articles/heroku-cli
   heroku login
   ```

2. **Create app and deploy:**
   ```bash
   cd patmaster-extraction

   # Create app
   heroku create patmaster-extraction

   # Add Redis
   heroku addons:create heroku-redis:premium-0

   # Set environment variables
   heroku config:set LLAMA_CLOUD_API_KEY=your_key
   heroku config:set GEMINI_API_KEY=your_key

   # Deploy
   git init
   git add .
   git commit -m "Initial commit"
   git push heroku main

   # Scale workers
   heroku ps:scale web=1 worker=2
   ```

3. **View logs:**
   ```bash
   heroku logs --tail
   ```

**Cost:** Free tier discontinued, starts at $7/month

---

### 4. 🔶 AWS EC2 (Full Control)

**Pros:** Complete control, custom configuration, VPC networking
**Time:** ~30 minutes

#### Steps:

1. **Launch EC2 Instance:**
   - Instance Type: `t3.xlarge` (4 vCPU, 16 GB RAM)
   - AMI: Ubuntu 22.04 LTS
   - Storage: 50 GB SSD
   - Security Group: Allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)

2. **SSH into instance:**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

3. **Setup application:**
   ```bash
   # Update system
   sudo apt-get update && sudo apt-get upgrade -y

   # Install dependencies
   sudo apt-get install -y python3.11 python3.11-venv python3-pip redis-server nginx supervisor git

   # Clone code
   git clone YOUR_REPO_URL
   cd patmaster-extraction

   # Create virtual environment
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Setup .env
   cp .env.example .env
   nano .env  # Add your API keys
   ```

4. **Setup Supervisor:**
   ```bash
   sudo nano /etc/supervisor/conf.d/patmaster.conf
   ```

   Paste:
   ```ini
   [program:redis]
   command=redis-server
   autostart=true
   autorestart=true

   [program:celery]
   command=/home/ubuntu/patmaster-extraction/venv/bin/celery -A workers.celery_app worker --loglevel=info --concurrency=10
   directory=/home/ubuntu/patmaster-extraction
   user=ubuntu
   autostart=true
   autorestart=true

   [program:fastapi]
   command=/home/ubuntu/patmaster-extraction/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   directory=/home/ubuntu/patmaster-extraction
   user=ubuntu
   autostart=true
   autorestart=true
   ```

   Start services:
   ```bash
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl status
   ```

5. **Setup Nginx:**
   ```bash
   sudo nano /etc/nginx/sites-available/patmaster
   ```

   Paste:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           client_max_body_size 100M;
           proxy_read_timeout 600s;
       }
   }
   ```

   Enable and restart:
   ```bash
   sudo ln -s /etc/nginx/sites-available/patmaster /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

6. **Setup SSL (Optional but recommended):**
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

**Cost:** ~$50-100/month for t3.xlarge

---

### 5. 🟠 DigitalOcean App Platform (Balanced)

**Pros:** Balance of simplicity and control, good pricing
**Time:** ~10 minutes

#### Steps:

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click "Create App" → Connect GitHub
3. Select `patmaster-extraction` repo
4. Configure:
   - **Type:** Web Service
   - **Build Command:** `pip install -r requirements.txt`
   - **Run Command:** `./start.sh`
   - **Environment Variables:** Add API keys
5. Add Redis database from DigitalOcean marketplace
6. Deploy!

**Cost:** ~$12/month for basic tier

---

## 🖥️ FRONTEND DEPLOYMENT

### Option 1: Vercel (Next.js/React)

1. **Create frontend:**
   ```bash
   npx create-next-app@latest patmaster-frontend
   cd patmaster-frontend
   ```

2. **Create upload page** (`app/page.tsx`):
   ```typescript
   'use client';
   import { useState } from 'react';

   export default function Home() {
     const [file, setFile] = useState<File | null>(null);
     const [result, setResult] = useState<any>(null);
     const [loading, setLoading] = useState(false);

     const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

     const handleUpload = async () => {
       if (!file) return;
       setLoading(true);

       const formData = new FormData();
       formData.append('file', file);

       const userId = 'user123'; // Replace with real user ID
       const sessionId = Date.now().toString();

       try {
         const endpoint = file.name.endsWith('.pdf')
           ? 'upload_idf_pdf'
           : 'upload_idf_transcription';

         const response = await fetch(
           `${API_URL}/api/v1/${userId}/${sessionId}/${endpoint}`,
           { method: 'POST', body: formData }
         );

         const uploadResult = await response.json();

         // Get extraction result
         const resultResponse = await fetch(
           `${API_URL}/api/v1/${userId}/${sessionId}/extraction_result`
         );
         const extractionResult = await resultResponse.json();

         setResult(extractionResult);
       } catch (error) {
         console.error('Upload failed:', error);
       } finally {
         setLoading(false);
       }
     };

     return (
       <div style={{ padding: '2rem' }}>
         <h1>PATMASTER Document Extraction</h1>
         <input
           type="file"
           accept=".pdf,.docx"
           onChange={(e) => setFile(e.target.files?.[0] || null)}
         />
         <button onClick={handleUpload} disabled={!file || loading}>
           {loading ? 'Extracting...' : 'Upload & Extract'}
         </button>

         {result && (
           <div style={{ marginTop: '2rem' }}>
             <h2>Extraction Result</h2>
             <p>Pages: {result.total_pages}</p>
             <p>Images: {result.extracted_images?.length || 0}</p>
             <p>Tables: {result.extracted_tables?.length || 0}</p>
             <pre>{JSON.stringify(result, null, 2)}</pre>
           </div>
         )}
       </div>
     );
   }
   ```

3. **Deploy to Vercel:**
   ```bash
   npm install -g vercel
   vercel
   ```

   Set environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.com
   ```

### Option 2: Netlify (Static HTML)

1. **Create simple HTML frontend** (`frontend/index.html`):
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <title>PATMASTER Extraction</title>
       <style>
           body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
           .upload-box { border: 2px dashed #ccc; padding: 40px; text-align: center; }
           button { background: #667eea; color: white; border: none; padding: 10px 20px; cursor: pointer; }
       </style>
   </head>
   <body>
       <h1>PATMASTER Document Extraction</h1>
       <div class="upload-box">
           <input type="file" id="fileInput" accept=".pdf,.docx">
           <br><br>
           <button onclick="upload()">Extract Document</button>
       </div>
       <div id="result"></div>

       <script>
           const API_URL = 'https://your-backend-url.com';

           async function upload() {
               const file = document.getElementById('fileInput').files[0];
               if (!file) return alert('Please select a file');

               const formData = new FormData();
               formData.append('file', file);

               const userId = 'user123';
               const sessionId = Date.now();
               const endpoint = file.name.endsWith('.pdf') ? 'upload_idf_pdf' : 'upload_idf_transcription';

               try {
                   const response = await fetch(`${API_URL}/api/v1/${userId}/${sessionId}/${endpoint}`, {
                       method: 'POST',
                       body: formData
                   });

                   const result = await response.json();
                   document.getElementById('result').innerHTML = '<h2>Success!</h2><pre>' + JSON.stringify(result, null, 2) + '</pre>';
               } catch (error) {
                   alert('Upload failed: ' + error.message);
               }
           }
       </script>
   </body>
   </html>
   ```

2. **Deploy to Netlify:**
   ```bash
   npm install -g netlify-cli
   netlify deploy --prod --dir=frontend
   ```

---

## 🔍 TESTING YOUR DEPLOYMENT

After deployment, test with:

```bash
# Health check
curl https://your-backend-url.com/health

# Upload PDF
curl -X POST "https://your-backend-url.com/api/v1/test/session1/upload_idf_pdf" \
  -F "file=@sample.pdf"

# View result
curl "https://your-backend-url.com/api/v1/test/session1/extraction_result"
```

---

## 📊 RECOMMENDED SETUP FOR PRODUCTION

**Backend:** Google Cloud Run or AWS EC2
**Redis:** Cloud Memorystore (GCP) or ElastiCache (AWS)
**Frontend:** Vercel (Next.js)
**Monitoring:** Sentry + Google Cloud Logging
**CDN:** Cloudflare

**Total Cost:** ~$50-150/month for moderate traffic

---

## 🆘 SUPPORT

For deployment issues:
1. Check logs: `heroku logs --tail` or `gcloud run logs read`
2. Verify environment variables are set
3. Test API keys separately
4. Check Redis connection: `redis-cli ping`

Need help? Open an issue on GitHub or email support@patmaster.com
