import subprocess
import sys
from pathlib import Path

# Windows: CREATE_NO_WINDOW
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

# Paths
REPO_ROOT = Path("C:/Users/dell-/AppData/Local/hermes/hermes-agent")
RELEASE_SCRIPT = REPO_ROOT / "scripts" / "release.py"

def main():
    print("⚕ Starting Hermes Auto-Release Bot...")
    
    try:
        # 1. Fetch latest changes to ensure we know about all tags/commits
        subprocess.run(["git", "fetch", "origin", "--tags"], cwd=str(REPO_ROOT), check=True, creationflags=WIN_FLAGS)
        
        # 2. Get latest tag
        tag_result = subprocess.run(["git", "describe", "--tags", "--abbrev=0"], 
                                   cwd=str(REPO_ROOT), capture_output=True, text=True,
                                   creationflags=WIN_FLAGS)
        
        if tag_result.returncode != 0:
            print("⚠ No tags found. This might be the first release.")
            latest_tag = None
        else:
            latest_tag = tag_result.stdout.strip()
            print(f"→ Latest tag found: {latest_tag}")
        
        # 3. Check for commits between latest tag and HEAD
        if latest_tag:
            commits_result = subprocess.run(["git", "rev-list", f"{latest_tag}..HEAD", "--count"],
                                           cwd=str(REPO_ROOT), capture_output=True, text=True,
                                           creationflags=WIN_FLAGS)
            count = int(commits_result.stdout.strip())
        else:
            count = 1 # Assume there's something to release
            
        if count == 0:
            print("✓ No new commits since last release.")
            return

        print(f"→ Found {count} new commit(s). Bumping version and publishing...")
        
        # 4. Run release.py
        # We use the python executable from the current environment, 
        # but release.py might need the hermes venv if it imports anything from hermes_cli.
        # However, release.py seems mostly standalone.
        subprocess.run([sys.executable, str(RELEASE_SCRIPT), "--bump", "patch", "--publish"], 
                       cwd=str(REPO_ROOT), check=True, creationflags=WIN_FLAGS)
        
        print("✓ Auto-release successful!")
        
    except Exception as e:
        print(f"✗ Auto-release failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
