import os
from datetime import datetime
import re

def save_brief(query: str, content: str) -> str:
    """Saves the generated markdown brief to the outputs folder."""
    outputs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    # ensure .gitkeep is there
    with open(os.path.join(outputs_dir, ".gitkeep"), "w") as f:
        pass
        
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', query).strip('_').lower()
    
    filename = f"brief_{date_str}_{slug}.md"
    filepath = os.path.join(outputs_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    return filepath
