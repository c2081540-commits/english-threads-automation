from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPO_ROOT.parent
MASTER_DIR = REPO_ROOT / "data" / "master"
QUIZ_MASTER_DIR = MASTER_DIR / "quiz"
NORMAL_MASTER_DIR = MASTER_DIR / "normal"
QUEUE_DIR = REPO_ROOT / "data" / "queue"
IMAGE_DIR = REPO_ROOT / "artifacts" / "images"
QUESTION_IMAGE_DIR = REPO_ROOT / "assets" / "question_images"
HOOK_CONFIG_PATH = REPO_ROOT / "config" / "quiz_hooks.json"
INSTAGRAM_REPO_ROOT = WORKSPACE_ROOT / "english-instagram-automation"
INSTAGRAM_MASTER_DIR = INSTAGRAM_REPO_ROOT / "data" / "master"


def require_file(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.parent != MASTER_DIR.resolve():
        raise ValueError(f"Master file must be directly under {MASTER_DIR}")
    if not resolved.is_file():
        raise FileNotFoundError(f"Required master file not found: {resolved}")
    return resolved


def require_direct_file(path: Path, expected_dir: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.parent != expected_dir.resolve():
        raise ValueError(f"{label} must be directly under {expected_dir}")
    if not resolved.is_file():
        raise FileNotFoundError(f"Required {label} not found: {resolved}")
    return resolved
