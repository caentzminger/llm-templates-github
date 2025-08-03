import pytest
from llm_templates_github import github_template_loader
from llm import Template
import yaml
import os
import json
import base64


@pytest.mark.parametrize(
    "template_path, expected_url, yaml_content_dict",
    [
        # Test case 1: Full path (user/repo/template) with simple string content
        (
            "testuser/testrepo/simple",
            "https://raw.githubusercontent.com/testuser/testrepo/main/simple.yaml",
            "Just a simple prompt.",
        ),
        # Test case 2: Short path (user/template) with simple string content
        (
            "testuser/short",
            "https://raw.githubusercontent.com/testuser/llm-templates/main/short.yaml",
            "Shorthand prompt.",
        ),
        # Test case 3: Full path with dictionary content
        (
            "dev/coolstuff/complex",
            "https://raw.githubusercontent.com/dev/coolstuff/main/complex.yaml",
            {
                "prompt": "Complex prompt with {{variable}}",
                "system": "You are helpful.",
                "model": "gpt-4",
            },
        ),
        # Test case 4: Short path with dictionary content
        (
            "dev/dict_template",
            "https://raw.githubusercontent.com/dev/llm-templates/main/dict_template.yaml",
            {"prompt": "Another dict prompt", "system": "Be concise"},
        ),
    ],
)
def test_github_loader_success(
    httpx_mock, template_path, expected_url, yaml_content_dict
):
    """Tests successful loading of templates via different paths and content types."""
    if isinstance(yaml_content_dict, dict):
        yaml_string = yaml.dump(yaml_content_dict)
        expected_template = Template(name=template_path, **yaml_content_dict)
    else:  # It's a string
        yaml_string = yaml_content_dict
        expected_template = Template(name=template_path, prompt=yaml_content_dict)

    httpx_mock.add_response(
        url=expected_url, method="GET", text=yaml_string, status_code=200
    )

    template = github_template_loader(template_path)

    assert template == expected_template
    # Check specific fields if __eq__ is not comprehensive
    assert template.name == template_path
    if isinstance(yaml_content_dict, dict):
        assert template.prompt == yaml_content_dict.get("prompt")
        assert template.system == yaml_content_dict.get("system")
        assert template.model == yaml_content_dict.get("model")
    else:
        assert template.prompt == yaml_content_dict
        assert template.system is None  # Assuming default is None
        assert template.model is None  # Assuming default is None


def test_private_repo_without_token(httpx_mock):
    """Test that accessing private repo without token gives helpful error."""
    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/org/private-repo/main/template.yaml",
        method="GET",
        status_code=404
    )
    
    with pytest.raises(ValueError) as exc_info:
        github_template_loader("org/private-repo/template")
    
    assert "private repository" in str(exc_info.value).lower()
    assert "GITHUB_TOKEN" in str(exc_info.value)


def test_private_repo_with_token_raw_url(httpx_mock, monkeypatch):
    """Test successful access to private repo via raw URL with token."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token-123")
    
    template_content = "Private template content"
    
    def custom_matcher(request):
        return (
            request.url == "https://raw.githubusercontent.com/org/private-repo/main/secret.yaml"
            and request.headers.get("Authorization") == "Bearer test-token-123"
        )
    
    httpx_mock.add_response(
        match_headers={"Authorization": "Bearer test-token-123"},
        url="https://raw.githubusercontent.com/org/private-repo/main/secret.yaml",
        text=template_content,
        status_code=200
    )
    
    template = github_template_loader("org/private-repo/secret")
    
    assert template.name == "org/private-repo/secret"
    assert template.prompt == template_content


def test_private_repo_with_token_api_fallback(httpx_mock, monkeypatch):
    """Test fallback to GitHub API when raw URL fails."""
    monkeypatch.setenv("LLM_GITHUB_TOKEN", "test-token-456")
    
    template_content = {"prompt": "API template", "system": "Be helpful"}
    yaml_content = yaml.dump(template_content)
    encoded_content = base64.b64encode(yaml_content.encode()).decode()
    
    # First request to raw URL fails
    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/org/private/main/api-template.yaml",
        match_headers={"Authorization": "Bearer test-token-456"},
        status_code=404
    )
    
    # Second request to API succeeds
    api_response = {
        "content": encoded_content,
        "encoding": "base64",
        "name": "api-template.yaml"
    }
    
    httpx_mock.add_response(
        url="https://api.github.com/repos/org/private/contents/api-template.yaml",
        match_headers={"Authorization": "Bearer test-token-456"},
        json=api_response,
        status_code=200
    )
    
    template = github_template_loader("org/private/api-template")
    
    assert template.name == "org/private/api-template"
    assert template.prompt == template_content["prompt"]
    assert template.system == template_content["system"]


def test_authentication_failure(httpx_mock, monkeypatch):
    """Test handling of authentication failures."""
    monkeypatch.setenv("GITHUB_TOKEN", "invalid-token")
    
    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/org/repo/main/template.yaml",
        status_code=401
    )
    
    with pytest.raises(ValueError) as exc_info:
        github_template_loader("org/repo/template")
    
    assert "Authentication failed" in str(exc_info.value)


def test_both_env_vars(httpx_mock, monkeypatch):
    """Test that GITHUB_TOKEN takes precedence over LLM_GITHUB_TOKEN."""
    monkeypatch.setenv("GITHUB_TOKEN", "primary-token")
    monkeypatch.setenv("LLM_GITHUB_TOKEN", "secondary-token")
    
    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/user/repo/main/test.yaml",
        match_headers={"Authorization": "Bearer primary-token"},
        text="test content",
        status_code=200
    )
    
    template = github_template_loader("user/repo/test")
    assert template.prompt == "test content"


def test_api_failure_with_token(httpx_mock, monkeypatch):
    """Test proper error when both raw and API URLs fail."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    
    # Raw URL fails
    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/org/repo/main/missing.yaml",
        status_code=404
    )
    
    # API also fails
    httpx_mock.add_response(
        url="https://api.github.com/repos/org/repo/contents/missing.yaml",
        status_code=404
    )
    
    with pytest.raises(ValueError) as exc_info:
        github_template_loader("org/repo/missing")
    
    assert "not found" in str(exc_info.value).lower()
    assert "API returned HTTP 404" in str(exc_info.value)
