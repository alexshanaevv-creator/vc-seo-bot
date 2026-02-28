"""
Веб-интерфейс для VC.RU SEO Bot.
Запуск: python app.py  →  открыть http://localhost:5000
"""

import json
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_file, Response

sys.path.insert(0, str(Path(__file__).parent))
import config
from generator import generate_article
from photos import pick_photos
from publisher import VcPublisher

app = Flask(__name__)

ARTICLES_DIR = Path(__file__).parent / "articles"
ARTICLES_DIR.mkdir(exist_ok=True)

# Состояние фоновых задач
tasks: dict[str, dict] = {}


# ─── HTML-шаблон ─────────────────────────────────────────────────────────────

TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VC.RU SEO Bot</title>
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#2563eb">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="SEO Bot">
<link rel="apple-touch-icon" href="/icon.svg">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --blue: #2563eb; --blue-h: #1d4ed8;
    --green: #16a34a; --red: #dc2626;
    --gray: #f1f5f9; --border: #e2e8f0;
    --text: #1e293b; --muted: #64748b;
  }
  body { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         background:#f8fafc; color:var(--text); min-height:100vh; }

  /* Header */
  header { background:#fff; border-bottom:1px solid var(--border); padding:16px 32px;
           display:flex; align-items:center; gap:16px; }
  header h1 { font-size:1.25rem; font-weight:700; }
  header span { font-size:.85rem; color:var(--muted); }
  .badge { background:var(--blue); color:#fff; font-size:.75rem; font-weight:600;
           padding:3px 10px; border-radius:99px; }

  /* Layout */
  .layout { display:grid; grid-template-columns:380px 1fr; gap:24px;
            padding:24px 32px; max-width:1400px; margin:0 auto; }

  /* Panel */
  .panel { background:#fff; border:1px solid var(--border); border-radius:12px;
           overflow:hidden; }
  .panel-head { padding:16px 20px; border-bottom:1px solid var(--border);
                font-weight:600; font-size:.95rem; display:flex; align-items:center;
                justify-content:space-between; }
  .panel-body { padding:20px; }

  /* Form */
  label { display:block; font-size:.85rem; font-weight:500; color:var(--muted);
          margin-bottom:5px; margin-top:14px; }
  label:first-child { margin-top:0; }
  input[type=text], textarea, select {
    width:100%; border:1px solid var(--border); border-radius:8px;
    padding:10px 12px; font-size:.9rem; font-family:inherit; color:var(--text);
    transition:border-color .2s; background:#fff;
  }
  input[type=text]:focus, textarea:focus { outline:none; border-color:var(--blue); }
  textarea { resize:vertical; min-height:60px; }
  .btn { display:inline-flex; align-items:center; gap:8px; padding:11px 20px;
         border:none; border-radius:8px; font-size:.9rem; font-weight:600;
         cursor:pointer; transition:background .2s; }
  .btn-primary { background:var(--blue); color:#fff; width:100%; justify-content:center; margin-top:16px; }
  .btn-primary:hover { background:var(--blue-h); }
  .btn-primary:disabled { background:#94a3b8; cursor:not-allowed; }
  .btn-sm { padding:6px 12px; font-size:.8rem; border-radius:6px; }
  .btn-ghost { background:var(--gray); color:var(--text); }
  .btn-ghost:hover { background:#e2e8f0; }
  .btn-green { background:var(--green); color:#fff; }
  .btn-green:hover { background:#15803d; }

  /* Progress */
  .progress-wrap { margin-top:16px; display:none; }
  .progress-wrap.visible { display:block; }
  .progress-bar { height:6px; background:var(--border); border-radius:99px; overflow:hidden; }
  .progress-fill { height:100%; background:var(--blue); border-radius:99px;
                   width:0%; transition:width .4s; animation:pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.6} }
  .progress-label { font-size:.82rem; color:var(--muted); margin-top:6px; }

  /* Article list */
  .art-list { display:flex; flex-direction:column; gap:2px; }
  .art-item { padding:14px 16px; border-radius:8px; cursor:pointer;
              transition:background .15s; display:flex; align-items:flex-start;
              gap:12px; }
  .art-item:hover, .art-item.active { background:var(--gray); }
  .art-item.active { background:#eff6ff; }
  .art-dot { width:8px; height:8px; border-radius:50%; background:#cbd5e1;
             margin-top:5px; flex-shrink:0; }
  .art-dot.new { background:var(--green); }
  .art-info { flex:1; min-width:0; }
  .art-title { font-size:.9rem; font-weight:600; white-space:nowrap;
               overflow:hidden; text-overflow:ellipsis; }
  .art-meta { font-size:.78rem; color:var(--muted); margin-top:2px; }
  .empty-state { padding:40px 20px; text-align:center; color:var(--muted);
                 font-size:.9rem; }

  /* Preview */
  .preview-header { padding:20px 28px; border-bottom:1px solid var(--border); }
  .preview-header h2 { font-size:1.3rem; line-height:1.4; margin-bottom:6px; }
  .preview-meta { font-size:.83rem; color:var(--muted); }
  .preview-actions { display:flex; gap:8px; margin-top:14px; flex-wrap:wrap; }
  .preview-body { padding:24px 28px; max-height: calc(100vh - 260px); overflow-y:auto; }
  .preview-body h2 { font-size:1.05rem; font-weight:700; margin:24px 0 8px; color:#1e40af; }
  .preview-body p { line-height:1.75; margin-bottom:10px; font-size:.92rem; }
  .preview-body ul { margin:6px 0 12px 20px; }
  .preview-body li { font-size:.92rem; line-height:1.7; }
  .preview-body .photo-slot { background:#f0f9ff; border:1px dashed #93c5fd;
    border-radius:8px; padding:14px; text-align:center; color:#3b82f6;
    font-size:.83rem; margin:12px 0; }
  .preview-empty { display:flex; align-items:center; justify-content:center;
                   height:400px; color:var(--muted); flex-direction:column; gap:12px; }
  .preview-empty svg { opacity:.3; }

  /* Toast */
  .toast { position:fixed; bottom:24px; right:24px; background:#1e293b; color:#fff;
           padding:12px 20px; border-radius:10px; font-size:.88rem; z-index:999;
           transform:translateY(80px); opacity:0; transition:all .3s; }
  .toast.show { transform:translateY(0); opacity:1; }

  /* Status chip */
  .chip { display:inline-block; font-size:.75rem; font-weight:600;
          padding:2px 9px; border-radius:99px; }
  .chip-ok { background:#dcfce7; color:#15803d; }
  .chip-err { background:#fee2e2; color:#dc2626; }
  .chip-pending { background:#fef9c3; color:#92400e; }

  @media(max-width:900px){
    .layout{grid-template-columns:1fr; padding:16px;}
  }
</style>
</head>
<body>

<header>
  <div>
    <h1>VC.RU SEO Bot</h1>
    <span>Автогенерация статей для osari.ru</span>
  </div>
  <div style="display:flex;align-items:center;gap:10px;">
    <button class="btn btn-sm btn-ghost" id="installBtn" style="display:none;" onclick="installApp()">
      📲 Установить приложение
    </button>
    <div class="badge">Claude AI</div>
  </div>
</header>

<div class="layout">

  <!-- Left: Generate form + Article list -->
  <div style="display:flex;flex-direction:column;gap:16px;">

    <!-- Generate panel -->
    <div class="panel">
      <div class="panel-head">✍️ Написать статью</div>
      <div class="panel-body">
        <label>Тема статьи</label>
        <input type="text" id="topic" placeholder="Например: Как выбрать массажное кресло в 2025 году">

        <label>Доп. контекст (необязательно)</label>
        <textarea id="description" placeholder="Что важно упомянуть, акценты..."></textarea>

        <label>Тип статьи</label>
        <select id="article_type">
          <option value="general">Общетематическая (Gemini Flash — бесплатно)</option>
          <option value="expert">Экспертная (Claude Opus — только позитив)</option>
        </select>

        <label>Характеристики товара/услуги (необязательно)</label>
        <textarea id="product_specs" placeholder="Модель, цена, технические параметры, особенности...&#10;Используется для точных цифр в статье." style="height:80px;"></textarea>

        <div style="border:1px solid var(--border);border-radius:8px;overflow:hidden;margin-top:2px;">
          <div style="padding:10px 14px;background:var(--gray);font-weight:600;font-size:.85rem;cursor:pointer;display:flex;justify-content:space-between;align-items:center;" onclick="toggleSection('webSearchSection')">
            🔍 Веб-поиск для исследования <span id="webSearchToggle">▶</span>
          </div>
          <div id="webSearchSection" style="display:none;padding:12px 14px;">
            <div style="display:flex;gap:8px;margin-bottom:8px;">
              <input type="text" id="webSearchQuery" placeholder="Запрос для поиска..." style="flex:1;">
              <button class="btn btn-sm btn-ghost" onclick="searchWeb()">Найти</button>
            </div>
            <div id="webSearchResults" style="font-size:.82rem;max-height:200px;overflow-y:auto;"></div>
            <label style="margin-top:10px;display:block;">Одобренные данные для статьи</label>
            <textarea id="research_data" placeholder="Скопируйте сюда нужные факты из результатов поиска..." style="height:80px;font-size:.82rem;"></textarea>
          </div>
        </div>

        <div style="border:1px solid var(--border);border-radius:8px;overflow:hidden;margin-top:8px;">
          <div style="padding:10px 14px;background:var(--gray);font-weight:600;font-size:.85rem;cursor:pointer;display:flex;justify-content:space-between;align-items:center;" onclick="toggleSection('rutubeSection')">
            📹 Видео RuTube <span id="rutubeSectionToggle">▶</span>
          </div>
          <div id="rutubeSection" style="display:none;padding:12px 14px;">
            <div style="display:flex;gap:8px;margin-bottom:8px;">
              <input type="text" id="rutubeQuery" placeholder="Запрос для поиска видео..." style="flex:1;">
              <button class="btn btn-sm btn-ghost" onclick="searchRutube()">Найти</button>
            </div>
            <div id="rutubeResults" style="font-size:.82rem;max-height:200px;overflow-y:auto;"></div>
            <div id="selectedVideos" style="margin-top:8px;font-size:.82rem;"></div>
          </div>
        </div>

        <label style="margin-top:8px;">Режим публикации</label>
        <select id="publish_mode">
          <option value="draft">Сохранить как черновик на VC.RU</option>
          <option value="local">Только сохранить локально (без VC.RU)</option>
          <option value="publish">Опубликовать сразу на VC.RU</option>
        </select>

        <button class="btn btn-primary" id="genBtn" onclick="generateArticle()">
          ⚡ Сгенерировать статью
        </button>

        <div class="progress-wrap" id="progress">
          <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
          <div class="progress-label" id="progressLabel">Запускаем генерацию...</div>
        </div>
      </div>
    </div>

    <!-- Articles list -->
    <div class="panel" style="flex:1;">
      <div class="panel-head">
        📄 Статьи
        <span id="artCount" style="font-weight:400;color:var(--muted);font-size:.82rem;"></span>
      </div>
      <div class="panel-body" style="padding:8px;">
        <div class="art-list" id="artList">
          <div class="empty-state">Нет статей. Сгенерируйте первую!</div>
        </div>
      </div>
    </div>

  </div>

  <!-- Right: Preview -->
  <div class="panel" id="previewPanel">
    <div class="preview-empty" id="previewEmpty">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14,2 14,8 20,8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10,9 9,9 8,9"/>
      </svg>
      <span>Выберите статью для предпросмотра</span>
    </div>
    <div id="previewContent" style="display:none;">
      <div class="preview-header">
        <h2 id="pvTitle"></h2>
        <div class="preview-meta" id="pvMeta"></div>
        <div class="preview-actions">
          <button class="btn btn-sm btn-ghost" onclick="copyText()">📋 Копировать текст</button>
          <button class="btn btn-sm btn-ghost" onclick="openHtml()">🌐 Открыть HTML</button>
          <button class="btn btn-sm btn-green" onclick="publishCurrent()">🚀 Опубликовать на VC.RU</button>
        </div>
      </div>
      <div class="preview-body" id="pvBody"></div>
    </div>
  </div>

</div>

<div class="toast" id="toast"></div>

<script>
let articles = [];
let currentArticle = null;
let currentTask = null;
let pollInterval = null;
let selectedVideoEmbeds = [];

function toggleSection(id) {
  const el = document.getElementById(id);
  const toggle = document.getElementById(id + 'Toggle');
  if (el.style.display === 'none') {
    el.style.display = 'block';
    if (toggle) toggle.textContent = '▼';
  } else {
    el.style.display = 'none';
    if (toggle) toggle.textContent = '▶';
  }
}

async function searchWeb() {
  const q = document.getElementById('webSearchQuery').value.trim();
  if (!q) return;
  const btn = event.target;
  btn.textContent = '...';
  btn.disabled = true;
  try {
    const res = await fetch('/api/search-web', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: q})
    });
    const data = await res.json();
    const el = document.getElementById('webSearchResults');
    if (!data.results || !data.results.length) {
      el.innerHTML = '<div style="color:var(--muted);padding:8px 0;">Ничего не найдено</div>';
    } else {
      el.innerHTML = data.results.map(r => `
        <div style="padding:6px 0;border-bottom:1px solid var(--border);">
          <div style="font-weight:600;margin-bottom:2px;">${r.title}</div>
          <div style="color:var(--muted);margin-bottom:4px;">${r.snippet || ''}</div>
          <button class="btn btn-sm btn-ghost" style="font-size:.75rem;padding:2px 8px;"
            onclick="addToResearch('${(r.title + ': ' + (r.snippet||'')).replace(/'/g,"\\'")}')">
            + В исследование
          </button>
        </div>
      `).join('');
    }
  } catch(e) {
    document.getElementById('webSearchResults').innerHTML = '<div style="color:var(--red);">Ошибка поиска</div>';
  }
  btn.textContent = 'Найти';
  btn.disabled = false;
}

function addToResearch(text) {
  const ta = document.getElementById('research_data');
  ta.value = (ta.value ? ta.value + '\n\n' : '') + text;
  showToast('Добавлено в исследование');
}

async function searchRutube() {
  const q = document.getElementById('rutubeQuery').value.trim();
  if (!q) return;
  const btn = event.target;
  btn.textContent = '...';
  btn.disabled = true;
  try {
    const res = await fetch('/api/search-rutube', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: q})
    });
    const data = await res.json();
    const el = document.getElementById('rutubeResults');
    if (!data.videos || !data.videos.length) {
      el.innerHTML = '<div style="color:var(--muted);padding:8px 0;">Ничего не найдено</div>';
    } else {
      el.innerHTML = data.videos.map(v => `
        <div style="padding:6px 0;border-bottom:1px solid var(--border);display:flex;gap:8px;align-items:center;">
          ${v.thumbnail ? `<img src="${v.thumbnail}" style="width:80px;height:45px;object-fit:cover;border-radius:4px;">` : ''}
          <div style="flex:1;min-width:0;">
            <div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${v.title}</div>
            <button class="btn btn-sm btn-ghost" style="font-size:.75rem;padding:2px 8px;margin-top:4px;"
              onclick='addVideo(${JSON.stringify(v)})'>+ Добавить в статью</button>
          </div>
        </div>
      `).join('');
    }
  } catch(e) {
    document.getElementById('rutubeResults').innerHTML = '<div style="color:var(--red);">Ошибка поиска</div>';
  }
  btn.textContent = 'Найти';
  btn.disabled = false;
}

function addVideo(v) {
  if (selectedVideoEmbeds.find(x => x.id === v.id)) { showToast('Видео уже добавлено'); return; }
  selectedVideoEmbeds.push(v);
  renderSelectedVideos();
  showToast('Видео добавлено в статью');
}

function removeVideo(id) {
  selectedVideoEmbeds = selectedVideoEmbeds.filter(v => v.id !== id);
  renderSelectedVideos();
}

function renderSelectedVideos() {
  const el = document.getElementById('selectedVideos');
  if (!selectedVideoEmbeds.length) { el.innerHTML = ''; return; }
  el.innerHTML = '<div style="font-weight:600;margin-bottom:6px;">Выбрано для статьи:</div>' +
    selectedVideoEmbeds.map(v => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;">${v.title}</span>
        <button class="btn btn-sm btn-ghost" style="font-size:.75rem;padding:2px 8px;margin-left:8px;color:var(--red);"
          onclick="removeVideo('${v.id}')">✕</button>
      </div>
    `).join('');
}

// ─── Load articles ─────────────────────────────────────────────────────────

async function loadArticles() {
  const res = await fetch('/api/articles');
  articles = await res.json();
  renderList();
}

function renderList() {
  const list = document.getElementById('artList');
  document.getElementById('artCount').textContent = articles.length ? `(${articles.length})` : '';
  if (!articles.length) {
    list.innerHTML = '<div class="empty-state">Нет статей. Сгенерируйте первую!</div>';
    return;
  }
  list.innerHTML = articles.map((a, i) => `
    <div class="art-item ${currentArticle && currentArticle.filename === a.filename ? 'active' : ''}" onclick="loadArticle('${a.filename}')">
      <div class="art-dot ${i === 0 ? 'new' : ''}"></div>
      <div class="art-info">
        <div class="art-title">${a.title}</div>
        <div class="art-meta">${a.date} · ${a.words} слов</div>
      </div>
    </div>
  `).join('');
}

async function loadArticle(filename) {
  const res = await fetch(`/api/article/${encodeURIComponent(filename)}`);
  const data = await res.json();
  currentArticle = data;
  showPreview(data);
  renderList();
}

function showPreview(data) {
  document.getElementById('previewEmpty').style.display = 'none';
  document.getElementById('previewContent').style.display = 'block';
  document.getElementById('pvTitle').textContent = data.title;
  document.getElementById('pvMeta').textContent =
    `${data.date}  ·  ~${data.words} слов  ·  ${data.filename}`;

  let html = '';
  if (data.intro) html += data.intro.split('\\n\\n').map(p => `<p>${p}</p>`).join('');

  (data.sections || []).forEach(s => {
    html += `<h2>${s.heading || ''}</h2>`;
    (s.paragraphs || []).forEach(p => html += `<p>${p}</p>`);
    if ((s.list_items || []).length) {
      html += '<ul>' + s.list_items.map(i => `<li>${i}</li>`).join('') + '</ul>';
    }
    if (s.has_image_placeholder) {
      html += '<div class="photo-slot">📷 Место для фотографии</div>';
    }
  });

  if (data.conclusion) {
    html += `<h2>Заключение</h2>`;
    html += data.conclusion.split('\\n\\n').map(p => `<p>${p}</p>`).join('');
  }

  document.getElementById('pvBody').innerHTML = html;
}

// ─── Generate ─────────────────────────────────────────────────────────────

async function generateArticle() {
  const topic = document.getElementById('topic').value.trim();
  if (!topic) { showToast('Введите тему статьи'); return; }

  const mode = document.getElementById('publish_mode').value;
  const publish = mode === 'publish';
  const localOnly = mode === 'local';

  document.getElementById('genBtn').disabled = true;
  showProgress('Отправляем запрос к Claude AI...');

  const res = await fetch('/api/generate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      topic,
      description: document.getElementById('description').value,
      article_type: document.getElementById('article_type').value,
      product_specs: document.getElementById('product_specs').value,
      research_data: document.getElementById('research_data').value,
      video_embeds: selectedVideoEmbeds.map(v => v.embed_html),
      publish,
      local_only: localOnly,
    })
  });
  const data = await res.json();
  currentTask = data.task_id;
  pollTask(currentTask);
}

function pollTask(taskId) {
  let progress = 5;
  const stages = [
    'Claude AI пишет статью...',
    'Генерация разделов...',
    'Добавляем SEO-ссылки...',
    'Финализируем статью...',
    'Сохраняем...',
  ];
  let stageIdx = 0;

  pollInterval = setInterval(async () => {
    progress = Math.min(progress + Math.random() * 8, 90);
    if (stageIdx < stages.length - 1 && progress > (stageIdx + 1) * 18) stageIdx++;
    setProgress(progress, stages[stageIdx]);

    const res = await fetch(`/api/task/${taskId}`);
    const data = await res.json();

    if (data.status === 'done') {
      clearInterval(pollInterval);
      setProgress(100, 'Готово!');
      setTimeout(() => {
        hideProgress();
        document.getElementById('genBtn').disabled = false;
        document.getElementById('topic').value = '';
        document.getElementById('description').value = '';
        showToast('✅ Статья сгенерирована!');
        loadArticles().then(() => {
          if (articles.length) loadArticle(articles[0].filename);
        });
      }, 600);
    } else if (data.status === 'error') {
      clearInterval(pollInterval);
      hideProgress();
      document.getElementById('genBtn').disabled = false;
      showToast('❌ Ошибка: ' + data.error, 4000);
    }
  }, 2000);
}

function showProgress(label) {
  const pw = document.getElementById('progress');
  pw.classList.add('visible');
  setProgress(5, label);
}
function setProgress(pct, label) {
  document.getElementById('progressFill').style.width = pct + '%';
  document.getElementById('progressLabel').textContent = label;
}
function hideProgress() {
  document.getElementById('progress').classList.remove('visible');
  setProgress(0, '');
}

// ─── Actions ───────────────────────────────────────────────────────────────

function copyText() {
  if (!currentArticle) return;
  const el = document.getElementById('pvBody');
  const text = el.innerText;
  navigator.clipboard.writeText(currentArticle.title + '\\n\\n' + text);
  showToast('📋 Текст скопирован в буфер обмена');
}

function openHtml() {
  if (!currentArticle) return;
  window.open(`/article/${encodeURIComponent(currentArticle.filename)}`, '_blank');
}

async function publishCurrent() {
  if (!currentArticle) return;
  showToast('🚀 Публикуем на VC.RU...');
  const res = await fetch('/api/publish', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ filename: currentArticle.filename })
  });
  const data = await res.json();
  if (data.ok) showToast('✅ Опубликовано: ' + (data.url || ''), 5000);
  else showToast('❌ ' + (data.error || 'Ошибка публикации'), 5000);
}

// ─── Toast ────────────────────────────────────────────────────────────────

function showToast(msg, ms=2500) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), ms);
}

// ─── PWA Install ──────────────────────────────────────────────────────────
let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  document.getElementById('installBtn').style.display = 'inline-flex';
});

function installApp() {
  if (!deferredPrompt) {
    showToast('Откройте сайт в Chrome и используйте меню ⋮ → "Установить приложение"');
    return;
  }
  deferredPrompt.prompt();
  deferredPrompt.userChoice.then(() => {
    deferredPrompt = null;
    document.getElementById('installBtn').style.display = 'none';
  });
}

window.addEventListener('appinstalled', () => {
  showToast('✅ Приложение установлено на рабочий стол!');
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

// ─── Init ─────────────────────────────────────────────────────────────────
loadArticles();
</script>
</body>
</html>"""


# ─── API ─────────────────────────────────────────────────────────────────────

def _parse_html_article(filepath: Path) -> dict:
    """Читает сохранённый HTML и возвращает базовую мета-инфу."""
    html = filepath.read_text(encoding="utf-8")
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    title = title_m.group(1).strip() if title_m else filepath.stem
    text = re.sub(r"<[^>]+>", "", html)
    words = len(text.split())
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    return {
        "filename": filepath.name,
        "title": title,
        "date": mtime.strftime("%d.%m.%Y %H:%M"),
        "words": words,
    }


@app.route("/")
def index():
    return render_template_string(TEMPLATE)


@app.route("/article/<filename>")
def serve_article(filename):
    path = ARTICLES_DIR / filename
    if path.exists():
        return send_file(path)
    return "Not found", 404


@app.route("/api/articles")
def api_articles():
    files = sorted(ARTICLES_DIR.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)
    return jsonify([_parse_html_article(f) for f in files])


@app.route("/api/article/<filename>")
def api_article(filename):
    path = ARTICLES_DIR / filename
    if not path.exists():
        return jsonify({"error": "not found"}), 404

    html = path.read_text(encoding="utf-8")
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    title = title_m.group(1).strip() if title_m else path.stem

    # Ищем JSON в мете (если есть) или парсим из HTML
    json_m = re.search(r"<!--JSON:(.*?)-->", html, re.S)
    if json_m:
        data = json.loads(json_m.group(1))
        data["filename"] = filename
        data["date"] = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
        data["words"] = len(re.sub(r"<[^>]+>", "", html).split())
        return jsonify(data)

    # Fallback: парсим из HTML-текста
    text = re.sub(r"<[^>]+>", "", html)
    words = len(text.split())
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return jsonify({
        "filename": filename,
        "title": title,
        "date": mtime.strftime("%d.%m.%Y %H:%M"),
        "words": words,
        "intro": "",
        "sections": [],
        "conclusion": "",
    })


@app.route("/api/generate", methods=["POST"])
def api_generate():
    body = request.get_json()
    topic = (body.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "Нет темы"}), 400

    task_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    tasks[task_id] = {"status": "running"}

    def worker():
        try:
            article = generate_article(
                topic_title=topic,
                topic_description=body.get("description", ""),
                product_specs=body.get("product_specs", ""),
                research_data=body.get("research_data", ""),
                article_type=body.get("article_type", "general"),
                niche_keywords=config.NICHE_KEYWORDS,
                site_url=config.YOUR_SITE_URL,
                site_anchor=config.YOUR_SITE_ANCHOR,
                claude_api_key=config.ANTHROPIC_API_KEY,
                gemini_api_key=config.GEMINI_API_KEY,
                min_words=config.ARTICLE_MIN_WORDS,
                links_count=config.ARTICLE_LINKS_COUNT,
                tone=config.ARTICLE_TONE,
                llm_provider=config.LLM_PROVIDER,
                claude_model=config.CLAUDE_MODEL,
                gemini_model=config.GEMINI_MODEL,
                video_embeds=body.get("video_embeds", []),
                image_count=config.PHOTOS_PER_ARTICLE,
            )

            # Сохраняем HTML + JSON-мету внутри
            import json as _json
            output_dir = ARTICLES_DIR
            safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in article.title)[:60]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = output_dir / f"{ts}_{safe}.html"

            sections_html = ""
            for section in article.sections:
                sections_html += f'<h2>{section.get("heading","")}</h2>\n'
                for p in section.get("paragraphs", []):
                    sections_html += f"<p>{p}</p>\n"
                items = section.get("list_items", [])
                if items:
                    sections_html += "<ul>\n" + "".join(f"  <li>{it}</li>\n" for it in items) + "</ul>\n"
                if section.get("has_image_placeholder"):
                    sections_html += '<p><em>[ФОТО]</em></p>\n'

            meta_json = _json.dumps({
                "title": article.title,
                "intro": article.intro,
                "sections": article.sections,
                "conclusion": article.conclusion,
                "meta_description": article.meta_description,
                "keywords": article.keywords,
            }, ensure_ascii=False)

            html = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>{article.title}</title>
<style>body{{max-width:860px;margin:40px auto;font-family:Georgia,serif;line-height:1.7;padding:0 20px}}
h1{{font-size:2em;margin-bottom:.3em}}h2{{margin-top:1.8em;color:#1e40af}}
p{{margin:.8em 0}}ul{{margin:.5em 0 1em 1.5em}}.meta{{color:#888;font-size:.9em;margin-bottom:2em}}</style>
</head><body>
<!--JSON:{meta_json}-->
<h1>{article.title}</h1>
<p class="meta">{article.meta_description}</p>
{article.intro.replace(chr(10)*2,"</p><p>")}
{sections_html}
<h2>Заключение</h2>
<p>{article.conclusion.replace(chr(10)*2,"</p><p>")}</p>
</body></html>"""
            filepath.write_text(html, encoding="utf-8")

            # Публикуем если нужно
            publish = body.get("publish", False)
            local_only = body.get("local_only", False)
            entry_url = None

            if not local_only:
                photos = pick_photos(config.PHOTOS_DIR, count=config.PHOTOS_PER_ARTICLE)
                pub = VcPublisher(token=config.VC_TOKEN, base_url=config.VC_BASE_URL)
                result = pub.publish_article(
                    article=article,
                    image_paths=photos,
                    subsite_id=config.VC_SUBSITE_ID,
                    publish=publish,
                )
                if result:
                    entry_url = result.get("url") or f"https://vc.ru/id/{result.get('id','?')}"

            tasks[task_id] = {"status": "done", "url": entry_url, "filename": filepath.name}

        except Exception as e:
            tasks[task_id] = {"status": "error", "error": str(e)}

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"task_id": task_id})


@app.route("/api/task/<task_id>")
def api_task(task_id):
    return jsonify(tasks.get(task_id, {"status": "unknown"}))


@app.route("/api/publish", methods=["POST"])
def api_publish():
    body = request.get_json()
    filename = body.get("filename")
    path = ARTICLES_DIR / filename
    if not path.exists():
        return jsonify({"ok": False, "error": "Файл не найден"})

    try:
        html = path.read_text(encoding="utf-8")
        json_m = re.search(r"<!--JSON:(.*?)-->", html, re.S)
        if not json_m:
            return jsonify({"ok": False, "error": "Нет данных статьи в файле"})

        import json as _json
        from generator import GeneratedArticle
        data = _json.loads(json_m.group(1))
        article = GeneratedArticle(
            title=data["title"],
            intro=data.get("intro", ""),
            sections=data.get("sections", []),
            conclusion=data.get("conclusion", ""),
            meta_description=data.get("meta_description", ""),
            keywords=data.get("keywords", []),
        )

        photos = pick_photos(config.PHOTOS_DIR, count=config.PHOTOS_PER_ARTICLE)
        pub = VcPublisher(token=config.VC_TOKEN, base_url=config.VC_BASE_URL)
        result = pub.publish_article(article=article, image_paths=photos,
                                     subsite_id=config.VC_SUBSITE_ID, publish=True)
        if result:
            url = result.get("url") or f"https://vc.ru/id/{result.get('id','?')}"
            return jsonify({"ok": True, "url": url})
        return jsonify({"ok": False, "error": "Ошибка публикации — проверьте токен VC.RU"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/search-web", methods=["POST"])
def api_search_web():
    import urllib.parse
    query = (request.get_json() or {}).get("query", "").strip()
    if not query:
        return jsonify({"results": []})
    try:
        import requests as _req
        resp = _req.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        data = resp.json()
        results = []
        if data.get("AbstractText"):
            results.append({"title": data.get("Heading", query), "snippet": data["AbstractText"]})
        for r in data.get("RelatedTopics", []):
            if isinstance(r, dict) and r.get("Text"):
                results.append({"title": r["Text"][:80], "snippet": r["Text"]})
            if len(results) >= 8:
                break
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"results": [], "error": str(e)})


@app.route("/api/search-rutube", methods=["POST"])
def api_search_rutube():
    from photos import search_rutube_videos
    query = (request.get_json() or {}).get("query", "").strip()
    if not query:
        return jsonify({"videos": []})
    videos = search_rutube_videos(query, count=6)
    return jsonify({"videos": videos})


@app.route("/api/yandex-disk", methods=["POST"])
def api_yandex_disk():
    from photos import list_yandex_disk_images
    url = (request.get_json() or {}).get("url", "").strip()
    if not url:
        return jsonify({"images": []})
    try:
        images = list_yandex_disk_images(url)
        return jsonify({"images": images})
    except Exception as e:
        return jsonify({"images": [], "error": str(e)})


@app.route("/manifest.json")
def manifest():
    data = {
        "name": "VC.RU SEO Bot",
        "short_name": "SEO Bot",
        "description": "Автогенерация SEO-статей для VC.RU",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": "#2563eb",
        "lang": "ru",
        "icons": [
            {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"},
        ]
    }
    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/json")


@app.route("/icon.svg")
def icon():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="20" fill="#2563eb"/>
  <text y="62" x="50" text-anchor="middle" font-size="52" font-family="Arial,sans-serif" font-weight="bold" fill="white">S</text>
  <text y="85" x="50" text-anchor="middle" font-size="18" font-family="Arial,sans-serif" fill="#93c5fd">SEO</text>
</svg>"""
    return Response(svg, mimetype="image/svg+xml")


@app.route("/sw.js")
def service_worker():
    sw = """
const CACHE = 'seo-bot-v1';
self.addEventListener('install', e => e.waitUntil(
  caches.open(CACHE).then(c => c.addAll(['/']))
));
self.addEventListener('fetch', e => {
  if (e.request.url.includes('/api/')) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
"""
    return Response(sw, mimetype="application/javascript")


if __name__ == "__main__":
    import webbrowser, time

    def open_browser():
        time.sleep(1.2)
        webbrowser.open("http://localhost:5000")

    threading.Thread(target=open_browser, daemon=True).start()

    print("\n" + "="*50)
    print("  VC.RU SEO Bot — Веб-интерфейс")
    print("  Открываем браузер: http://localhost:5000")
    print("  Закрыть бот: Ctrl+C в этом окне")
    print("="*50 + "\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
