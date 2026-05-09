"use strict";

// ─── Display-width helpers ────────────────────────────────────────────────────
//
//  Same rules as the Python version:
//    CJK ideographs / kana / hangul  → 2 columns
//    CJK / fullwidth punctuation     → 1 column
//    Everything else                 → 1 column

function _cw(ch) {
    const cp = ch.codePointAt(0);
    if (cp === 0x3000) return 2;                    // ideographic space
    if (cp >= 0x4E00 && cp <= 0x9FFF)  return 2;   // CJK Unified Ideographs
    if (cp >= 0x3400 && cp <= 0x4DBF)  return 2;   // CJK Extension A
    if (cp >= 0x20000 && cp <= 0x3134F) return 2;  // CJK Extensions B-G
    if (cp >= 0xF900 && cp <= 0xFAFF)  return 2;   // CJK Compatibility Ideographs
    if (cp >= 0x3041 && cp <= 0x3096)  return 2;   // Hiragana
    if (cp >= 0x30A1 && cp <= 0x30FA)  return 2;   // Katakana
    if (cp >= 0x31F0 && cp <= 0x31FF)  return 2;   // Katakana Phonetic Extensions
    if (cp >= 0xAC00 && cp <= 0xD7A3)  return 2;   // Hangul Syllables
    if (cp >= 0x1100 && cp <= 0x11FF)  return 2;   // Hangul Jamo
    if (cp >= 0xA960 && cp <= 0xA97F)  return 2;   // Hangul Jamo Extended-A
    if (cp >= 0xD7B0 && cp <= 0xD7FF)  return 2;   // Hangul Jamo Extended-B
    if (cp >= 0x3105 && cp <= 0x312F)  return 2;   // Bopomofo
    if (cp >= 0x31A0 && cp <= 0x31BB)  return 2;   // Bopomofo Extended
    if (cp >= 0xFE30 && cp <= 0xFE4F)  return 2;   // CJK Compatibility Forms
    if (cp >= 0x3200 && cp <= 0x32FF)  return 2;   // Enclosed CJK Letters & Months
    if (cp >= 0x3300 && cp <= 0x33FF)  return 2;   // CJK Compatibility
    return 1;
}

function _sw(s) {
    let w = 0;
    for (const ch of s) w += _cw(ch);  // for...of iterates code points, not code units
    return w;
}

// ─── Formatting logic ─────────────────────────────────────────────────────────

// Characters forbidden at the start of a line (行首禁则)
const LINE_START_FORBIDDEN = new Set([...'。，、！？；：）】』」…—～·》〕〉']);

// Paragraph starting with 2+ non-space chars + colon → speech turn (first line flush)
const SPEECH_RE = /^\S{2,}[：:]/;

function wrapParagraph(para, width, indent, space) {
    para = para.trimEnd();
    if (!para.trim()) return '';

    const pad = space.repeat(Math.floor(indent)) + (indent % 1 >= 0.5 ? ' ' : '');
    const padW = _sw(pad);
    const bodyW = Math.max(width - padW, 1);

    // \s in JS regex matches U+3000 (ideographic space), so this detects any leading whitespace
    const stripped = para.replace(/^\s+/, '');
    const hasExplicitIndent = para.length !== stripped.length;
    const isSpeech = SPEECH_RE.test(stripped);
    // Continuation paragraphs: every line (including the first) gets the pad
    const allIndented = !isSpeech && !hasExplicitIndent;

    const lines = [];
    let buf = '', bufW = 0;
    let first = !allIndented;   // false → pad applied from the very first line

    for (const ch of para) {
        const cw = _cw(ch);
        const cap = first ? width : bodyW;
        if (bufW + cw > cap && buf) {
            if (LINE_START_FORBIDDEN.has(ch)) {
                // Push forbidden-at-line-start punctuation onto the current line
                buf += ch;
                lines.push(first ? buf : pad + buf);
                first = false;
                buf = ''; bufW = 0;
            } else {
                lines.push(first ? buf : pad + buf);
                first = false;
                buf = ch; bufW = cw;
            }
        } else {
            buf += ch;
            bufW += cw;
        }
    }
    if (buf) lines.push(first ? buf : pad + buf);

    return lines.join('\n');
}

function formatText(text, width, indent, fullwidth) {
    const space = fullwidth ? '　' : ' ';
    return text.split('\n').map(p => wrapParagraph(p, width, indent, space)).join('\n');
}

// ─── UI helpers ───────────────────────────────────────────────────────────────

const inp       = document.getElementById('inp');
const out       = document.getElementById('out');
const statusBar = document.getElementById('statusbar');

function setStatus(msg) { statusBar.textContent = msg; }

function getParams() {
    const hz       = parseInt(document.getElementById('v-width').value,   10);
    const indent   = parseFloat(document.getElementById('v-indent').value);
    const fullwidth = document.querySelector('input[name="space"]:checked').value === 'full';
    return { hz, indent, fullwidth };
}

// ─── Actions ─────────────────────────────────────────────────────────────────

function doFormat() {
    const raw = inp.value;
    if (!raw.trim()) { setStatus('输入为空，请先粘贴文字'); return; }
    const { hz, indent, fullwidth } = getParams();
    if (!Number.isFinite(hz) || !Number.isFinite(indent)) {
        alert('行宽须为整数，缩进须为数字'); return;
    }
    const w = hz * 2;
    const result = formatText(raw, w, indent, fullwidth);
    out.value = result;
    const lineCount = (result.match(/\n/g) || []).length + 1;
    const sp = fullwidth ? '全角' : '半角';
    setStatus(`完成 — ${lineCount} 行 | 宽度 ${hz} 汉字(${w} 列) | 缩进 ${indent} 字符 (${sp}空格)`);
}

async function doPaste() {
    try {
        const text = await navigator.clipboard.readText();
        inp.value = text;
        doFormat();
    } catch {
        setStatus('无法访问剪贴板（需 HTTPS 或本地文件），请手动粘贴后按格式化');
    }
}

function doClear() {
    inp.value = '';
    out.value = '';
    setStatus('已清空');
}

async function doCopy() {
    if (!out.value) { setStatus('输出为空，请先格式化'); return; }
    try {
        await navigator.clipboard.writeText(out.value);
        setStatus('已复制到剪贴板');
    } catch {
        out.select();
        document.execCommand('copy');
        setStatus('已复制到剪贴板');
    }
}

function doSave() {
    if (!out.value) { setStatus('输出为空，请先格式化'); return; }
    const blob = new Blob([out.value], { type: 'text/plain;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const a    = Object.assign(document.createElement('a'), { href: url, download: 'formatted.txt' });
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setStatus('已保存');
}

// ─── Event bindings ───────────────────────────────────────────────────────────

document.getElementById('btn-format').addEventListener('click', doFormat);
document.getElementById('btn-paste').addEventListener('click', doPaste);
document.getElementById('btn-clear').addEventListener('click', doClear);
document.getElementById('btn-copy').addEventListener('click', doCopy);
document.getElementById('btn-save').addEventListener('click', doSave);

document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); doFormat(); }
});

// ─── Synchronized scrolling (approximate) ────────────────────────────────────

let syncing = false;

function syncScroll(from, to) {
    if (syncing) return;
    syncing = true;
    const maxFrom = from.scrollHeight - from.clientHeight;
    const ratio   = maxFrom > 0 ? from.scrollTop / maxFrom : 0;
    to.scrollTop  = ratio * (to.scrollHeight - to.clientHeight);
    syncing = false;
}

inp.addEventListener('scroll', () => syncScroll(inp, out));
out.addEventListener('scroll', () => syncScroll(out, inp));

// ─── Draggable splitter ───────────────────────────────────────────────────────

(function () {
    const splitter = document.getElementById('splitter');
    const panelIn  = document.getElementById('panel-in');
    let dragging = false, startX = 0, startW = 0;

    splitter.addEventListener('mousedown', e => {
        dragging = true;
        startX   = e.clientX;
        startW   = panelIn.getBoundingClientRect().width;
        splitter.classList.add('active');
        document.body.style.cursor     = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    document.addEventListener('mousemove', e => {
        if (!dragging) return;
        const newW = Math.max(80, startW + e.clientX - startX);
        panelIn.style.flex = `0 0 ${newW}px`;
    });

    document.addEventListener('mouseup', () => {
        if (!dragging) return;
        dragging = false;
        splitter.classList.remove('active');
        document.body.style.cursor     = '';
        document.body.style.userSelect = '';
    });
})();
