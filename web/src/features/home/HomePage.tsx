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
            {isAuthenticated ? (
              <Link className="personal" to="/dashboard">Dashboard ↗</Link>
            ) : (
              <Link className="personal" to="/login">Log in / Register ↗</Link>
            )}
          </nav>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="shell hero-grid">
            <div className="hero-copy">
              <p className="kicker">A private workspace for your job search</p>
              <h1>Build your story.<span>Keep the thread.</span></h1>
              <p>Keep your CV, career material, and applications connected—from first draft to final PDF.</p>
              <div className="actions">
                <PrimaryAction authenticated={isAuthenticated} />
                <a className="button ghost" href="#tour">Watch the tour</a>
              </div>
              <div className="hero-note"><span>Live document preview</span><span>Reusable career Library</span><span>Tailored applications</span></div>
            </div>
            <div className="atlas" aria-label="Actual Aergia product screens">
              <div className="atlas-card"><img src="/showcase/tailored.webp" alt="A real demo CV in the Aergia builder" /><span className="tag">Application-ready CV</span></div>
              <div className="atlas-card"><img src="/showcase/library.webp" alt="Adding career material from the Library" /><span className="tag">Reuse your work</span></div>
              <div className="atlas-card"><img src="/showcase/application-detail.webp" alt="Application detail with job relevance" /><span className="tag">Keep role context</span></div>
              <div className="atlas-card"><p>One connected workspace</p><strong>CV → Library → application → tailored output</strong></div>
            </div>
          </div>
        </section>



         <section className="map" id="map">
          <div className="shell">
            <div className="section-title"><div className="section-title-main"><div className="section-no">01 / THE SYSTEM</div><h2>One workspace. Four connected parts.</h2></div><p>CVs, Library, Applications, and output work together—without trapping your source material.</p></div>
            <div className="system-map">
              <div className="system-screen"><img src="/showcase/dashboard.webp" alt="Aergia dashboard connecting CVs, Library, and Applications" loading="lazy" /><span className="stamp">Actual dashboard</span></div>
              <div className="system-flow">
                <div className="flow-node"><small>01</small><h3>CVs</h3><p>Create, import, and maintain reusable versions.</p></div>
                <div className="flow-arrow">→</div>
                <div className="flow-node"><small>02</small><h3>Library</h3><p>Save evidence you can use again.</p></div>
                <div className="flow-arrow">↑</div>
                <div className="flow-core">AERGIA</div>
                <div className="flow-arrow">↓</div>
                <div className="flow-node"><small>04</small><h3>Output</h3><p>Review quality and export the PDF.</p></div>
                <div className="flow-arrow">←</div>
                <div className="flow-node"><small>03</small><h3>Applications</h3><p>Keep roles, relevance, status, and follow-up together.</p></div>
              </div>
            </div>
          </div>
        </section>

        <section className="zone" id="author">
          <div className="shell">
            <div className="section-title"><div className="section-title-main"><div className="section-no">02 / AUTHOR</div><h2>Build one CV you can reuse.</h2></div><p>Edit structured content, tune the design, and see the resolved document as you work.</p></div>
            <div className="anatomy">
              <img src="/showcase/builder.webp" alt="Aergia content editor and live document preview" loading="lazy" />
              <div className="anatomy-label one"><b>01 / CONTENT</b><span>Edit and reorder structured sections.</span></div>
              <div className="anatomy-label two"><b>02 / PREVIEW</b><span>See changes in the real document.</span></div>
              <div className="anatomy-label three"><b>03 / OUTPUT</b><span>Export when it is ready.</span></div>
            </div>
            <div className="split-showcase">
              <article className="visual"><img src="/showcase/imported.webp" alt="Importing an existing CV with a selected template" loading="lazy" /><div className="caption"><small>Start with what exists</small><h3>Import a PDF into an editable CV</h3><p>Choose a template, then continue in the builder.</p></div></article>
              <article className="visual"><img src="/showcase/customize.webp" alt="Typography and section customization controls" loading="lazy" /><div className="caption"><small>Make it yours</small><h3>Customize the document</h3><p>Tune type, color, spacing, and layout beside the page.</p></div></article>
            </div>
          </div>
        </section>

        <section className="zone light" id="remember">
          <div className="shell">
            <div className="section-title"><div className="section-title-main"><div className="section-no">03 / REMEMBER</div><h2>Reuse your best work.</h2></div><p>The Library keeps career evidence separate from any one CV, so strong material can compound.</p></div>
            <div className="library-stage">
              <div className="library-screen"><img src="/showcase/library.webp" alt="Adding saved experience from the Aergia Library" loading="lazy" /></div>
              <div className="library-copy">
                <div><small>SAVE FROM THE BUILDER</small><h3>Keep the good parts.</h3><p>Promote a project or experience once; reuse it anywhere.</p></div>
                <div><small>ADD IN CONTEXT</small><h3>Bring evidence back.</h3><p>Insert saved material into the CV you are editing.</p></div>
                <div><small>POWER TAILORING</small><h3>Start from a dependable profile.</h3><p>Give direct editing and agent-assisted tailoring a consistent source.</p></div>
              </div>
            </div>
            <div className="category-strip" aria-label="Library categories"><span>Experiences</span><span>Education</span><span>Skills</span><span>Projects</span><span>Certifications</span><span>Languages</span><span>Research</span></div>
          </div>
        </section>

        <section className="zone" id="pursue">
          <div className="shell">
            <div className="section-title"><div className="section-title-main"><div className="section-no">04 / PURSUE</div><h2>Keep every application together.</h2></div><p>Job context, scanner findings, status, follow-up, and the linked CV stay attached to the role.</p></div>
            <div className="application-stage">
              <div className="application-copy">
                <p className="kicker">One record per role</p><h3>Review what the role asks for.</h3><p>Keep the opportunity and the document in the same working context.</p>
                <div className="signal"><b>01</b><div><strong>Job context</strong><span>Role, company, description, notes, and follow-up.</span></div></div>
                <div className="signal"><b>02</b><div><strong>Scanner</strong><span>Requirement evidence, term visibility, presentation findings, and PDF text recovery.</span></div></div>
                <div className="signal"><b>03</b><div><strong>Progress</strong><span>Status history that shows what happens next.</span></div></div>
                <div className="signal"><b>04</b><div><strong>Document</strong><span>A linked CV you can review, edit, check, and export.</span></div></div>
              </div>
              <div className="application-screen scanner-preview" role="img" aria-label="Illustration of four separate resume scanner analyses">
                <div className="scanner-preview-top"><span>SCANNER PREVIEW</span><span>JOB DESCRIPTION + EXISTING CV</span></div>
                <div className="scanner-preview-grid">
                  <article><small>01 / SEMANTIC JOB FIT</small><h4>Evidence by requirement</h4><p><span>Supported</span><span>Partial</span><span>Not evidenced</span></p></article>
                  <article><small>02 / TERM VISIBILITY</small><h4>Lexical ATS signals</h4><p><span>Exact</span><span>Variant</span><span>Absent</span></p></article>
                  <article><small>03 / PRESENTATION</small><h4>Resume quality findings</h4><p>Structure · specificity · outcomes</p></article>
                  <article><small>04 / PDF TEXT RECOVERY</small><h4>Aergia parser check</h4><p>Text · sections · reading order · links</p></article>
                </div>
                <p className="scanner-preview-note">Four independent analyses · no composite score</p>
              </div>
            </div>

            <section className="tailoring">
              <div className="tailoring-head"><div><p className="kicker dark">Edit directly or use an agent</p><h3>Tailor with control.</h3></div><p>Start from an existing CV in the editor, or use a time-limited agent session. Review every agent draft before accepting it.</p></div>
              <div className="tailoring-modes">
                <article className="mode"><small>EDITOR PATH</small><h4>Work directly on your CV</h4><p>Build or revise a document from your own experience and reusable Library material.</p><ul><li>Keep your CV under your control</li><li>Edit structured sections</li><li>Preview and export a PDF</li></ul></article>
                <article className="mode"><small>AGENT PATH</small><h4>Use your coding agent</h4><p>Let Codex, Claude Code, or OpenCode compose a draft through a scoped session.</p><ul><li>Time-limited access</li><li>Can adjust content and design</li><li>Returns a reviewable draft</li><li>Accept or reject before replacing</li></ul></article>
              </div>
            </section>

            <div className="output-grid">
              <article className="visual feature-note"><div className="caption"><small>Across the search</small><h3>See the next action.</h3><p>Track application status, linked CVs, scanner findings, and follow-up dates together.</p></div></article>
              <article className="visual feature-note"><div className="caption"><small>Inside one application</small><h3>Review an agent-authored draft.</h3><p>Inspect, edit, accept, or reject each draft before it becomes part of your application.</p></div></article>
            </div>
          </div>
        </section>

        <section className="trust">
          <div className="shell trust-grid">
            <div><p className="kicker dark">Quiet infrastructure</p><h2>Private by default. Consistent by design.</h2></div>
            <div className="trust-list">
              <div className="trust-item"><b>01</b><div><h3>Private workspace</h3><p>Career material is account-scoped to your job search.</p></div></div>
              <div className="trust-item"><b>02</b><div><h3>Credentials stay transient</h3><p>Import provider keys stay in memory; they are not stored.</p></div></div>
              <div className="trust-item"><b>03</b><div><h3>Drafts stay reviewable</h3><p>Agent-tailored work is reviewed before it replaces an application CV.</p></div></div>
              <div className="trust-item"><b>04</b><div><h3>Preview and PDF align</h3><p>The working preview and exported PDF share the same document path.</p></div></div>
            </div>
          </div>
        </section>

        <section className="tour" id="tour">
          <div className="shell tour-grid">
            <div><p className="kicker dark">See the real workflow</p><h2>From source CV to send-ready PDF.</h2><p>Watch import, editing, reuse, tracking, tailoring, and export in one real flow.</p></div>
            <video controls muted playsInline poster="/showcase/aergia-showcase-poster.webp" aria-label="Aergia product tour"><source src="/showcase/aergia-showcase.webm" type="video/webm" /><source src="/showcase/aergia-showcase.mp4" type="video/mp4" />Your browser does not support embedded video.</video>
          </div>
        </section>

        <section className="final"><div className="shell"><p className="kicker">Keep the thread</p><h2>Build once. Apply with intent.</h2><p>One private workspace for every relevant version.</p><PrimaryAction authenticated={isAuthenticated} /></div></section>
      </main>

      <footer><div className="shell"><span>Aergia © 2026</span><span>CV builder · Career Library · Application tracker · Agent tailoring · PDF export</span><span>Built by <a href="https://rmahbub.com" target="_blank" rel="noreferrer">Riasat Mahbub ↗</a></span></div></footer>
    </div>
  );
}
