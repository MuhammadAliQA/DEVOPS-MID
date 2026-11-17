// Copy the lockfile-installed Anime.js browser distribution, retaining its license.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const packageDir = path.join(root, 'node_modules/animejs');
const manifest = JSON.parse(fs.readFileSync(path.join(packageDir, 'package.json'), 'utf8'));
const lock = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json'), 'utf8'));
if (manifest.version !== lock.packages['node_modules/animejs'].version) throw Error('Run npm ci: installed Anime.js differs from the lockfile');
const target = path.join(root, 'static/vendor');
fs.mkdirSync(target, {recursive: true});
const source = fs.readFileSync(path.join(packageDir, 'dist/bundles/anime.umd.min.js'));
fs.writeFileSync(path.join(target, 'anime.umd.min.js'), source);
fs.copyFileSync(path.join(packageDir, 'LICENSE.md'), path.join(target, 'anime.LICENSE.md'));
fs.writeFileSync(path.join(target, 'anime-manifest.json'), JSON.stringify({package: 'animejs', version: manifest.version, license: manifest.license, sha256: crypto.createHash('sha256').update(source).digest('hex')}, null, 2) + '\n');
console.log(`Anime.js ${manifest.version}: ${source.length} bytes, self-hosted with MIT license`);
