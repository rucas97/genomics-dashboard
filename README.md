Genomics Dashboard
Self-serve genomics analytics for research labs and biotech.

Turns raw VCF/FASTQ/BAM files into a queryable dashboard: QC metrics, variant explorer, cohort analysis, and an audit log — the "last mile" layer that makes existing pharma/lab infrastructure usable by researchers without a data-engineering ticket.

Status
Scaffold + Modules 1–2 functional. Modules 3–7 in progress.

Module	Status
1. Samples & uploads	✅ Working
2. QC metrics	✅ Working
3. Variant explorer	🟡 Basic
4. Cohorts	⬜ Stub
5. Pipelines	⬜ Stub
6. Reports	⬜ Stub
7. Audit log	✅ Working
Stack
Frontend: Next.js 14 (App Router) + Tailwind CSS

Backend: FastAPI (Python 3.11)

Database: Supabase (Postgres + Auth + Storage)

VCF parsing: vcfpy (pure Python, no htslib)

Deploy: Vercel (frontend) + Render (backend)

Setup
1. Supabase
Create a project at supabase.com

SQL Editor → paste infrastructure/supabase/schema.sql → Run

Project Settings → API → copy the URL, anon public, and service_role keys

Authentication → Providers → enable Email and Anonymous sign-ins

Authentication → URL Configuration → Site URL = http://localhost:3000, add http://localhost:3000/** to redirect URLs

2. Backend
bash
cd backend
cp .env.example .env
# fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
Health check: http://localhost:8000/health → {"status":"ok"}

3. Frontend
bash
cd frontend
cp .env.local.example .env.local
# fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL
npm install
npm run dev
Open http://localhost:3000

Usage
Sign in with a magic link or continue as guest

Upload a .vcf file (uncompressed)

Wait for status to flip from processing → ready

Explore variants in Variant Explorer

Check the Audit Log for every action

Roadmap
□ Module 3: VEP / ClinVar annotation pipeline
□ Module 4: Cohort PCA + heatmaps
□ Module 5: Nextflow pipeline runner
□ Module 6: PDF report generation
□ Helm chart for on-prem deployment
□ SAML/OIDC SSO for enterprise
License
MIT — see LICENSE

Contributing
This is currently a solo project. Issues and PRs welcome once the v1 is stable.

How to paste it into GitHub
Open https://github.com/rucas97/genomics-dashboard

If README.md doesn't exist yet:

Click Add file → Create new file

Name it README.md

If it exists:

Click the file → click the pencil ✏️ icon (Edit)

Delete whatever is in the editor

Paste the text above

Scroll down → Commit changes → commit directly to main

Done. The repo home page will render it as a formatted README.

Also add the LICENSE
Separate file. Same process: Add file → Create new file, name it LICENSE (no extension), paste:

MIT License

Copyright (c) 2026 Rucas97

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
