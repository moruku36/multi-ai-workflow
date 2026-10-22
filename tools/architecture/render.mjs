import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { render } from 'pele';

const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, '..', '..', 'assets');
const diagrams = [
  ['workflow', 'en', 'Task-directed implementation and independent verification; dot reports evidence to the owner for acceptance.', 'Current task workflow'],
  ['workflow', 'ja', '案件ごとに実装担当と独立検証を選び、dotが根拠を本人に報告して受入を確認します。', '現行の案件フロー'],
  ['dashboard', 'en', 'The private Windows board is canonical. Inbox handoff, authorized application, evidence and public-view sync are separate stages.', 'Dashboard record boundary'],
  ['dashboard', 'ja', 'Windowsの非公開ボードが正本です。差分受け渡し、認可された適用、証拠、公開画面との同期を分けます。', 'ダッシュボードの正本境界'],
];

for (const [name, lang, description, title] of diagrams) {
  const source = await readFile(join(here, `${name}.${lang}.mmd`), 'utf8');
  const fontFamily = lang === 'ja' ? 'Meiryo, "Noto Sans CJK JP", sans-serif' : 'Arial, sans-serif';
  const svgFont = lang === 'ja' ? 'Meiryo,\'Noto Sans CJK JP\',sans-serif' : 'Arial,sans-serif';
  const { svg, width, height } = render(source, {
    fontSize: 17,
    fontFamily,
    maxWidth: 740,
    idPrefix: `${name}-${lang}`,
    links: false,
    images: false,
  });
  const escape = (value) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  const themed = svg
    .replace('<svg ', `<svg lang="${lang}" aria-labelledby="${name}-${lang}-title ${name}-${lang}-desc" `)
    .replace('style="max-width:', `style="--pele-bg:#ffffff;--pele-fg:#17212d;--pele-muted:#334155;--pele-line:#334155;--pele-surface:#e8f1fa;--pele-surface-alt:#e8f1fa;--pele-border:#52677f;--pele-accent:#2563eb;--pele-font:${svgFont};max-width:`)
    .replace(/(<svg[^>]*>)/, `$1<title id="${name}-${lang}-title">${escape(title)}</title><desc id="${name}-${lang}-desc">${escape(description)}</desc><rect width="${width}" height="${height}" fill="#ffffff"/>`);
  if (!themed.includes('<g class="pele-edges"')) throw new Error(`Pele output missing for ${name}.${lang}`);
  const output = name === 'workflow' ? `workflow-architecture.${lang}.svg` : `dashboard-boundary.${lang}.svg`;
  await writeFile(join(out, output), themed + '\n');
  console.log(`${output}: ${width} × ${height}`);
}
