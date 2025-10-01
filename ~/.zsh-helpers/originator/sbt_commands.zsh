# Originator SBT Commands and Startup Helpers
# Provides utilities for starting and managing Originator SBT processes

# Kill all SBT processes and clean up
killsbt() {
  set +e
  pkill -f '[s]btn' 2>/dev/null
  pkill -f '[s]bt-launch' 2>/dev/null
  pkill -f '[s]bt.Defaults' 2>/dev/null
  pkill -f '[p]lay.core.server' 2>/dev/null
  pkill -f '[p]lay.core.server.ProdServerStart' 2>/dev/null
  pkill -f '[p]lay.core.server.DevServerStart' 2>/dev/null
  lsof -tiTCP:9000 -sTCP:LISTEN 2>/dev/null | xargs -r kill -9
  lsof -tiTCP:9443 -sTCP:LISTEN 2>/dev/null | xargs -r kill -9
  find "$HOME/Documents/git-projects/engine/originator" "$PWD" -type f -name RUNNING_PID -maxdepth 6 -print -exec rm -f {} \; 2>/dev/null
  rm -rf ~/.sbt/1.0/server ~/.sbt/.sbtn/server 2>/dev/null
  echo "sbt/play stopped; ports cleared; RUNNING_PID removed."
}

# Start Originator implementation
_start_originator_impl() {
  local env="$1"
  
  # Common setup
  killsbt
  colima start

  # JVM options for sbt
  export SBT_OPTS="-Xms1G -Xmx2G -XX:+ClassUnloading -XX:+UseG1GC -XX:+UseStringDeduplication"

  # Environment-specific configuration
  case "$env" in
    "prod")
      # Export prod environment variables
      source <(chamber export --format dotenv originator-prod | awk '{print "export "$0}')
      export FINANCE_URL=https://api.evenfinancial.com/finance
      export ORIGINATOR_BASE_URL=https://api.evenfinancial.com/originator
      export PARTNER_DATA_BASE_URL=https://api.evenfinancial.com/partnerData
      export SVC_LEAD_URL=https://api.evenfinancial.com
      export THIRD_PARTY_DATA_URL=https://api.evenfinancial.com/third-party-data
      export ML_PROXY_URL=https://api.evenfinancial.com/mlProxy
      export PROFILE_BASE_URL=https://api.evenfinancial.com/profile
      export LIFE_INSURANCE_BASE_URL=https://api.evenfinancial.com/lifeInsurance
      export AUTH_BASE_URL=https://api.evenfinancial.com/auth

      # Go to repo and start sbt svc with prod-local config
      cd ~/Documents/git-projects/engine/originator || return
      sbt "project svc" 'start -Dconfig.resource=prod-local.conf -Dlogger.resource=logback-test.xml'
      ;;
    "dev")
      # Load dev environment vars from chamber
      source <(chamber export --format dotenv originator-dev | awk '{print "export "$0}')

      # Go to repo and start sbt svc with dev-local config
      cd ~/Documents/git-projects/engine/originator || return
      sbt "project svc" 'start -Dconfig.resource=dev-local.conf -Duser.timezone=UTC'
      ;;
    *)
      echo "❌ Invalid environment: $env. Use 'dev' or 'prod'"
      return 1
      ;;
  esac
}
