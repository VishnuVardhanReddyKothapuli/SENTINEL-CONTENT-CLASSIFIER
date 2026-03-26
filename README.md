# NSFWGuard — NSFW Content Classifier & Blur Tool

A full-stack web app that classifies images and videos as **Safe / Suggestive / NSFW** and optionally **blurs explicit regions** automatically. Built with FastAPI, MySQL, NudeNet, and Python.

---

## What it does

- **Classifier mode** — Upload an image, video, or paste a YouTube URL. Get a label (Safe / Suggestive / NSFW) plus a confidence score and per-category breakdown.
- **Classifier + Blur mode** — Same as above, but NSFW regions are automatically blurred (Gaussian blur, frame-by-frame for videos). 90%+ accuracy.
- **Green indicator** — Processed/safe media gets a green border. Suggestive = yellow, NSFW = red.
- **Upload links** — After classification, if the content is safe or has been blurred, one-click links to YouTube Studio, Instagram, Reddit, Discord, TikTok, and Twitter are shown.
- **Auth** — Email/password signup + Google Sign-In. All connected to MySQL.

---

## Project Structure

```
nsfw_classifier/
├── app/
│   ├── main.py             # FastAPI app, middleware, router registration
│   ├── database.py         # SQLAlchemy engine + session
│   ├── models.py           # User and ClassificationResult DB models
│   ├── classifier.py       # NudeNet wrapper — classify + blur images/videos
│   ├── auth_utils.py       # Password hashing, JWT, Google OAuth helpers
│   ├── routers/
│   │   ├── home.py         # Landing page
│   │   ├── auth.py         # Login, signup, logout, Google OAuth callback
│   │   └── classify.py     # /classify/run, /classify/blur, /classify/youtube
│   ├── templates/
│   │   ├── base.html       # Shared layout (navbar, fonts, footer)
│   │   ├── home.html       # Landing page with tutorial YT embed
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── signup.html
│   │   └── classify/
│   │       └── lab.html    # The main classifying lab UI
│   └── static/
│       ├── css/
│       │   ├── main.css    # Global styles
│       │   └── lab.css     # Lab page styles
│       ├── js/
│       │   ├── main.js     # Global JS (placeholder)
│       │   └── lab.js      # Lab page — drag+drop, API calls, results render
│       ├── img/
│       │   └── google-icon.svg
│       └── uploads/        # Where uploaded/processed files are saved
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run.py                  # Local dev server
├── .env.example            # Copy to .env and fill in
└── .gitignore
```

---

## Setup — Option A: Docker (recommended, easiest)

### Step 1 — Clone the repo

```bash
git clone https://github.com/yourname/nsfw-classifier.git
cd nsfw-classifier
```

### Step 2 — Set up your environment file

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
SECRET_KEY=some-long-random-string
MYSQL_USER=nsfw_user
MYSQL_PASSWORD=pick_a_strong_password
MYSQL_HOST=db
MYSQL_DB=nsfw_classifier
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

Also update `docker-compose.yml` line `MYSQL_PASSWORD:` to match the password you chose above.

### Step 3 — Build and start

```bash
docker compose up --build
```

That's it. Open http://localhost:8000 in your browser.

To run in background: `docker compose up --build -d`

To stop: `docker compose down`

---

## Setup — Option B: Local Python (without Docker)

### Step 1 — Prerequisites

- Python 3.10 or 3.11
- MySQL 8.0 running locally
- `ffmpeg` installed (needed by yt-dlp for video handling)

On Ubuntu/Debian:
```bash
sudo apt install ffmpeg
```

On Mac:
```bash
brew install ffmpeg
```

### Step 2 — Create MySQL database

Log in to MySQL:
```bash
mysql -u root -p
```

Run these SQL commands:
```sql
CREATE DATABASE nsfw_classifier CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'nsfw_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON nsfw_classifier.* TO 'nsfw_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 3 — Clone the repo

```bash
git clone https://github.com/yourname/nsfw-classifier.git
cd nsfw-classifier
```

### Step 4 — Create a virtual environment

```bash
python -m venv venv

# On Mac/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 5 — Install dependencies

```bash
pip install -r requirements.txt
```

> NudeNet will automatically download its model (~90 MB) on the first classification run.

### Step 6 — Set up your .env

```bash
cp .env.example .env
```

Edit `.env` — set `MYSQL_HOST=localhost` and fill in all other values.

### Step 7 — Run the app

```bash
python run.py
```

Open http://localhost:8000

---

## Setting up Google Sign-In

1. Go to https://console.cloud.google.com/
2. Create a new project (or select an existing one)
3. Go to **APIs & Services → OAuth consent screen**
   - Set User Type to **External**
   - Fill in App name, support email
   - Add your email under Test users
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Authorized redirect URIs: `http://localhost:8000/auth/google/callback`
5. Copy the **Client ID** and **Client Secret** into your `.env`

When you deploy to production, add your production URL to the authorized redirect URIs and update `GOOGLE_REDIRECT_URI` in `.env`.

---

## How the NSFW classifier works

The classifier uses **NudeNet** — a purpose-built neural network for detecting explicit body parts in images and videos.

**Classification tiers:**

| Label | Meaning |
|---|---|
| ✅ Safe | No sensitive body parts detected above threshold |
| ⚠️ Suggestive | Exposed non-explicit regions (belly, armpits, etc.) |
| 🚫 NSFW | Explicit nudity detected |

**Blur tool:**
- Images: Gaussian blur (kernel 99×99, sigma 30) applied over each detected bounding box
- Videos: Detection runs every 10 frames; blur is applied to every frame using the most recent detections (fast + smooth)
- Only explicitly-defined NSFW regions are blurred — safe areas are untouched

**Accuracy:**
NudeNet achieves 90%+ accuracy on standard adult content benchmarks. Confidence threshold is set at 0.45 (detections below this are ignored).

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home page |
| GET | `/auth/login` | Login page |
| POST | `/auth/login` | Submit login form |
| GET | `/auth/signup` | Signup page |
| POST | `/auth/signup` | Submit signup form |
| GET | `/auth/logout` | Clear session |
| GET | `/auth/google` | Redirect to Google OAuth |
| GET | `/auth/google/callback` | Handle Google OAuth return |
| GET | `/classify/lab` | Classifying Lab UI |
| POST | `/classify/run` | Classify uploaded file (no blur) |
| POST | `/classify/blur` | Classify + blur uploaded file |
| POST | `/classify/youtube` | Classify a YouTube URL |
| GET | `/health` | Health check |

---

## Environment Variables Reference

| Variable | Description |
|---|---|
| `SECRET_KEY` | Random string for signing sessions and JWTs |
| `MYSQL_USER` | MySQL username |
| `MYSQL_PASSWORD` | MySQL password |
| `MYSQL_HOST` | MySQL host (`db` in Docker, `localhost` otherwise) |
| `MYSQL_PORT` | MySQL port (default: `3306`) |
| `MYSQL_DB` | Database name |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | Must match what you registered in Google Cloud |

---

## Deploying to production

1. Set `GOOGLE_REDIRECT_URI` to your production URL, e.g. `https://yourdomain.com/auth/google/callback`
2. Add that URI to your Google Cloud OAuth authorized redirect URIs
3. Use a strong, unique `SECRET_KEY`
4. Use a real MySQL host (e.g. AWS RDS, PlanetScale, Supabase)
5. Put the app behind a reverse proxy like Nginx with HTTPS (Let's Encrypt)

---

## Troubleshooting

**NudeNet model not downloading**
Run a quick test to trigger the download manually:
```bash
python -c "from nudenet import NudeDetector; NudeDetector()"
```

**MySQL connection refused**
- Check that MySQL is running: `sudo systemctl status mysql`
- Confirm the credentials in `.env` match the MySQL user you created

**Google login not working**
- Make sure `GOOGLE_REDIRECT_URI` exactly matches what's in Google Cloud Console
- Check that your Google account is added as a Test user in the OAuth consent screen

**Video processing is slow**
- That's normal for long videos. The blur tool processes every frame.
- For very large videos, consider reducing `sample_every_n_frames` in `classifier.py`

---

## License

MIT — do whatever you want with it.
