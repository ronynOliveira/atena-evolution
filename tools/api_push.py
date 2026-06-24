#!/usr/bin/env python3
import urllib.request, json, subprocess, sys

def get_github_token():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        value, _ = winreg.QueryValueEx(key, "GITHUB_TOKEN")
        winreg.CloseKey(key)
        return value
    except Exception as e:
        print(f"Registry error: {e}")
        return None

def api_request(url, token, method='GET', data=None):
    if data:
        payload = json.dumps(data).encode('utf-8')
    else:
        payload = None
    req = urllib.request.Request(url, data=payload, method=method)
    req.add_header('Authorization', f'token {token}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def push_via_api(token):
    repo = 'ronynOliveira/atena-evolution'
    
    # Get latest commit on main
    print("Fetching latest commit on main...")
    commit = api_request(f'https://api.github.com/repos/{repo}/commits/main', token)
    remote_sha = commit['sha']
    print(f"  Remote main: {remote_sha[:12]}")
    
    # Get local HEAD
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True, text=True, timeout=10
    )
    local_sha = result.stdout.strip()
    print(f"  Local HEAD: {local_sha[:12]}")
    
    if local_sha == remote_sha:
        print("Already in sync!")
        return True
    
    # Push: update ref to local HEAD
    print("Pushing to main...")
    ref_data = {'sha': local_sha, 'force': False}
    try:
        result = api_request(
            f'https://api.github.com/repos/{repo}/git/refs/heads/main',
            token, method='PATCH', data=ref_data
        )
        print(f"  Push successful! New SHA: {result['object']['sha'][:12]}")
        return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  Push failed: {e.code}")
        if '422' in str(e.code):
            print("  Likely: divergent branches. Trying force push...")
            return force_push(token, repo, local_sha)
        print(f"  {error_body[:300]}")
        return False

def force_push(token, repo, local_sha):
    """Force push as fallback (safe when we know what we're doing)."""
    ref_data = {'sha': local_sha, 'force': True}
    result = api_request(
        f'https://api.github.com/repos/{repo}/git/refs/heads/main',
        token, method='PATCH', data=ref_data
    )
    print(f"  Force push successful! SHA: {result['object']['sha'][:12]}")
    return True

def main():
    token = get_github_token()
    if not token:
        print("ERROR: GITHUB_TOKEN not found in registry")
        sys.exit(1)
    print(f"Token: {token[:8]}...{token[-5:]}")
    success = push_via_api(token)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
