import subprocess
import sys
from pathlib import Path

# Windows: CREATE_NO_WINDOW
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

# Paths
EVO_REPO = Path("C:/Users/dell-/hermes-agent-self-evolution")
ANALYSIS_SCRIPT = EVO_REPO / "self_analysis.py"

def main():
    print("⚕ Starting Hermes Self-Analysis...")
    
    try:
        # Run self_analysis.py
        subprocess.run([sys.executable, str(ANALYSIS_SCRIPT)], 
                       cwd=str(EVO_REPO), check=True,
                       creationflags=WIN_FLAGS)
        
        print("✓ Self-analysis complete. Report updated.")
        
    except Exception as e:
        print(f"✗ Self-analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
