import os
from pathlib import Path
from email.message import EmailMessage

MOCK_CANDIDATES = [
    {
        "name": "Sarah Chen",
        "email": "sarah.chen@example.com",
        "github": "tiangolo",
        "linkedin": "https://linkedin.com/in/sarahchen-dev",
        "subject": "Application - Sarah Chen - Senior Backend Engineer",
        "body": "Hi Hiring Team,\n\nPlease find attached my resume for the Senior Backend Engineer position.\nGitHub: https://github.com/tiangolo\nLinkedIn: https://linkedin.com/in/sarahchen-dev\n\nLooking forward to hearing from you,\nSarah"
    },
    {
        "name": "Rohan Verma",
        "email": "rohan.verma@example.com",
        "github": "octocat",
        "linkedin": "https://linkedin.com/in/rohanverma",
        "subject": "Application - Rohan Verma - Full Stack Python Lead",
        "body": "Hi Team,\n\nI am applying for the Full Stack Python Lead role. I have 5 years experience building scalable systems in Python and React.\nGitHub: https://github.com/octocat\nLinkedIn: https://linkedin.com/in/rohanverma\n\nRegards,\nRohan"
    },
    {
        "name": "Alex Rivera",
        "email": "alex.rivera@example.com",
        "github": "yyx990803",
        "linkedin": "https://linkedin.com/in/alexrivera-tech",
        "subject": "Frontend Engineer Application - Alex Rivera",
        "body": "Hello,\n\nSubmitting my application for the Frontend Engineer position. You can inspect my open source UI libraries and contributions on GitHub: https://github.com/yyx990803.\n\nBest,\nAlex"
    },
    {
        "name": "Emily Davis",
        "email": "emily.davis@example.com",
        "github": "nonexistent_github_dev_999",
        "linkedin": "https://linkedin.com/in/emilydavis",
        "subject": "Intern Application - Emily Davis",
        "body": "Dear Hiring Manager,\n\nI am excited to apply for the Software Internship. I recently graduated in Computer Science. My GitHub profile is: https://github.com/nonexistent_github_dev_999.\n\nThank you,\nEmily"
    },
    {
        "name": "Priya Patel",
        "email": "priya.patel@example.com",
        "github": "tiangolo",
        "linkedin": "https://linkedin.com/in/priyapatel-eng",
        "subject": "Application - Priya Patel - Cloud & API Architect",
        "body": "Hi,\n\nAttached is my CV for the Cloud & API Architect role. My GitHub profile with active REST and container projects is at https://github.com/tiangolo.\n\nThanks,\nPriya"
    },
    {
        "name": "Liam Wilson",
        "email": "liam.wilson@example.com",
        "github": "octocat",
        "linkedin": "https://linkedin.com/in/liamwilson",
        "subject": "Application - Liam Wilson - Senior Microservices Developer",
        "body": "Dear Team,\n\nApplying for Senior Microservices role with 4 years claimed Python experience. Check my profile: https://github.com/octocat.\n\nLiam"
    },
    {
        "name": "Ananya Gupta",
        "email": "ananya.gupta@example.com",
        "github": "tiangolo",
        "linkedin": "https://linkedin.com/in/ananyagupta",
        "subject": "Resume Submission: Ananya Gupta - Python & Systems Engineer",
        "body": "Hi there,\n\nExcited to submit my candidacy. View my code repository: https://github.com/tiangolo.\n\nBest,\nAnanya"
    },
    {
        "name": "Marcus Vance",
        "email": "marcus.vance@example.com",
        "github": "octocat",
        "linkedin": "https://linkedin.com/in/marcusvance",
        "subject": "Application - Marcus Vance - Full Stack Developer",
        "body": "Hello,\n\nSharing my resume for consideration. GitHub is https://github.com/octocat.\n\nMarcus"
    },
    {
        "name": "Tara Sharma",
        "email": "tara.sharma@example.com",
        "github": "tiangolo",
        "linkedin": "https://linkedin.com/in/tarasharma",
        "subject": "Application - Tara Sharma - Backend API Specialist",
        "body": "Hi Recruiter,\n\nAttached is my resume. Active code samples on GitHub: https://github.com/tiangolo.\n\nTara"
    },
    {
        "name": "Kevin Miller",
        "email": "kevin.miller@example.com",
        "github": "none",
        "linkedin": "https://linkedin.com/in/kevinmiller",
        "subject": "Application - Kevin Miller - Software Engineer",
        "body": "Hi,\n\nApplying for the general software engineer opening. Resume attached. Currently private repositories.\n\nKevin"
    }
]

def generate_mock_eml_files(output_dir: str = "mock_inbox"):
    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    sample_pdf_bytes = b""
    if os.path.exists("sample_resume.pdf"):
        with open("sample_resume.pdf", "rb") as f:
            sample_pdf_bytes = f.read()

    for idx, c in enumerate(MOCK_CANDIDATES):
        msg = EmailMessage()
        msg["Subject"] = c["subject"]
        msg["From"] = f"{c['name']} <{c['email']}>"
        msg["To"] = "screening@company.com"
        msg.set_content(c["body"])

        if sample_pdf_bytes:
            msg.add_attachment(
                sample_pdf_bytes,
                maintype="application",
                subtype="pdf",
                filename=f"{c['name'].replace(' ', '_').lower()}_resume.pdf"
            )

        file_path = out / f"app_{idx+1}_{c['name'].replace(' ', '_').lower()}.eml"
        with open(file_path, "wb") as f:
            f.write(msg.as_bytes())

    print(f"✅ Generated 10 mock .eml candidate application files in '{output_dir}/'")

if __name__ == "__main__":
    generate_mock_eml_files()
