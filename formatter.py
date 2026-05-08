#!/usr/bin/env python3
"""Fixed-width text formatter with hanging indent (stdlib only, Python 3.13+)."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import unicodedata


# ─────────────────────────────────────────────────────────────────────────────
#  Display-width helpers
#
#  Rules (matching common CJK typewriter conventions):
#    · CJK ideographs (汉字, kana, …) → 2 columns
#    · CJK punctuation (。，、！？…) → 1 column  ("标点算半个字")
#    · Everything else (ASCII, half-width) → 1 column
# ─────────────────────────────────────────────────────────────────────────────

def _cw(ch: str) -> int:
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ('W', 'F'):
        # Punctuation / symbols in full-width slots count as half (1 col)
        if unicodedata.category(ch)[0] in ('P', 'S'):
            return 1
        return 2
    return 1


def _sw(s: str) -> int:
    return sum(_cw(c) for c in s)


# ─────────────────────────────────────────────────────────────────────────────
#  Formatting logic
# ─────────────────────────────────────────────────────────────────────────────

def wrap_paragraph(para: str, width: int, indent: float, space: str) -> str:
    """
    Wrap one paragraph with hanging indent.
    First line fills `width` columns; continuation lines are prefixed with
    `indent` × `space` (fractional .5 appends one half-width space) and
    fill the remaining columns.
    """
    para = para.strip()
    if not para:
        return ''

    pad = space * int(indent) + (' ' if indent % 1 >= 0.5 else '')
    pad_w = _sw(pad)
    body_w = max(width - pad_w, 1)

    lines: list[str] = []
    buf, buf_w = '', 0
    first = True

    for ch in para:
        cw = _cw(ch)
        cap = width if first else body_w
        if buf_w + cw > cap and buf:
            lines.append(buf if first else pad + buf)
            first = False
            buf, buf_w = ch, cw
        else:
            buf += ch
            buf_w += cw

    if buf:
        lines.append(buf if first else pad + buf)

    return '\n'.join(lines)


def format_text(text: str, width: int, indent: float, fullwidth: bool) -> str:
    space = '　' if fullwidth else ' '
    return '\n'.join(
        wrap_paragraph(p, width, indent, space) for p in text.split('\n')
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Reusable scrolled-text container
# ─────────────────────────────────────────────────────────────────────────────

class _ST(tk.Frame):
    def __init__(self, parent, hscroll: bool = False, **kw):
        super().__init__(parent)
        self.text = tk.Text(self, **kw)
        ys = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=ys.set)
        if hscroll:
            xs = ttk.Scrollbar(self, orient='horizontal', command=self.text.xview)
            self.text.configure(xscrollcommand=xs.set)
            xs.pack(side='bottom', fill='x')
        ys.pack(side='right', fill='y')
        self.text.pack(fill='both', expand=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Application
# ─────────────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('固定宽度格式化器')
        self.geometry('740x680')
        self.minsize(500, 520)
        self._mono = self._pick_font()
        self._build()

    # ── font detection ────────────────────────────────────────────────────────

    @staticmethod
    def _pick_font() -> tuple:
        try:
            from tkinter import font as tkf
            avail = set(tkf.families())
            for name in ('NSimSun', 'SimSun', 'Courier New', 'Consolas'):
                if name in avail:
                    return (name, 11)
        except Exception:
            pass
        return ('Courier New', 11)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build(self):
        self._statusbar()    # pack bottom first so expanding panels don't crowd it
        self._settings()
        self._input_panel()
        self._button_bar()
        self._output_panel()

    def _settings(self):
        sf = ttk.LabelFrame(self, text='设置', padding=8)
        sf.pack(fill='x', padx=10, pady=(8, 2))

        ttk.Label(sf, text='行宽（汉字数）:').grid(row=0, column=0, sticky='w')
        self.v_width = tk.IntVar(value=24)
        ttk.Spinbox(sf, from_=2, to=200, textvariable=self.v_width,
                    width=6).grid(row=0, column=1, padx=(2, 16))

        ttk.Label(sf, text='悬挂缩进（字符数）:').grid(row=0, column=2, sticky='w')
        self.v_indent = tk.DoubleVar(value=3.5)
        ttk.Spinbox(sf, from_=0.0, to=40.0, increment=0.5, format='%.1f',
                    textvariable=self.v_indent,
                    width=6).grid(row=0, column=3, padx=(2, 16))

        ttk.Label(sf, text='缩进空格:').grid(row=0, column=4, sticky='w')
        self.v_fw = tk.BooleanVar(value=True)
        ttk.Radiobutton(sf, text='全角', variable=self.v_fw, value=True).grid(row=0, column=5, padx=2)
        ttk.Radiobutton(sf, text='半角', variable=self.v_fw, value=False).grid(row=0, column=6, padx=2)

        ttk.Label(sf, text='（标点计 1 列）', foreground='gray').grid(
            row=0, column=7, padx=(12, 0), sticky='w')

    def _input_panel(self):
        f = ttk.LabelFrame(self, text='输入', padding=4)
        f.pack(fill='both', expand=True, padx=10, pady=4)
        st = _ST(f, wrap='word', height=9, undo=True, font=self._mono)
        st.pack(fill='both', expand=True)
        self.inp = st.text
        self.inp.bind('<Control-Return>', lambda _: self._format())

    def _button_bar(self):
        bf = ttk.Frame(self)
        bf.pack(fill='x', padx=10, pady=4)
        ttk.Button(bf, text='格式化  Ctrl+Enter', command=self._format,
                   width=18).pack(side='left', padx=4)
        ttk.Button(bf, text='粘贴剪贴板', command=self._paste,
                   width=10).pack(side='left', padx=4)
        ttk.Button(bf, text='清空', command=self._clear,
                   width=6).pack(side='left', padx=4)
        ttk.Button(bf, text='保存为 TXT', command=self._save).pack(side='right', padx=4)
        ttk.Button(bf, text='复制输出', command=self._copy).pack(side='right', padx=4)

    def _output_panel(self):
        f = ttk.LabelFrame(self, text='输出', padding=4)
        f.pack(fill='both', expand=True, padx=10, pady=(2, 6))
        st = _ST(f, hscroll=True, wrap='none', height=9,
                 state='disabled', font=self._mono)
        st.pack(fill='both', expand=True)
        self.out = st.text

    def _statusbar(self):
        self.status = tk.StringVar(value='就绪')
        ttk.Label(self, textvariable=self.status, relief='sunken', anchor='w',
                  padding=(6, 2)).pack(fill='x', side='bottom')

    # ── actions ───────────────────────────────────────────────────────────────

    def _format(self, _event=None):
        raw = self.inp.get('1.0', 'end-1c')
        if not raw.strip():
            self.status.set('输入为空，请先粘贴文字')
            return
        try:
            hz  = int(self.v_width.get())
            ind = float(self.v_indent.get())
        except (ValueError, tk.TclError):
            messagebox.showerror('参数错误', '行宽须为整数，缩进须为数字')
            return
        w = hz * 2  # 1汉字 = 2显示列
        result = format_text(raw, w, ind, bool(self.v_fw.get()))
        self._set_output(result)
        n  = result.count('\n') + 1
        sp = '全角' if self.v_fw.get() else '半角'
        self.status.set(f'完成 — {n} 行 | 宽度 {hz} 汉字({w} 列) | 缩进 {ind} 字符 ({sp}空格)')

    def _paste(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            self.status.set('剪贴板为空或内容无法读取')
            return
        self.inp.delete('1.0', 'end')
        self.inp.insert('1.0', text)
        self.status.set(f'已粘贴 {len(text)} 个字符')

    def _clear(self):
        self.inp.delete('1.0', 'end')
        self._set_output('')
        self.status.set('已清空')

    def _copy(self):
        content = self.out.get('1.0', 'end-1c')
        if not content:
            self.status.set('输出为空，请先格式化')
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.status.set('已复制到剪贴板')

    def _save(self):
        content = self.out.get('1.0', 'end-1c')
        if not content:
            self.status.set('输出为空，请先格式化')
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')],
        )
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.status.set(f'已保存 → {path}')
        except OSError as e:
            messagebox.showerror('保存失败', str(e))

    def _set_output(self, text: str):
        self.out.configure(state='normal')
        self.out.delete('1.0', 'end')
        if text:
            self.out.insert('1.0', text)
        self.out.configure(state='disabled')


if __name__ == '__main__':
    App().mainloop()
