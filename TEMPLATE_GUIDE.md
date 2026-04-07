# User Template Guide

## Overview

User templates allow you to create custom CV templates with unique layouts, styles, and structures. Instead of using the built-in Modern, Classic, or Minimal templates, you can upload your own HTML template that will be rendered in the CV preview and used for PDF export.

## What is a User Template?

A user template is an HTML file that contains your custom CV template. When a CV uses a user template, the template HTML is rendered with your CV data injected into it via `window.__CV_DATA__`.

## Template Requirements

### Basic Structure
Your template should be a complete HTML document with the following requirements:

1. **HTML5 boilerplate**: `<!DOCTYPE html>` with proper `<html>`, `<head>`, and `<body>` tags
2. **Data injection script**: Include a `<script>` tag that reads `window.__CV_DATA__` to access CV section data
3. **Responsive design**: The template should work well on different screen sizes
4. **Print-friendly**: CSS that works well when printing to PDF

### Data Format

The `window.__CV_DATA__` object contains the CV section instances:

```typescript
interface CVData {
  instances: SectionInstance[];
}

interface SectionInstance {
  id: string;
  type: string; // "profile", "experience", "education", "skills", "projects", "languages", "certifications"
  title: string;
  enabled: boolean;
  data: any; // Type-specific data based on the section type
  style?: SectionStyle; // Optional per-instance styling
}
```

### Example Template

Here's a simple two-column template example:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your CV Template</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: 'Inter', system-ui, sans-serif;
      line-height: 1.6;
      color: #374151;
      max-width: 210mm;
      margin: 0 auto;
      padding: 20px;
    }
    
    .container {
      display: flex;
      gap: 40px;
    }
    
    .sidebar {
      flex: 1;
      background-color: #f8fafc;
      padding: 20px;
      border-radius: 8px;
    }
    
    .main {
      flex: 2;
    }
    
    .section {
      margin-bottom: 24px;
    }
    
    .section-title {
      font-size: 1.2em;
      font-weight: 600;
      margin-bottom: 12px;
      color: #111827;
      border-bottom: 2px solid #e5e7eb;
      padding-bottom: 4px;
    }
    
    .profile-info img {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      object-fit: cover;
      margin-bottom: 12px;
    }
    
    .experience-item, .education-item {
      margin-bottom: 16px;
    }
    
    .experience-title {
      font-weight: 600;
      font-size: 1.1em;
    }
    
    .experience-company {
      color: #6b7280;
      font-size: 0.95em;
    }
    
    .skills-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    
    .skill-tag {
      background-color: #eff6ff;
      color: #1d4ed8;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 0.85em;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="sidebar">
      <div class="section">
        <h2 class="section-title">Profile</h2>
        <div class="profile-info">
          <script>
            if (window.__CV_DATA__ && window.__CV_DATA__.instances) {
              const profile = window.__CV_DATA__.instances.find(i => i.type === 'profile');
              if (profile) {
                document.write(`<img src="${profile.data.photo_url || ''}" alt="Profile Photo" />`);
                document.write(`<h3>${profile.data.name || 'Your Name'}</h3>`);
                document.write(`<p>${profile.data.title || ''}</p>`);
                document.write(`<p>${profile.data.email || ''}</p>`);
                document.write(`<p>${profile.data.phone || ''}</p>`);
                document.write(`<p>${profile.data.location || ''}</p>`);
              }
            }
          </script>
        </div>
      </div>
      
      <div class="section">
        <h2 class="section-title">Skills</h2>
        <div class="skills-list">
          <script>
            if (window.__CV_DATA__ && window.__CV_DATA__.instances) {
              const skills = window.__CV_DATA__.instances.find(i => i.type === 'skills');
              if (skills && skills.data) {
                skills.data.forEach(group => {
                  group.items.forEach(skill => {
                    document.write(`<span class="skill-tag">${skill}</span>`);
                  });
                });
              }
            }
          </script>
        </div>
      </div>
    </div>
    
    <div class="main">
      <div class="section">
        <h2 class="section-title">Work Experience</h2>
        <script>
          if (window.__CV_DATA__ && window.__CV_DATA__.instances) {
            const experience = window.__CV_DATA__.instances.find(i => i.type === 'experience');
            if (experience && experience.data) {
              experience.data.forEach(exp => {
                document.write(`<div class="experience-item">`);
                document.write(`<h3 class="experience-title">${exp.position || ''}</h3>`);
                document.write(`<p class="experience-company">${exp.company || ''}, ${exp.start_date || ''} - ${exp.end_date || 'Present'}</p>`);
                document.write(`<p>${exp.description || ''}</p>`);
                document.write(`</div>`);
              });
            }
          }
        </script>
      </div>
      
      <div class="section">
        <h2 class="section-title">Education</h2>
        <script>
          if (window.__CV_DATA__ && window.__CV_DATA__.instances) {
            const education = window.__CV_DATA__.instances.find(i => i.type === 'education');
            if (education && education.data) {
              education.data.forEach(edu => {
                document.write(`<div class="education-item">`);
                document.write(`<h3>${edu.degree || ''}</h3>`);
                document.write(`<p>${edu.institution || ''}</p>`);
                document.write(`<p>${edu.start_date || ''} - ${edu.end_date || ''}${edu.gpa ? ` | GPA: ${edu.gpa}` : ''}</p>`);
                document.write(`</div>`);
              });
            }
          }
        </script>
      </div>
    </div>
  </div>
</body>
</html>
```

## Template Data Access

Your template can access CV data through `window.__CV_DATA__`. Here's how to access different section types:

### Profile Section
```javascript
const profile = window.__CV_DATA__.instances.find(i => i.type === 'profile');
// Access profile fields:
profile.data.name
profile.data.title
profile.data.email
profile.data.phone
profile.data.location
profile.data.summary
```

### Experience Section
```javascript
const experience = window.__CV_DATA__.instances.find(i => i.type === 'experience');
// Access experience entries:
experience.data.forEach(exp => {
  exp.company
  exp.position
  exp.start_date
  exp.end_date
  exp.current
  exp.location
  exp.description
});
```

### Skills Section
```javascript
const skills = window.__CV_DATA__.instances.find(i => i.type === 'skills');
// Access skill groups:
skills.data.forEach(group => {
  group.category
  group.items // array of skill strings
});
```

### Other Sections
Similar patterns apply for education, projects, languages, and certifications sections.

## Styling Your Template

### CSS Custom Properties
Your template can use CSS custom properties for theming:

```css
:root {
  --primary-color: #2563eb;
  --secondary-color: #f8fafc;
  --text-color: #374151;
  --heading-color: #111827;
  --accent-color: #2563eb;
}
```

### Responsive Design
Use media queries to make your template responsive:

```css
@media print {
  body {
    margin: 0;
    padding: 0;
  }
  
  .container {
    width: 100%;
    margin: 0;
  }
}
```

## Template Upload

### File Format
- File extension: `.html` or `.htm`
- File size: Maximum 5MB
- Content type: HTML text/plain

### Upload Process
1. Click "Add Template" in the template selector modal
2. Select your HTML template file
3. Provide a name for your template
4. The template will be saved and appear in your template list

### Best Practices
1. **Keep it simple**: Start with a basic template and add styling progressively
2. **Use CSS variables**: Make it easy to customize colors and fonts
3. **Test thoroughly**: Preview your template with different CV data
4. **Check print preview**: Ensure your template looks good when printed to PDF

## Template Examples

### Minimal Template
A clean, simple template with minimal styling:

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; }
    .header { border-bottom: 2px solid #ccc; padding-bottom: 10px; }
    .section { margin: 20px 0; }
    .section-title { font-weight: bold; }
  </style>
</head>
<body>
  <div class="header">
    <h1 id="name"></h1>
    <p id="title"></p>
  </div>
  <script>
    if (window.__CV_DATA__) {
      const profile = window.__CV_DATA__.instances.find(i => i.type === 'profile');
      if (profile) {
        document.getElementById('name').textContent = profile.data.name || '';
        document.getElementById('title').textContent = profile.data.title || '';
      }
    }
  </script>
</body>
</html>
```

### Two-Column Template
A professional two-column layout:

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    .container { display: flex; gap: 30px; }
    .left { flex: 1; }
    .right { flex: 2; }
    .section { margin-bottom: 20px; }
    .title { font-weight: bold; margin-bottom: 8px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="left">
      <div class="section">
        <h2 class="title">Contact</h2>
        <script>
          if (window.__CV_DATA__) {
            const profile = window.__CV_DATA__.instances.find(i => i.type === 'profile');
            if (profile) {
              document.write(`<p>${profile.data.email}</p>`);
              document.write(`<p>${profile.data.phone}</p>`);
              document.write(`<p>${profile.data.location}</p>`);
            }
          }
        </script>
      </div>
    </div>
    <div class="right">
      <div class="section">
        <h2 class="title">Professional Summary</h2>
        <script>
          if (window.__CV_DATA__) {
            const profile = window.__CV_DATA__.instances.find(i => i.type === 'profile');
            if (profile) {
              document.write(`<p>${profile.data.summary || ''}</p>`);
            }
          }
        </script>
      </div>
    </div>
  </div>
</body>
</html>
```

## Troubleshooting

### Common Issues

1. **Template not loading**: Ensure your HTML file is valid and doesn't have syntax errors
2. **Data not appearing**: Check that you're accessing the correct data structure
3. **Styling not applied**: Verify your CSS is properly loaded and applied
4. **PDF export issues**: Check browser console for JavaScript errors

### Debugging Tips
- Open browser developer tools and check the Console tab
- Use `console.log(window.__CV_DATA__)` to verify data is being passed
- Check Network tab to ensure your template HTML is being loaded
- Use browser screenshot tools to verify template appearance

## Advanced Features

### Custom Section Rendering
You can create custom section rendering logic in your template:

```javascript
function renderSection(instance) {
  const data = instance.data;
  const style = instance.style || {};
  
  const wrapperStyle = {
    fontFamily: style.font || 'inherit',
    color: style.color || 'inherit',
  };
  
  return `
    <div style="${Object.entries(wrapperStyle).map(([k, v]) => `${k}: ${v};`).join('')}">
      <h3 style="fontWeight: ${style.weight || 'normal'}">${instance.title}</h3>
      ${renderSectionData(instance.type, data)}
    </div>
  `;
}
```

### Dynamic Content
You can dynamically load additional data or modify the template based on CV content:

```javascript
if (window.__CV_DATA__.instances.some(i => i.type === 'experience' && i.data.length > 0)) {
  document.body.classList.add('has-experience');
}
```

## Best Practices

1. **Keep it simple initially**: Start with basic HTML and CSS, then add features
2. **Use consistent naming**: Use consistent class names and IDs
3. **Test with real data**: Use actual CV data to test your template
4. **Check print preview**: Ensure your template looks good when printed
5. **Responsive design**: Test on different screen sizes
6. **Accessibility**: Include proper semantic HTML for screen readers

## Getting Help

If you encounter issues with your template:
1. Check the browser console for JavaScript errors
2. Review the template examples above
3. Test with a simple CV entry
4. Contact support if you need assistance with complex template requirements

## Template Versioning

User templates are versioned by the upload timestamp. You can update a template by uploading a new version with the same name (the system will replace the old template).

## Security Notes

- User templates are executed in a sandboxed iframe
- Templates can only access data provided via `window.__CV_DATA__`
- No external network requests are allowed from templates
- Templates are stored securely on the server

## Conclusion

User templates give you complete control over your CV's appearance. Start with a simple template and progressively add features as you become more comfortable with the template format. The built-in system templates (Modern, Classic, Minimal) are always available as a fallback if you need to switch away from a custom template.