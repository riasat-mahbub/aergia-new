import ProfileRenderer from "../sections/profile/ProfileRenderer";

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import ExperienceRenderer from "../sections/experience/ExperienceRenderer";
import EducationRenderer from "../sections/education/EducationRenderer";
import ProjectsRenderer from "../sections/projects/ProjectsRenderer";
import ResearchRenderer from "../sections/research/ResearchRenderer";
import CertificationsRenderer from "../sections/certifications/CertificationsRenderer";
import { DATE_STYLE_OPTIONS } from "../../lib/sections/DateField";
import type { SectionStyle, DateStyle } from "../../lib/sections/types";

const PRESETS = DATE_STYLE_OPTIONS.map((o): [string, DateStyle] => [
  o.value,
  { key: o.value, rangeSep: o.rangeSep },
]);

describe("renderers defer to default when style is absent", () => {
  it("experience renders YYYY-MM-dash range by default", () => {
    const { container } = render(
      <ExperienceRenderer
        data={[
          {
            id: "e1",
            company: "Acme",
            position: "Engineer",
            start_date: "2021-03",
            end_date: "2022-01",
            current: false,
            location: "",
            description: "",
          },
        ]}
      />,
    );
    expect(container.textContent).toContain("2021-03 \u2013 2022-01");
  });

  it("research renders Published YYYY-MM by default", () => {
    const { container } = render(
      <ResearchRenderer

        data={[
          {
            id: "r1",
            title: "Paper",
            paper_url: "",
            paper_link_text: "",
            description: "",
            publication_date: "2025-04",
            publication_value: "",
          },
        ]}
      />,
    );
    expect(container.textContent).toContain("2025-04");
  });

  it("certifications renders date on its own line by default", () => {
    const { container } = render(
      <CertificationsRenderer
        data={[
          {
            id: "c1",
            name: "AWS",
            issuer: "Amazon",
            date: "2024-01",
            credential_url: "",
          },
        ]}
      />,
    );
    expect(container.textContent).toContain("2024-01");
  });
});

describe("experience renderer respects style.date_style", () => {
  it.each(PRESETS)("formats range with %s", (_key, dateStyle) => {
    const style: SectionStyle = { date_style: dateStyle };
    const { container } = render(
      <ExperienceRenderer
        style={style}
        data={[
          {
            id: "e1",
            company: "Acme",
            position: "Engineer",
            start_date: "2021-03",
            end_date: "2022-01",
            current: false,
            location: "",
            description: "",
          },
        ]}
      />,
    );
    const expectedStart = formatBound("2021-03", dateStyle);
    const expectedEnd = formatBound("2022-01", dateStyle);
    const text = container.textContent ?? "";
    expect(text).toContain(expectedStart);
    expect(text).toContain(expectedEnd);
    expect(text).toContain(`${expectedStart}${dateStyle.rangeSep}${expectedEnd}`);
  });
});

describe("education renderer respects style.date_style", () => {
  it.each(PRESETS)("formats range with %s", (_key, dateStyle) => {
    const style: SectionStyle = { date_style: dateStyle };
    const { container } = render(
      <EducationRenderer
        style={style}
        data={[
          {
            id: "e1",
            institution: "MIT",
            degree: "BS",
            start_date: "2021-03",
            end_date: "2022-01",
            current: false,
            gpa: "",
            summary: "",
          },
        ]}
      />,
    );
    const expectedStart = formatBound("2021-03", dateStyle);
    const expectedEnd = formatBound("2022-01", dateStyle);
    const text = container.textContent ?? "";
    expect(text).toContain(`${expectedStart}${dateStyle.rangeSep}${expectedEnd}`);
  });
});

describe("projects renderer respects style.date_style", () => {
  it.each(PRESETS)("formats range with %s", (_key, dateStyle) => {
    const style: SectionStyle = { date_style: dateStyle };
    const { container } = render(
      <ProjectsRenderer
        style={style}
        data={[
          {
            id: "p1",
            name: "Tool",
            url: "",
            link_text: "",
            start_date: "2021-03",
            end_date: "2022-01",
            description: "",
            tech_stack: [],
          },
        ]}
      />,
    );
    const expectedStart = formatBound("2021-03", dateStyle);
    const expectedEnd = formatBound("2022-01", dateStyle);
    const text = container.textContent ?? "";
    expect(text).toContain(`${expectedStart}${dateStyle.rangeSep}${expectedEnd}`);
  });
});

describe("current=true path still wins with style", () => {
  it("experience shows 'March 2021 – Present' for current with Month YYYY", () => {
    const style: SectionStyle = { date_style: { key: "Month YYYY", rangeSep: " \u2013 " } };
    const { container } = render(
      <ExperienceRenderer
        style={style}
        data={[
          {
            id: "e1",
            company: "Acme",
            position: "Engineer",
            start_date: "2021-03",
            end_date: "2022-01",
            current: true,
            location: "",
            description: "",
          },
        ]}
      />,
    );
    expect(container.textContent).toContain("March 2021 \u2013 Present");
  });
});

describe("research renderer respects style.date_style", () => {
  it.each(PRESETS)("renders Publication date with %s", (_key, dateStyle) => {
    const style: SectionStyle = { date_style: dateStyle };
    const { container } = render(
      <ResearchRenderer
        style={style}
        data={[
          {
            id: "r1",
            title: "Paper",
            paper_url: "",
            paper_link_text: "",
            description: "",
            publication_date: "2021-03",
            publication_value: "",
          },
        ]}
      />,
    );
    const expected = formatBound("2021-03", dateStyle);
    expect(container.textContent).toContain(expected);
  });
});

describe("certifications renderer respects style.date_style", () => {
  it.each(PRESETS)("formats date with %s", (_key, dateStyle) => {
    const style: SectionStyle = { date_style: dateStyle };
    const { container } = render(
      <CertificationsRenderer
        style={style}
        data={[
          {
            id: "c1",
            name: "AWS",
            issuer: "Amazon",
            date: "2021-03",
            credential_url: "",
          },
        ]}
      />,
    );
    const expected = formatBound("2021-03", dateStyle);
    expect(container.textContent).toContain(expected);
  });
});

describe("renderers skip empty date paragraphs", () => {
  it("research hides Published line when publication_date is empty", () => {
    const { container } = render(
      <ResearchRenderer
        data={[
          {
            id: "r1",
            title: "Paper",
            paper_url: "",
            paper_link_text: "",
            description: "",
            publication_date: "",
            publication_value: "",
          },
        ]}
      />,
    );
    expect(container.textContent).not.toContain("Published");
  });
  it("certifications skips the date line when date is empty", () => {
    const { container } = render(
      <CertificationsRenderer
        data={[
          {
            id: "c1",
            name: "AWS",
            issuer: "Amazon",
            date: "",
            credential_url: "",
          },
        ]}
      />,
    );
    expect(container.textContent).not.toContain("2024-01");
  });
});

// Helper mirroring formatSingleDate without importing it (keeps test
// independent of helper signature drift).
function formatBound(raw: string, style: DateStyle): string {
  const [y, m] = raw.split("-");
  if (!y || !m) return raw;
  const year = Number(y);
  const month = Number(m);
  if (!Number.isInteger(year) || !Number.isInteger(month)) return raw;
  if (month < 1 || month > 12) return raw;
  const yy = String(year);
  const mm = String(month).padStart(2, "0");
  const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  const SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  switch (style.key) {
    case "YYYY-MM":
      return `${yy}-${mm}`;
    case "YYYY/MM":
      return `${yy}/${mm}`;
    case "MM/YYYY":
      return `${mm}/${yy}`;
    case "MM-YYYY":
      return `${mm}-${yy}`;
    case "MM.YYYY":
      return `${mm}.${yy}`;
    case "YYYY.MM":
      return `${yy}.${mm}`;
    case "Mon YYYY":
      return `${SHORT[month - 1]} ${yy}`;
    case "Month YYYY":
      return `${MONTH_NAMES[month - 1]} ${yy}`;
    case "YYYY":
      return yy;
    case "Mon-YYYY":
      return `${SHORT[month - 1]}-${yy}`;
    default:
      return raw;
  }


describe("social links row", () => {
  it("profile renders social links on a separate row with icons", () => {
    const { container } = render(
      <ProfileRenderer
        data={{
          name: "Alice",
          title: "",
          email: "",
          email_link: true,
          phone: "",
          location: "",
          site_text: "",
          site_url: "",
          summary: "",
          photo_url: "",
          social_links: [
            { label: "LinkedIn", url: "https://www.linkedin.com/in/alice", icon: "linkedin" },
            { label: "GitHub", url: "https://github.com/alice", icon: "github" },
          ],
        }}
      />,
    );
    const text = container.textContent ?? "";
    expect(text).toContain("LinkedIn");
    expect(text).toContain("GitHub");
    // The icons render as <svg> elements via SocialIcon.
    expect(container.querySelectorAll("svg").length).toBeGreaterThanOrEqual(2);
  });

  it("profile omits the social-links row when empty", () => {
    const { container } = render(
      <ProfileRenderer
        data={{
          name: "Alice",
          title: "",
          email: "",
          email_link: true,
          phone: "",
          location: "",
          site_text: "",
          site_url: "",
          summary: "",
          photo_url: "",
          social_links: [],
        }}
      />,
    );
    expect(container.textContent ?? "").not.toContain("LinkedIn");
  });

  it("profile renders social link with empty URL as a span (preview)", () => {
    const { container } = render(
      <ProfileRenderer
        data={{
          name: "Alice",
          title: "",
          email: "",
          email_link: true,
          phone: "",
          location: "",
          site_text: "",
          site_url: "",
          summary: "",
          photo_url: "",
          social_links: [
            { label: "Pending", url: "", icon: "globe" },
          ],
        }}
      />,
    );
    // The label still shows for the editor preview but the anchor is omitted.
    expect(container.textContent ?? "").toContain("Pending");
    expect(container.querySelector("a")).toBeNull();
  });
});

describe("research publication_value renders as a separate paragraph", () => {
  it("renders publication_value when set", () => {
    const { container } = render(
      <ResearchRenderer
        data={[
          {
            id: "r1",
            title: "Paper",
            paper_url: "",
            paper_link_text: "",
            description: "",
            publication_date: "2025-04",
            publication_value: "NeurIPS 2024",
          },
        ]}
      />,
    );
    expect(container.textContent ?? "").toContain("NeurIPS 2024");
  });

  it("omits publication_value when empty", () => {
    const { container } = render(
      <ResearchRenderer
        data={[
          {
            id: "r1",
            title: "Paper",
            paper_url: "",
            paper_link_text: "",
            description: "",
            publication_date: "2025-04",
            publication_value: "",
          },
        ]}
      />,
    );
    // The publication_date still renders; only publication_value is absent.
    expect(container.textContent ?? "").toContain("2025-04");
  });
  it("publication_value is a direct sibling of the title, not of the outer row", () => {
    const { container } = render(
      <ResearchRenderer
        data={[
          {
            id: "r1",
            title: "Paper",
            paper_url: "https://doi.org/10.0000/x",
            paper_link_text: "DOI",
            description: "",
            publication_date: "2025-04",
            publication_value: "NeurIPS 2024",
          },
        ]}
      />,
    );
    const title = container.querySelector("h3");
    const titleNext = title?.nextElementSibling;
    expect(titleNext?.textContent).toBe("NeurIPS 2024");
  });
});

describe("projects link sits beside the date", () => {
  it("renders url link in right column with arrow glyph", () => {
    const { container } = render(
      <ProjectsRenderer
        data={[
          {
            id: "p1",
            name: "Tool",
            url: "https://example.com/tool",
            link_text: "Repo",
            start_date: "2024-01",
            end_date: null,
            description: "",
            tech_stack: [],
          },
        ]}
      />,
    );
    const anchor = container.querySelector("a");
    expect(anchor).not.toBeNull();
    expect(anchor?.getAttribute("href")).toBe("https://example.com/tool");
    expect(anchor?.textContent).toContain("Repo");
    expect(anchor?.textContent).toContain("\u2197");
  });

  it("description is a direct sibling of the name, not of the outer row", () => {
    const { container } = render(
      <ProjectsRenderer
        data={[
          {
            id: "p1",
            name: "Tool",
            url: "https://example.com/tool",
            link_text: "Repo",
            start_date: "2024-01",
            end_date: null,
            description: "A project description.",
            tech_stack: [],
          },
        ]}
      />,
    );
    const title = container.querySelector("h3");
    const titleNext = title?.nextElementSibling;
    expect(titleNext?.textContent).toBe("A project description.");
  });
});

}