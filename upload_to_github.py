import os
import sys
import json
import base64
import urllib.request
import urllib.error

REPO_OWNER = "Raziyah-Ali"
REPO_NAME = "2025EM1300257-VAHAN-RTO-Vehicle-Registration-Analytics"
BRANCH = "main"

# Files and folders to skip
EXCLUDE_DIRS = {'.git', '.kilo', '__pycache__', '.pytest_cache', 'venv', 'env', '.venv', '.idea', '.vscode'}
EXCLUDE_FILES = {'.DS_Store', 'upload_to_github.py'}

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

def api_request(url, method="GET", data=None, token=None):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as res:
            resp_body = res.read().decode("utf-8")
            return json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"API Error ({e.code}) at {url}: {err_msg}")
        raise

def upload_files(token):
    print(f"Uploading files to GitHub repository: {REPO_OWNER}/{REPO_NAME}...")
    
    # 1. Collect all files
    files_to_upload = []
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f in EXCLUDE_FILES:
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
            files_to_upload.append((rel_path, full_path))
            
    print(f"Found {len(files_to_upload)} files to upload.")
    
    # 2. Create Blobs for each file
    tree_items = []
    for rel_path, full_path in files_to_upload:
        with open(full_path, 'rb') as fp:
            content = fp.read()
        
        # Check if text or binary
        try:
            content_str = content.decode('utf-8')
            blob_data = {
                "content": content_str,
                "encoding": "utf-8"
            }
        except UnicodeDecodeError:
            blob_data = {
                "content": base64.b64encode(content).decode('ascii'),
                "encoding": "base64"
            }
            
        print(f"  Uploading blob for {rel_path} ({len(content)} bytes)...")
        blob_res = api_request(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/blobs",
            method="POST",
            data=blob_data,
            token=token
        )
        
        tree_items.append({
            "path": rel_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_res["sha"]
        })
        
    # 3. Create Tree
    print("Creating git tree...")
    tree_res = api_request(
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees",
        method="POST",
        data={"tree": tree_items},
        token=token
    )
    tree_sha = tree_res["sha"]
    
    # 4. Check if reference main branch exists
    parent_commits = []
    try:
        ref_res = api_request(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/ref/heads/{BRANCH}",
            method="GET",
            token=token
        )
        parent_commits = [ref_res["object"]["sha"]]
    except Exception:
        print(f"Branch '{BRANCH}' does not exist yet. Creating initial commit.")
        
    # 5. Create Commit
    print("Creating git commit...")
    commit_data = {
        "message": "Initial commit: VAHAN RTO Vehicle Registration Analytics pipeline and Streamlit dashboard",
        "tree": tree_sha,
        "parents": parent_commits
    }
    commit_res = api_request(
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/commits",
        method="POST",
        data=commit_data,
        token=token
    )
    commit_sha = commit_res["sha"]
    
    # 6. Update or Create Ref
    print(f"Updating branch 'refs/heads/{BRANCH}' to {commit_sha}...")
    if parent_commits:
        api_request(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/heads/{BRANCH}",
            method="PATCH",
            data={"sha": commit_sha, "force": True},
            token=token
        )
    else:
        api_request(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/refs",
            method="POST",
            data={"ref": f"refs/heads/{BRANCH}", "sha": commit_sha},
            token=token
        )
        
    print(f"\nSUCCESS! All files have been uploaded to:")
    print(f"https://github.com/{REPO_OWNER}/{REPO_NAME}")

if __name__ == "__main__":
    tok = get_token()
    upload_files(tok)
