import os
import sys
import subprocess

REPO_URL = "https://github.com/Raziyah-Ali/2025EM1300257-VAHAN-RTO-Vehicle-Registration-Analytics.git"
BRANCH = "main"

def get_token():
    token = os.environ.get("GITHUB_TOKEN")
    if not token and len(sys.argv) > 1:
        token = sys.argv[1]
    if not token:
        print("Error: GitHub Personal Access Token (PAT) is required.")
        print("Usage:")
        print("  python upload_to_github.py <YOUR_GITHUB_TOKEN>")
        print("  or set environment variable GITHUB_TOKEN")
        sys.exit(1)
    return token

def push_with_git(token):
    git_exe = os.path.expanduser('~/.mingit/cmd/git.exe')
    if not os.path.exists(git_exe):
        git_exe = "git"
        
    cwd = os.path.dirname(os.path.abspath(__file__))
    
    # URL with token for authentication
    authenticated_url = REPO_URL.replace("https://", f"https://{token}@")
    
    print(f"Pushing all files to branch '{BRANCH}' on GitHub...")
    try:
        cmd = [git_exe, "push", "--set-upstream", authenticated_url, f"{BRANCH}:{BRANCH}", "--force"]
        out = subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT)
        print(out.decode())
        print("\n==========================================")
        print(" SUCCESS! All files uploaded successfully!")
        print(" View your repository here:")
        print(" https://github.com/Raziyah-Ali/2025EM1300257-VAHAN-RTO-Vehicle-Registration-Analytics")
        print("==========================================")
    except subprocess.CalledProcessError as e:
        print("Error pushing to GitHub:")
        print(e.output.decode())
        sys.exit(1)

if __name__ == "__main__":
    tok = get_token()
    push_with_git(tok)
