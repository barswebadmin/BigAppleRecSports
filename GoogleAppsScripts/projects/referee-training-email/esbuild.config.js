/**
 * esbuild configuration for referee-training-email
 */

module.exports = {
  entryPoints: ['index.js'],
  buildDir: 'build',
  outputFile: 'Code.js',
  srcDir: 'src',
  target: 'es2020',
  keepNames: true,
  minify: false,
};
