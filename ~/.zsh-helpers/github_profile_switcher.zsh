# GitHub Profile Switcher - Unified SSH, GPG, and Token Management
# Consolidates git identity, SSH keys, GPG signing, and GitHub tokens by organization

# Organization profile switching based on current directory
switch_github_profile_by_org() {
  local quiet="$1"
  local current_dir org ssh_key gpg_key gh_token git_email git_name message
  current_dir=$(pwd)

  # Determine organization from path
  if [[ "$current_dir" == */Documents/BARS_Github/* || "$current_dir" == */Documents/git-projects/bars/* ]]; then
    org="bars"
    ssh_key="$HOME/.config/bars/bars_ssh_signing_key"
    gpg_key=$(cat "$HOME/.config/bars/bars_gpg_signing_key" 2>/dev/null)
    gh_token=$(cat "$HOME/.config/bars/bars_gh_token" 2>/dev/null)
    git_email="jprandazzo@icloud.com"
    git_name="Joe Randazzo"
    message="⚾️ Switched to BARS profile"
  elif [[ "$current_dir" == */Documents/Engine_Github/* || "$current_dir" == */Documents/git-projects/engine/* ]]; then
    org="engine"
    ssh_key="$HOME/.config/engine/engine_ssh_signing_key"
    gpg_key=$(cat "$HOME/.config/engine/engine_gpg_signing_key" 2>/dev/null)
    gh_token=$(cat "$HOME/.config/engine/engine_gh_token" 2>/dev/null)
    git_email="jrandazzo@moneylion.com"
    git_name="Joe Randazzo"
    message="🦁 Switched to Engine profile"
  else
    # Default to engine
    org="engine"
    ssh_key="$HOME/.config/engine/engine_ssh_signing_key"
    gpg_key=$(cat "$HOME/.config/engine/engine_gpg_signing_key" 2>/dev/null)
    gh_token=$(cat "$HOME/.config/engine/engine_gh_token" 2>/dev/null)
    git_email="jrandazzo@moneylion.com"
    git_name="Joe Randazzo"
    message="🔧 Using default (Engine) profile"
  fi

  # Set SSH identity for git operations
  local ssh_cmd="ssh -i $ssh_key -o IdentitiesOnly=yes"
  if [[ "${GIT_SSH_COMMAND-}" != "$ssh_cmd" ]]; then
    export GIT_SSH_COMMAND="$ssh_cmd"
  fi

  # Set GitHub token for CLI operations
  if [[ -n "$gh_token" && "${GH_TOKEN-}" != "$gh_token" ]]; then
    export GH_TOKEN="$gh_token"
    export GITHUB_TOKEN="$gh_token"
  fi

  # Set git user identity and org-specific settings (local repo only)
  if git rev-parse --git-dir >/dev/null 2>&1; then
    git config user.email "$git_email"
    git config user.name "$git_name"
    if [[ -n "$gpg_key" ]]; then
      git config user.signingkey "$gpg_key"
      git config commit.gpgsign true
      git config tag.gpgSign true
    fi
    
    # Set org-specific URL rewrites
    if [[ "$org" == "bars" ]]; then
      git config url."git@github-bars:barswebadmin/".insteadOf "git@github.com:barswebadmin/"
    elif [[ "$org" == "engine" ]]; then
      git config url."git@github-engine:EVENFinancial/".insteadOf "git@github.com:EVENFinancial/"
    fi
  fi

  # Report changes
  [[ -z "$quiet" ]] && echo "$message"
}

# Hook to run on directory change
autoload -U add-zsh-hook
add-zsh-hook chpwd switch_github_profile_by_org

# Initialize on shell startup (silent)
switch_github_profile_by_org quiet
