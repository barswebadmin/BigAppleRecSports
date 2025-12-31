/**
 * esbuild configuration for waitlist-script-comprehensive
 */

module.exports = {
  // Entry point that imports all GAS trigger functions
  entryPoints: ['src/index.js'],
  
  // Output directory and filename
  buildDir: 'build',
  outputFile: 'Code.js',
  
  // Source directory
  srcDir: 'src',
  
  // Target ES version (GAS V8 supports ES2020)
  target: 'es2020',
  
  // Keep function names for GAS triggers
  keepNames: true,
  
  // Don't minify for easier debugging in GAS editor
  minify: false,
};

