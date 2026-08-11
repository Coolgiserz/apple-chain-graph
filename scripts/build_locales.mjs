#!/usr/bin/env node
// 单一真相源（single source of truth）：
//   1) 把 locales/{zh,en,fr,ja}.json（+ enum_map.json）内联成 dist/locales.js
//      （window.I18N_LOCALES / window.I18N_ENUM_MAP），供 i18n.js 直接读取，
//      不再依赖运行时 fetch/XHR——彻底规避「语言包 404 / 切换无效 / file:// 打不开」。
//   2) 构建期 i18n 审计：扫描 src/engine + src/lib 里所有 i18nText("bottleneck.*"/"home.*")
//      调用，逐一核对是否确实存在于刚生成的 bundle；缺失即 fail-fast（process.exit(1)），
//      从源头阻止「漏翻的 key 以原始后台标签形态渲染到页面」再次上线。
//
// 为什么是 Node 而不是 Python：本脚本由 `npm run build`（含 Docker 的 nodebuilder 阶段）
// 调用，该环境只有 Node、没有 Python；而 build_all.py 的 Python 阶段改为直接复用本脚本产物，
// 不再各自实现一份，避免「Python/JS 双份实现漂移」再次导致 raw key 漏网。
//
// 用法：node scripts/build_locales.mjs

import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const LANGS = ['zh', 'en', 'fr', 'ja'];

function readJSON(p) {
  return JSON.parse(readFileSync(p, 'utf8'));
}

// —— 1) 内联 locales ——
const bundles = {};
for (const lng of LANGS) {
  const p = join(ROOT, 'locales', lng + '.json');
  if (existsSync(p)) bundles[lng] = readJSON(p);
}

const out = [
  '/* 自动生成：locales/*.json 内联为全局，供 i18n.js 使用。勿手改，改 locales/*.json 后重跑构建。*/',
  'window.I18N_LOCALES = ' + JSON.stringify(bundles) + ';',
];
const enumPath = join(ROOT, 'locales', 'enum_map.json');
if (existsSync(enumPath)) {
  out.push('window.I18N_ENUM_MAP = ' + JSON.stringify(readJSON(enumPath)) + ';');
}

const distDir = join(ROOT, 'dist');
mkdirSync(distDir, { recursive: true });
writeFileSync(join(distDir, 'locales.js'), out.join('\n') + '\n', 'utf8');
console.log('generated: dist/locales.js packs:', Object.keys(bundles).join(', '));

// —— 2) 构建期 i18n 审计 ——
const re = /i18nText\(\s*["']((?:bottleneck|home)\.[A-Za-z0-9_]+)["']/g;
const referenced = new Set();
for (const d of ['src/engine', 'src/lib']) {
  const dir = join(ROOT, d);
  if (!existsSync(dir)) continue;
  for (const f of readdirSync(dir)) {
    if (!f.endsWith('.js')) continue;
    const src = readFileSync(join(dir, f), 'utf8');
    let m;
    while ((m = re.exec(src)) !== null) referenced.add(m[1]);
  }
}

// bundle 中各语言 key 取并集：任一种语言有译文即视为已翻译（运行时未加载该语言才会告警）。
const present = new Set();
for (const d of Object.values(bundles)) {
  for (const k of Object.keys(d)) present.add(k);
}

const missing = [...referenced].filter((k) => !present.has(k)).sort();
if (missing.length) {
  console.error(
    '✗ i18n 审计失败：以下翻译键在 locales/*.json 中缺失，将以原始后台标签渲染到页面：',
  );
  for (const k of missing) console.error('   - ' + k);
  console.error('  → 请在 locales/{zh,en,fr,ja}.json 补上对应译文后，重跑构建（npm run build / make up）。');
  process.exit(1);
}
console.log('i18n audit: ' + referenced.size + ' referenced keys, all present ✔');
