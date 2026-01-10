/**
 * esbuild configuration for create-products-new
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
