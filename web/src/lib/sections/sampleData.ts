import { generateInstanceId } from "./types";

export const sampleInstances = [
  {
    id: "sample_profile",
    type: "profile",
    title: "Profile",
    enabled: true,
    data: {
      name: "Alex Morgan",
      title: "Senior Software Engineer",
      email: "alex.morgan@email.com",
      email_link: true,
      phone: "+1 (555) 123-4567",
      location: "San Francisco, CA",
      site_text: "aergia.dev",
      site_url: "https://aergia.dev",
      summary: "Experienced software engineer with 8+ years in full-stack development. Passionate about building scalable systems and clean user experiences.",
      photo_url: "",
      social_links: [
        { label: "LinkedIn", url: "https://www.linkedin.com/in/alex-morgan", icon: "linkedin" },
        { label: "GitHub", url: "https://github.com/alexmorgan", icon: "github" },
      ],
    },
  } as const,
  {
    id: "sample_experience",
    type: "experience",
    title: "Experience",
    enabled: true,
    data: [
      {
        id: generateInstanceId(),
        company: "TechCorp Inc.",
        position: "Senior Software Engineer",
        start_date: "2021-03",
        end_date: null,
        current: true,
        location: "San Francisco, CA",
        description: "Led development of microservices architecture serving 2M+ users. Mentored junior engineers and established coding standards.",
      },
      {
        id: generateInstanceId(),
        company: "StartupXYZ",
        position: "Software Engineer",
        start_date: "2018-06",
        end_date: "2021-02",
        current: false,
        location: "Austin, TX",
        description: "Built and maintained full-stack web applications using React, Node.js, and PostgreSQL. Improved page load times by 40%.",
      },
    ],
  } as const,
  {
    id: "sample_education",
    type: "education",
    title: "Education",
    enabled: true,
    data: [
      {
        id: generateInstanceId(),
        institution: "University of California, Berkeley",
        degree: "B.S. Computer Science",
        start_date: "2014-09",
        end_date: "2018-05",
        current: false,
        gpa: "3.8",
        summary: "",
      },
    ],
  } as const,
  {
    id: "sample_skills",
    type: "skills",
    title: "Skills",
    enabled: true,
    data: [
      {
        id: generateInstanceId(),
        category: "Languages",
        items: ["TypeScript", "Python", "JavaScript", "Go"],
      },
      {
        id: generateInstanceId(),
        category: "Frameworks",
        items: ["React", "Next.js", "FastAPI", "Django", "Tailwind CSS"],
      },
      {
        id: generateInstanceId(),
        category: "Tools",
        items: ["Docker", "Kubernetes", "AWS", "PostgreSQL", "Redis"],
      },
    ],
  } as const,
  {
    id: "sample_projects",
    type: "projects",
    title: "Projects",
    enabled: true,
    data: [
      {
        id: generateInstanceId(),
        url: "https://aergia.dev",
        link_text: "",
        start_date: "2024-01",
        end_date: null,
        description: "Open-source CV builder with drag-and-drop templates, PDF export, and real-time preview.",
        tech_stack: ["React", "FastAPI", "PostgreSQL", "Playwright"],
      },
    ],
  } as const,
  {
    id: "sample_languages",
    type: "languages",
    title: "Languages",
    enabled: true,
    data: [
      {
        id: generateInstanceId(),
        language: "English",
        proficiency: "Native",
      },
      {
        id: generateInstanceId(),
        language: "Spanish",
        proficiency: "Intermediate",
      },
    ],
  } as const,
  {
    id: "sample_certifications",
    type: "certifications",
    title: "Certifications",
    enabled: true,
    data: [
      {
        id: generateInstanceId(),
        name: "AWS Solutions Architect – Associate",
        issuer: "Amazon Web Services",
        date: "2023-06",
        credential_url: "",
      },
    ],
  } as const,
  {
    id: "sample_research",
    type: "research",
    title: "Research",
    enabled: true,
    data: [
      {
        id: generateInstanceId(),
        title: "Efficient Document Rendering with Intermediate Representations",
        paper_url: "https://doi.org/10.0000/aergia.2026",
        paper_link_text: "DOI",
        description: "Demonstrates a layout-stable IR that preserves user intent across template switches.",
        publication_value: "NeurIPS 2024",
        publication_date: "2026-06",
      },
    ],
  } as const,
];
