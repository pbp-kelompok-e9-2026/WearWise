import { copyFileSync, mkdirSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = new URL('../', import.meta.url);
const cli = fileURLToPath(new URL('node_modules/@tailwindcss/cli/dist/index.mjs', root));
for (const name of ['worth_to_buy', 'analyzer_workspace']) {
  const result = spawnSync(process.execPath, [cli, '-i', `static/src/${name}.css`, '-o', `static/css/${name}.css`, '--minify'], {cwd: fileURLToPath(root), stdio: 'inherit'});
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
mkdirSync(new URL('static/vendor/', root), {recursive: true});
copyFileSync(new URL('node_modules/htmx.org/dist/htmx.min.js', root), new URL('static/vendor/htmx.min.js', root));
copyFileSync(new URL('node_modules/htmx.org/LICENSE', root), new URL('static/vendor/htmx.LICENSE', root));
const htmx = JSON.parse(readFileSync(new URL('node_modules/htmx.org/package.json', root), 'utf8'));
console.log(`Built Tailwind CSS and bundled htmx ${htmx.version}.`);
