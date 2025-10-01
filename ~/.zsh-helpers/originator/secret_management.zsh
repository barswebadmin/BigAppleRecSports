# Originator Secret Management Helpers
# Provides completion and utilities for creating secrets in Engine/Originator

# Main secret creation function
_originator_create_secret_impl() {
  ensure_network
  ./scripts/create_secret.sh "$1" "$2" "$3"
}

# Completion function for originator_create_secret
_originator_create_secret() {
  local context state line
  typeset -A opt_args

  _arguments -C \
    '1:environment:(dev prod)' \
    '2:config_key:->config_key' \
    '3:value:_files'

  case $state in
    config_key)
      local environment=$words[2]
      local config_file="/Users/jrandazzo/Documents/git-projects/engine/originator/modules/svc/conf/${environment}-base.conf"
      
      if [[ -f "$config_file" ]]; then
        local current_key="$words[3]"
        
        if [[ "$current_key" == *.* ]]; then
          # Handle nested keys
          _complete_nested_key "$config_file" "$current_key"
        else
          # Handle top-level keys
          local keys=($(grep -E '^[a-zA-Z][a-zA-Z0-9]*\s*\{' "$config_file" | sed 's/\s*{.*$//' | sort))
          if [[ ${#keys[@]} -gt 0 ]]; then
            compadd -S '' $keys
          fi
        fi
      fi
      ;;
  esac
}

# Helper for nested key completion
_complete_nested_key() {
  local config_file="$1"
  local current_key="$2"
  
  # Split by dots
  local -a key_parts
  key_parts=(${(s:.:)current_key})
  local parent_key="${key_parts[1]}"
  local current_suffix="${current_key#*.}"
  
  # Find the parent section
  local section_start=$(grep -n "^${parent_key}\s*{" "$config_file" | head -1 | cut -d: -f1)
  
  if [[ -n "$section_start" ]]; then
    # Extract keys from the section (look for 2-space indented keys)
    local -a nested_keys
    nested_keys=($(sed -n "${section_start},$((section_start + 20))p" "$config_file" | \
      grep -E '^\s\s[a-zA-Z][a-zA-Z0-9]*\s*[=\{]' | \
      sed 's/^\s\s//' | \
      sed 's/\s*[=\{].*$//' | \
      sort))
    
    # Filter keys that start with the current suffix
    local -a filtered_keys
    for key in "${nested_keys[@]}"; do
      if [[ "$key" == ${current_suffix}* ]]; then
        filtered_keys+=("${parent_key}.${key}")
      fi
    done
    
    if [[ ${#filtered_keys[@]} -gt 0 ]]; then
      compadd -S '' $filtered_keys
    fi
  fi
}

# Register the completion function
compdef _originator_create_secret originator_create_secret
