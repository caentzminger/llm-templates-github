from llm import Template, hookimpl
import yaml
import httpx
import os
import base64


@hookimpl
def register_template_loaders(register):
    register("gh", github_template_loader)


def github_template_loader(template_path: str) -> Template:
    """
    Load a template from GitHub

    Format: username/repo/template_name (without the .yaml extension)
      or username/template_name which means username/llm-templates/template_name
    
    Supports private repositories via GITHUB_TOKEN or LLM_GITHUB_TOKEN environment variable.
    """
    parts = template_path.split("/")
    if len(parts) == 2:
        parts.insert(1, "llm-templates")
    elif len(parts) != 3:
        raise ValueError(
            "GitHub template format should be 'username/repo/template_name' or 'username/template_name'"
        )

    username, repo, template_name = parts
    
    # Check for GitHub token in environment
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("LLM_GITHUB_TOKEN")
    
    # Prepare headers if token is available
    headers = {}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    
    # Try raw.githubusercontent.com first (works for public repos and private with token)
    path = f"{template_name}.yaml"
    raw_url = f"https://raw.githubusercontent.com/{username}/{repo}/main/{path}"
    
    try:
        response = httpx.get(raw_url, headers=headers, follow_redirects=True)
        
        if response.status_code == 200:
            content = response.text
        elif response.status_code == 404 and github_token:
            # If raw URL fails with token, try GitHub API
            api_url = f"https://api.github.com/repos/{username}/{repo}/contents/{path}"
            api_response = httpx.get(api_url, headers=headers)
            
            if api_response.status_code == 200:
                api_data = api_response.json()
                # GitHub API returns base64-encoded content
                content = base64.b64decode(api_data["content"]).decode("utf-8")
            else:
                raise ValueError(
                    f"Template '{template_name}' not found in repository '{username}/{repo}' "
                    f"(API returned HTTP {api_response.status_code})"
                )
        elif response.status_code == 404:
            raise ValueError(
                f"Template '{template_name}' not found in repository '{username}/{repo}'. "
                f"If this is a private repository, set GITHUB_TOKEN or LLM_GITHUB_TOKEN environment variable."
            )
        elif response.status_code == 401:
            raise ValueError(
                f"Authentication failed for repository '{username}/{repo}'. "
                f"Please check your GitHub token."
            )
        else:
            raise ValueError(
                f"Failed to fetch template from '{username}/{repo}' (HTTP {response.status_code})"
            )
    except httpx.HTTPError as ex:
        raise ValueError(f"Failed to fetch template from GitHub: {ex}")

    # Parse YAML and create template
    try:
        loaded = yaml.safe_load(content)
        if isinstance(loaded, str):
            return Template(name=template_path, prompt=loaded)
        else:
            return Template(name=template_path, **loaded)
    except yaml.YAMLError as ex:
        raise ValueError(f"Invalid YAML in GitHub template: {ex}")
