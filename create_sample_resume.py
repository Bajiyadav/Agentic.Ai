import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_sample_resume(output_path: str = "sample_resume.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#334155")
    )
    
    story = []
    
    # Header
    story.append(Paragraph("Aarav Sharma", title_style))
    story.append(Paragraph("Email: aarav.sharma.dev@example.com | Phone: +91 98765 43210 | GitHub: https://github.com/octocat", subtitle_style))
    story.append(Spacer(1, 4))
    
    # Summary
    story.append(Paragraph("Professional Summary", section_style))
    story.append(Paragraph(
        "Software Engineer with 3+ years of experience designing and scaling web services, cloud infrastructure, "
        "and data pipelines. Proven track record in developing high-throughput REST APIs with Python and FastAPI, "
        "and crafting interactive frontend applications using TypeScript and React.",
        body_style
    ))
    story.append(Spacer(1, 8))
    
    # Technical Skills
    story.append(Paragraph("Technical Skills", section_style))
    skills_text = (
        "<b>Languages:</b> Python, JavaScript, TypeScript, SQL, Bash<br/>"
        "<b>Frameworks & Web:</b> FastAPI, Django, React, Next.js, Node.js<br/>"
        "<b>Databases & Caching:</b> PostgreSQL, Redis, MongoDB<br/>"
        "<b>DevOps & Tools:</b> Docker, Kubernetes, Git, GitHub Actions, AWS, Linux"
    )
    story.append(Paragraph(skills_text, body_style))
    story.append(Spacer(1, 8))
    
    # Work Experience
    story.append(Paragraph("Professional Experience", section_style))
    exp1_title = "<b>Software Engineer</b> — TechNova Solutions (2022 – Present)"
    exp1_bullets = (
        "• Architected backend microservices in Python & FastAPI serving over 150,000 daily active users.<br/>"
        "• Spearheaded frontend redesign using React and TypeScript, decreasing page load time by 38%.<br/>"
        "• Containerized 12 core services using Docker and configured automated CI/CD workflows via GitHub Actions.<br/>"
        "• Optimized PostgreSQL database queries and connection pooling, reducing p99 response latencies by 45%."
    )
    story.append(Paragraph(exp1_title, body_style))
    story.append(Paragraph(exp1_bullets, body_style))
    story.append(Spacer(1, 8))
    
    # Projects
    story.append(Paragraph("Featured Projects", section_style))
    proj_text = (
        "<b>Distributed Task Queue Engine:</b> Built a lightweight task queue in Python and Redis featuring automatic retry policies and worker thread autoscaling.<br/>"
        "<b>Real-time Analytics Dashboard:</b> Created an event tracking dashboard using Next.js, WebSockets, and TailwindCSS for live metrics visualization."
    )
    story.append(Paragraph(proj_text, body_style))
    
    doc.build(story)
    print(f"✅ Generated sample resume PDF at: {output_path}")

if __name__ == "__main__":
    generate_sample_resume()
