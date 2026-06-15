/**
 * Build script for process-refunds-exchanges.
 *
 * This project's src/*.js files don't use ES imports between each other —
 * they rely on GAS's implicit cross-file global scope. The shared esbuild
 * bundler at scripts/deployment/google/build.js requires ESM imports to
 * trace its module graph; running it against this project produces an empty
 * bundle (every file looks side-effect-free to esbuild).
 *
 * Until / unless the src tree is refactored to use ESM, we just copy
 * src/*.js + appsscript.json into build/ verbatim. clasp then pushes each
 * file individually (matching what's currently in Google).
 */

const fs = require('fs');
const path = require('path');

const projectDir = process.cwd();
const srcDir = path.join(projectDir, 'src');
const buildDir = path.join(projectDir, 'build');

if (!fs.existsSync(srcDir)) {
  console.error(`❌ src/ not found at ${srcDir}`);
  process.exit(1);
}

if (fs.existsSync(buildDir)) {
  fs.rmSync(buildDir, { recursive: true });
}
fs.mkdirSync(buildDir, { recursive: true });

function copyRecursive(srcAbs, destAbs) {
  const stat = fs.statSync(srcAbs);
  if (stat.isDirectory()) {
    fs.mkdirSync(destAbs, { recursive: true });
    for (const entry of fs.readdirSync(srcAbs)) {
      copyRecursive(path.join(srcAbs, entry), path.join(destAbs, entry));
    }
  } else if (stat.isFile() && srcAbs.endsWith('.js')) {
    fs.copyFileSync(srcAbs, destAbs);
  }
}

console.log(`📋 Copying src/ → build/ …`);
copyRecursive(srcDir, buildDir);

const appsscript = path.join(projectDir, 'appsscript.json');
if (fs.existsSync(appsscript)) {
  fs.copyFileSync(appsscript, path.join(buildDir, 'appsscript.json'));
  console.log(`   appsscript.json copied`);
}

// scripts/deploy expects build/Code.js to exist as a sentinel (it checks for a
// `Build time:` header and injects a FORCE_DEPLOY marker into deploy_temp/Code.js
// before clasp push). Since we're not bundling, this Code.js is a no-op stub —
// the real code lives in the individual *.js files copied above.
const codeJsStub = `/**
 * Bundle stub — this project pushes individual src/*.js files instead of a
 * unified bundle. See build.js for the rationale.
 * Build time: ${new Date().toISOString()}
 */
`;
fs.writeFileSync(path.join(buildDir, 'Code.js'), codeJsStub);
console.log(`   Code.js stub written (sentinel for scripts/deploy)`);

const files = [];
function collect(dir, prefix) {
  for (const entry of fs.readdirSync(dir)) {
    const abs = path.join(dir, entry);
    const rel = prefix ? `${prefix}/${entry}` : entry;
    if (fs.statSync(abs).isDirectory()) collect(abs, rel);
    else files.push(rel);
  }
}
collect(buildDir, '');

console.log(`✅ Build complete — ${files.length} files in build/:`);
for (const f of files.sort()) console.log(`   ${f}`);
console.log(`\nNext: clasp push (handled by scripts/deploy)`);
