BigAppleRecSports/
│
├── backend/                  # pnpm workspace root
│   ├── packages/
│   │   ├── product-creator/
│   │   ├── variant-manager/
│   │   └── shared/
│   └── tsconfig.base.json
│
├── frontend/                 # Not in pnpm workspace
│   └── next-app/             # Maybe Yarn or npm
│
├── data-tools/               # Python utilities
│   └── waitlist_importer.py
│
├── infra/                    # Terraform, Pulumi, etc.
│
├── .env
├── .gitignore
└── pnpm-workspace.yaml       # Only includes ./backend/packages/**