import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { render } from 'pele';

const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, '..', '..', 'assets');
const variants = [
  ['en', 'Current manual workflow: owner direction, Dottie coordination (Codex for handoff and result checks only), Gemini 3.8 Flash implementation with manual escalation to higher-tier models for hard problems, manual review via MiMo V2.6 Pro in existing Open WebUI, tests and owner acceptance.'],
  ['ja', '現行の手動ワークフロー：本人方針、Dottie調整（Codexは受け渡し・結果確認のみ）、Gemini 3.8 Flash主体の実作業と難所での手動上位モデル昇格・復帰、既存Open WebUIでのMiMo V2.6 Pro手動レビュー、テストと本人承認。'],
];

for (const [lang, description] of variants) {
  const source = await readFile(join(here, `workflow.${lang}.mmd`), 'utf8');
  const fontFamily = lang === 'ja' ? 'Meiryo, "Noto Sans CJK JP", sans-serif' : 'Arial, sans-serif';
  const svgFont = lang === 'ja' ? 'Meiryo,\'Noto Sans CJK JP\',sans-serif' : 'Arial,sans-serif';
  const { svg, width, height } = render(source, {
    fontSize: 18,
    fontFamily,
    maxWidth: 650,
    idPrefix: `workflow-${lang}`,
    links: false,
    images: false,
  });
  const title = lang === 'ja' ? '現行の Multi-AI ワークフロー' : 'Current Multi-AI workflow';
  const escape = (value) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  const themed = svg
    .replace('<svg ', `<svg lang="${lang}" aria-labelledby="workflow-${lang}-title workflow-${lang}-desc" `)
    .replace('style="max-width:', `style="--pele-bg:#ffffff;--pele-fg:#17212d;--pele-muted:#334155;--pele-line:#334155;--pele-surface:#e8f1fa;--pele-surface-alt:#e8f1fa;--pele-border:#52677f;--pele-accent:#2563eb;--pele-font:${svgFont};max-width:`)
    .replace(/(<svg[^>]*>)/, `$1<title id="workflow-${lang}-title">${escape(title)}</title><desc id="workflow-${lang}-desc">${escape(description)}</desc><rect width="${width}" height="${height}" fill="#ffffff"/>`);
  if (!themed.includes('<g class="pele-edges"')) throw new Error(`Pele output missing for ${lang}`);
  await writeFile(join(out, `workflow-architecture.${lang}.svg`), themed + '\n');
  console.log(`${lang}: ${width} × ${height}`);
}
