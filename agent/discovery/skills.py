"""Skill discovery for Claude Agent SDK.

Discovers and loads skills from .claude/skills/ directory.
"""
from pathlib import Path

from agent import PROJECT_ROOT
from agent.display import print_warning


def discover_skills() -> list[dict]:
    """Discover skills from .claude/skills/ directory.

    Returns:
        List of dictionaries with skill name and description.
    """
    skills_dir = PROJECT_ROOT / ".claude" / "skills"
    skills_data = []

    if not skills_dir.exists():
        return skills_data

    for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
        skill_name = skill_path.parent.name
        description = "No description"
        try:
            with open(skill_path, 'r') as f:
                content = f.read()
                # Parse YAML frontmatter for description
                if content.startswith('---'):
                    desc_start = content.find('description:')
                    if desc_start != -1:
                        desc_line_start = content.find(':', desc_start) + 1
                        desc_line_end = content.find('\n', desc_line_start)
                        description = content[desc_line_start:desc_line_end].strip().strip('"')
            # Truncate long descriptions
            if len(description) > 80:
                description = description[:77] + "..."
            skills_data.append({
                "name": skill_name,
                "description": description
            })
        except Exception as e:
            print_warning(f"Failed to load skill '{skill_name}': {e}")
    return skills_data
