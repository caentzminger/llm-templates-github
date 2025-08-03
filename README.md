# llm-templates-github

[![PyPI](https://img.shields.io/pypi/v/llm-templates-github.svg)](https://pypi.org/project/llm-templates-github/)
[![Changelog](https://img.shields.io/github/v/release/simonw/llm-templates-github?include_prereleases&label=changelog)](https://github.com/simonw/llm-templates-github/releases)
[![Tests](https://github.com/simonw/llm-templates-github/actions/workflows/test.yml/badge.svg)](https://github.com/simonw/llm-templates-github/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/llm-templates-github/blob/main/LICENSE)

Load LLM templates from GitHub repositories

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).
```bash
llm install llm-templates-github
```
## Usage

To use the template from `templatename.yaml` in the `https://github.com/username/llm-templates` repo:

```bash
llm -t gh:username/templatename
```

e.g. to try [this summarize.yaml](https://github.com/simonw/llm-templates/blob/main/summarize.yaml) template:
```bash
curl -L https://llm.datasette.io/ | llm -t gh:simonw/summarize
```

### Private Repository Support

This plugin supports loading templates from private GitHub repositories. To use this feature, you need to provide a GitHub personal access token via environment variable:

```bash
export GITHUB_TOKEN="your-github-token"
# or
export LLM_GITHUB_TOKEN="your-github-token"
```

Then you can use templates from private repositories just like public ones:

```bash
llm -t gh:yourorg/private-repo/template-name
```

#### Creating a GitHub Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token" (classic or fine-grained)
3. For classic tokens: Select the `repo` scope
4. For fine-grained tokens: Grant "Contents" repository permissions for the repositories you want to access
5. Copy the token and set it as an environment variable

**Security Note**: Keep your GitHub token secure and never commit it to version control.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd llm-templates-github
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
llm install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
