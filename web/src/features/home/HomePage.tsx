import { Link } from "@tanstack/react-router";
import { useAuthStore } from "@/features/authentication";
import "./HomePage.css";

function PrimaryAction({ authenticated }: { authenticated: boolean }) {
  return authenticated ? (
    <Link className="button" to="/dashboard">Open your workspace →</Link>
  ) : (
    <Link className="button" to="/register">Create your workspace →</Link>
  );
}

export default function HomePage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <div className="product-atlas">
      <header>
        <div className="shell">
          <Link className="brand" to="/"><b>A</b>Aergia</Link>
          <nav aria-label="Home">
            <a href="#map">System</a>
            <a href="#author">Author</a>
            <a href="#remember">Remember</a>
            <a href="#pursue">Pursue</a>
            <a href="#tour">Tour</a>
            <a className="personal" href="https://rmahbub.com" target="_blank" rel="noreferrer">rmahbub.com ↗</a>
          </nav>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="shell hero-grid">
            <div className="hero-copy">
              <p className="kicker">A private operating system for your job search</p>
              <h1>Build your story.<span>Keep the thread.</span></h1>
              <p>Aergia connects the CV you maintain, the career material you reuse, and every role you pursue—from first draft to application-ready PDF.</p>
              <div className="actions">
                <PrimaryAction authenticated={isAuthenticated} />
                <a className="button ghost" href="#tour">Watch the tour</a>
              </div>
              <div className="hero-note"><span>Real document preview</span><span>Reusable career Library</span><span>Application-specific CVs</span></div>
            </div>
            <div className="atlas" aria-label="Actual Aergia product screens">
              <div className="atlas-card"><img src="/showcase/tailored.webp" alt="A real demo CV in the Aergia builder" /><span className="tag">Application-ready CV</span></div>
              <div className="atlas-card"><img src="/showcase/library.webp" alt="Adding career material from the Library" /><span className="tag">Reuse your work</span></div>
              <div className="atlas-card"><img src="/showcase/application-detail.webp" alt="Application detail with job relevance" /><span className="tag">Keep role context</span></div>
              <div className="atlas-card"><p>One connected workspace</p><strong>CV → Library → application → tailored output</strong></div>
            </div>
          </div>
        </section>

        <section className="section-index">
          <div className="shell">
            <a href="#map"><strong>00</strong>See the connected system</a>
            <a href="#author"><strong>01</strong>Author the source</a>
            <a href="#remember"><strong>02</strong>Reuse what matters</a>
            <a href="#pursue"><strong>03</strong>Pursue each role</a>
          </div>
        </section>

        <section className="premise"><div className="shell"><p>Most CV tools stop at the page. Aergia keeps going—through the <em>source material, the opportunity, the tailored draft, and the follow-up.</em></p></div></section>

        <section className="map" id="map">
          <div className="shell">
            <div className="section-title"><div className="section-no">00 / THE SYSTEM</div><h2>Everything has a place—and a relationship.</h2><p>The dashboard is an overview, not a dead end. Each area feeds the next while the source material stays reusable and independently editable.</p></div>
            <div className="system-map">
              <div className="system-screen"><img src="/showcase/dashboard.webp" alt="Aergia dashboard connecting CVs, Library, and Applications" loading="lazy" /><span className="stamp">Actual dashboard</span></div>
              <div className="system-flow">
                <div className="flow-node"><small>01</small><h3>CVs</h3><p>Create, import, duplicate, edit, and keep reusable versions.</p></div>
                <div className="flow-arrow">→</div>
                <div className="flow-node"><small>02</small><h3>Library</h3><p>Maintain the evidence and profile that power future documents.</p></div>
                <div className="flow-arrow">↑</div>
                <div className="flow-core">AERGIA</div>
                <div className="flow-arrow">↓</div>
                <div className="flow-node"><small>04</small><h3>Output</h3><p>Review the resolved page, run quality checks, and export PDF.</p></div>
                <div className="flow-arrow">←</div>
                <div className="flow-node"><small>03</small><h3>Applications</h3><p>Attach job context, relevance, status, follow-up, and tailored CV.</p></div>
              </div>
            </div>
          </div>
        </section>

        <section className="zone" id="author">
          <div className="shell">
            <div className="section-title"><div className="section-no">01 / AUTHOR</div><h2>Make one CV worth maintaining.</h2><p>Start from a blank template or import the document you already have. Structured editing, document design, and the resolved output stay in the same working context.</p></div>
            <div className="anatomy">
              <img src="/showcase/builder.webp" alt="Aergia content editor and live document preview" loading="lazy" />
              <div className="anatomy-label one"><b>01 / CONTENT</b><span>Reorder, show, hide, add, and edit structured sections.</span></div>
              <div className="anatomy-label two"><b>02 / PREVIEW</b><span>See the real HTML document resolve as you work.</span></div>
              <div className="anatomy-label three"><b>03 / OUTPUT</b><span>Save, promote useful material, or export the current PDF.</span></div>
            </div>
            <div className="ledger">
              <div className="ledger-row"><div className="code">AUTHOR / 01</div><h3>Structured content</h3><p>Profile, experience, education, skills, projects, certifications, languages, research, and custom ordering.</p></div>
              <div className="ledger-row"><div className="code">AUTHOR / 02</div><h3>Section-level control</h3><p>Reorder instances, toggle visibility, add sections, and tune individual heading and layout behavior.</p></div>
              <div className="ledger-row"><div className="code">AUTHOR / 03</div><h3>Document-level design</h3><p>Templates, typography, heading colors, section accents, body text, spacing, page breaks, and date presentation.</p></div>
              <div className="ledger-row"><div className="code">AUTHOR / 04</div><h3>One resolved output</h3><p>The editing preview and Chromium PDF share the same document model, reducing surprises at export.</p></div>
            </div>
            <div className="split-showcase">
              <article className="visual"><img src="/showcase/imported.webp" alt="Importing an existing CV with a selected template" loading="lazy" /><div className="caption"><small>Start from what exists</small><h3>Import a PDF into an editable CV</h3><p>Give it a title, choose the starting template, and continue in the same builder.</p></div></article>
              <article className="visual"><img src="/showcase/customize.webp" alt="Typography and section customization controls" loading="lazy" /><div className="caption"><small>Make the system yours</small><h3>Customize without losing the page</h3><p>Design controls remain beside the document they affect, from heading treatment to spacing and page behavior.</p></div></article>
            </div>
          </div>
        </section>

        <section className="zone light" id="remember">
          <div className="shell">
            <div className="section-title"><div className="section-no">02 / REMEMBER</div><h2>Your best career material should compound.</h2><p>The Library is not a folder of old CVs. It is the reusable source material behind them, plus the profile used to generate role-specific drafts.</p></div>
            <div className="library-stage">
              <div className="library-screen"><img src="/showcase/library.webp" alt="Adding saved experience from the Aergia Library" loading="lazy" /></div>
              <div className="library-copy">
                <div><small>SAVE FROM THE BUILDER</small><h3>Promote what is worth keeping.</h3><p>A strong project or experience can become reusable material instead of staying trapped in one CV.</p></div>
                <div><small>ADD IN CONTEXT</small><h3>Bring the right evidence back.</h3><p>Browse saved entries while editing and insert the relevant one into the current document.</p></div>
                <div><small>POWER TAILORING</small><h3>Keep one dependable profile.</h3><p>Your Library profile and selected entries give tailored CV generation a consistent source.</p></div>
              </div>
            </div>
            <div className="category-strip" aria-label="Library categories"><span>Experiences</span><span>Education</span><span>Skills</span><span>Projects</span><span>Certifications</span><span>Languages</span><span>Research</span></div>
            <div className="ledger">
              <div className="ledger-row"><div className="code">REMEMBER / 01</div><h3>Create and edit entries directly</h3><p>Maintain the source independently, even when it does not yet belong to a specific CV.</p></div>
              <div className="ledger-row"><div className="code">REMEMBER / 02</div><h3>Move both directions</h3><p>Promote sections from a CV to the Library or pull Library entries into a CV without manual re-entry.</p></div>
              <div className="ledger-row"><div className="code">REMEMBER / 03</div><h3>Keep source and use separate</h3><p>Reuse does not force every application to tell the same story; each CV can select only what fits.</p></div>
            </div>
          </div>
        </section>

        <section className="zone" id="pursue">
          <div className="shell">
            <div className="section-title"><div className="section-no">03 / PURSUE</div><h2>Keep the role attached to the work.</h2><p>An application is more than a status label. Aergia keeps the job description, relevance evidence, next follow-up, status history, generated CV, and final output together.</p></div>
            <div className="application-stage">
              <div className="application-copy">
                <p className="kicker">A complete application record</p><h3>Know why this version belongs to this role.</h3><p>The CV remains editable, but its purpose and evidence never drift away from the opportunity.</p>
                <div className="signal"><b>01</b><div><strong>Job context</strong><span>Company, role, description, URL, notes, and next follow-up.</span></div></div>
                <div className="signal"><b>02</b><div><strong>Relevance evidence</strong><span>Weighted fit plus matched, missing, and source evidence in the linked CV.</span></div></div>
                <div className="signal"><b>03</b><div><strong>Progress history</strong><span>Current status and a recorded history as the application moves forward.</span></div></div>
                <div className="signal"><b>04</b><div><strong>Generated document</strong><span>Selected sections, Library sources, quality result, edit link, and PDF export.</span></div></div>
              </div>
              <div className="application-screen"><img src="/showcase/application-detail.webp" alt="Aergia application detail with job, relevance, and generated CV panels" loading="lazy" /><div className="score"><div><b>64%</b><small>RELEVANCE</small></div></div></div>
            </div>
            <div className="process"><div><b>03A</b><h3>Track and search roles</h3></div><div><b>03B</b><h3>Set status and follow-up</h3></div><div><b>03C</b><h3>Inspect relevance evidence</h3></div><div><b>03D</b><h3>Review the tailored draft</h3></div><div><b>03E</b><h3>Edit and export PDF</h3></div></div>

            <section className="tailoring">
              <div className="tailoring-head"><div><p className="kicker dark">Two paths, one review step</p><h3>Tailor with control—not blind automation.</h3></div><p>Aergia can generate a standard application CV or open a secure, time-limited session for your coding agent. Either way, the result stays a draft you can inspect and edit before it replaces anything.</p></div>
              <div className="tailoring-modes">
                <article className="mode"><small>FAST PATH</small><h4>Generate a standard CV</h4><p>Create a role-focused document from the profile and Library when you want a dependable starting point quickly.</p><ul><li>Uses the application’s job context</li><li>Selects relevant Library material</li><li>Produces an editable linked CV</li><li>Runs document quality checks</li></ul></article>
                <article className="mode"><small>AGENT PATH</small><h4>Use your coding agent</h4><p>Let Codex, Claude Code, or OpenCode compose a complete draft through a scoped tailoring session.</p><ul><li>Time-limited session and one-time access</li><li>May adjust content, sections, template, layout, and styles</li><li>Returns relevance, warnings, and review notes</li><li>Accept or reject before changing the application CV</li></ul></article>
              </div>
            </section>

            <div className="output-grid">
              <article className="visual"><img src="/showcase/pipeline.webp" alt="Searchable application pipeline with relevance and follow-up" loading="lazy" /><div className="caption"><small>Across the search</small><h3>See roles, relevance, status, and follow-ups</h3><p>Search and filter the pipeline so the next action is visible.</p></div></article>
              <article className="visual"><img src="/showcase/tailored.webp" alt="Tailored CV open for review and editing" loading="lazy" /><div className="caption"><small>Inside one application</small><h3>Keep the tailored CV editable</h3><p>Review it in the same builder, refine what the role needs, and export only when it is ready.</p></div></article>
            </div>
          </div>
        </section>

        <section className="trust">
          <div className="shell trust-grid">
            <div><p className="kicker dark">Quiet infrastructure</p><h2>Private where it matters. Consistent where it counts.</h2></div>
            <div className="trust-list">
              <div className="trust-item"><b>01</b><div><h3>Private workspace</h3><p>Your career material is account-scoped and designed around one person’s job search.</p></div></div>
              <div className="trust-item"><b>02</b><div><h3>Import credentials are not retained</h3><p>Provider keys used to parse an imported CV stay in memory and are not stored by Aergia.</p></div></div>
              <div className="trust-item"><b>03</b><div><h3>Drafts remain drafts</h3><p>Agent-tailored work must be reviewed and accepted before replacing the CV attached to an application.</p></div></div>
              <div className="trust-item"><b>04</b><div><h3>Preview and PDF stay aligned</h3><p>The same HTML-first document path powers the working preview and Chromium export.</p></div></div>
            </div>
          </div>
        </section>

        <section className="tour" id="tour">
          <div className="shell tour-grid">
            <div><p className="kicker dark">Real product, real workflow</p><h2>One minute from source CV to send-ready PDF.</h2><p>No fantasy screens. Watch the application move through import, editing, customization, reuse, tracking, tailoring, and export.</p></div>
            <video controls muted playsInline poster="/showcase/aergia-showcase-poster.webp" aria-label="Aergia product tour"><source src="/showcase/aergia-showcase.webm" type="video/webm" /><source src="/showcase/aergia-showcase.mp4" type="video/mp4" />Your browser does not support embedded video.</video>
          </div>
        </section>

        <section className="final"><div className="shell"><p className="kicker">Your career material deserves continuity</p><h2>Build once. Keep improving. Apply with intent.</h2><p>One private workspace. Every relevant version.</p><PrimaryAction authenticated={isAuthenticated} /></div></section>
      </main>

      <footer><div className="shell"><span>Aergia © 2026</span><span>CV builder · Career Library · Application tracker · Agent tailoring · PDF export</span><span>Built by <a href="https://rmahbub.com" target="_blank" rel="noreferrer">Riasat Mahbub ↗</a></span></div></footer>
    </div>
  );
}
