#!/bin/bash

set -euo pipefail
cd "$(dirname "$0")"

ROOT_DIR=".."

echo "Checking for duplicate function signatures in GAS projects..."

NODE=$(command -v node || true)
if [ -z "$NODE" ]; then
  echo "Node.js is required to run this check." >&2
  exit 1
fi

node - <<'NODE'
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

function listProjects(dir) {
  const projectsDir = path.join(dir, 'projects');
  if (!fs.existsSync(projectsDir)) return [];
  return fs.readdirSync(projectsDir).filter(d => fs.statSync(path.join(projectsDir, d)).isDirectory());
}

function walk(dir, files=[]) {
  for (const entry of fs.readdirSync(dir)) {
    const p = path.join(dir, entry);
    const st = fs.statSync(p);
    if (st.isDirectory()) walk(p, files);
    else if (st.isFile() && (p.endsWith('.gs') || p.endsWith('.js'))) files.push(p);
  }
  return files;
}

function findDuplicates(files) {
  const fnMap = new Map(); // name -> [file:line]
  const dupes = [];
  const fnRegex = /\bfunction\s+([a-zA-Z0-9_]+)\s*\(/g;
  for (const file of files) {
    const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
    for (let i=0;i<lines.length;i++) {
      const line = lines[i];
      let m;
      while ((m = fnRegex.exec(line))) {
        const name = m[1];
        const where = `${file}:${i+1}`;
        if (!fnMap.has(name)) fnMap.set(name, [where]);
        else {
          fnMap.get(name).push(where);
        }
      }
    }
  }
  for (const [name, locs] of fnMap.entries()) {
    if (locs.length > 1) {
      dupes.push({ name, locations: locs });
    }
  }
  return dupes;
}

let hadDupes = false;
const projects = listProjects(ROOT);
for (const proj of projects) {
  const srcDir = path.join(ROOT, 'projects', proj, 'src');
  if (!fs.existsSync(srcDir)) continue;
  const files = walk(srcDir);
  const dupes = findDuplicates(files);
  if (dupes.length) {
    hadDupes = true;
    console.log(`\nProject: ${proj}`);
    for (const d of dupes) {
      console.log(`Duplicate function: ${d.name}`);
      for (const loc of d.locations) console.log(`  - ${loc}`);
    }
  }
}

if (hadDupes) {
  console.error('\n❌ Duplicate function signatures found.');
  process.exit(1);
} else {
  console.log('\n✅ No duplicate function signatures found.');
}
NODE

exit 0


