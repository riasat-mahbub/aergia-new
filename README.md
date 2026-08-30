# Aergia

Aergia is a private workspace for building professional CVs, keeping your
best career material reusable, and preparing applications.

You can use it to create several versions of your CV, import an existing PDF,
track the jobs you are applying for, and export a polished PDF when you are
ready to apply.

## What you can do

- **Build multiple CVs.** Create reusable CV drafts and versions from scratch.
  Add Profile, Experience, Education, Skills, Projects, Languages,
  Certifications, Research, or Extras sections.
- **Start from an existing CV.** Import a PDF and review the extracted content
  in the editor before using it as a new CV.W
- **Choose your look.** Use Modern, Classic, or Minimal templates, then adjust
  colors, fonts, section order, spacing, and layout.
- **Reuse your best work.** Save experiences, skills, projects, education,
  certifications, languages, and research in the Library. Pull those entries
  into any CV or promote content from an existing CV into the Library.
- **Track applications.** Save a company, role, job description, job link,
  notes, status, and next follow-up date in one place.
- **Create a tailored CV.** A tracked application can generate an editable CV
  using your profile and Library content. Aergia also shows requirement
  coverage, supporting evidence, and a one-page fit check.
- **Preview and export.** The live preview and downloaded PDF use the same
  document rendering, and links in the PDF remain clickable.

## A simple workflow

1. Create an account and open the Dashboard.
2. Add your shared profile details in **Settings**.
3. Open **CVs** and create a CV, or import an existing PDF.
4. Fill in your sections, reorder them, choose a template, and customize the
   appearance.
5. Check the live preview and select **Export PDF**.
6. For a specific job, open **Applications**, choose **Track application**,
   paste the job description, and generate a tailored CV.

## Templates

- **Modern** — a two-column layout with a sidebar for profile-style content.
- **Classic** — a compact single-column layout.
- **Minimal** — a spacious single-column layout.

The template controls the starting design. Your CV customizations can then
adjust the look without changing the content itself.

## The Library and tailored CVs

The Library is your reusable source material. Keep strong versions of your
experience, projects, skills, and other sections there, then choose what fits
each CV or application.

When you generate a tailored CV for an application, Aergia creates a normal
editable CV snapshot. Later changes to the Library or job description do not
silently rewrite that CV. Edit it in the Builder, or generate again explicitly
when you want a new version.

The relevance score is a guide to weighted job-requirement coverage. It is not
an ATS score or a prediction of hiring success. Open the linked CV to inspect
the matched requirements, missing requirements, and source evidence.

## Importing a PDF

PDF import extracts content into editable sections so you can correct names,
dates, formatting, and classifications before sending the CV anywhere.

The default parser works without an external service. You can optionally
configure an OpenAI, Anthropic, Gemini, or Groq key in **Settings** for
AI-assisted parsing. A key is held in memory for the import, used for that
request, and then cleared; it is not saved to browser storage or to your
Aergia account.

Always review imported content. Complex layouts, scanned PDFs, and unusual
formatting may need manual corrections.

## Privacy and account security

Aergia is designed to be self-hosted, so the operator controls the instance
and its storage. Production deployments use secure authentication cookies and
should be served over HTTPS.

Password recovery is not currently available. Keep your account password in a
safe place or contact the instance operator if you need help.

## Self-hosting

If you are using an existing Aergia instance, you can skip this section. To
run your own production instance, see [`DEPLOY.md`](DEPLOY.md).

The production container:

- runs database migrations automatically before starting the app;
- includes the pinned GLiNER2.5-small model and lazy-loads one process-local
  copy for requirement extraction;
- serializes model inference; 2+ vCPUs and 8GB RAM are the preferred target
  (`DEPLOY.md` documents the constrained lower bound);
- stores the SQLite database and uploaded images in Docker volumes; and
- binds its local port to `127.0.0.1:8000` so a host-based Cloudflare Tunnel
  can be used without exposing the app directly to the Internet.

For the documented Cloudflare setup, the tunnel target is:

```bash
cloudflared tunnel --url http://localhost:8000
```

Set a real `SECRET_KEY` in `.env` before starting the container. The app is
available through the HTTPS hostname configured for the tunnel.

## Documentation status

- [`DEPLOY.md`](DEPLOY.md) is the current operator guide.
- `docs/plans/` contains active internal implementation plans, not user
  instructions.
- `tracker-legacy/` contains historical tracker exports and is not part of the
  current user workflow.
