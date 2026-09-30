# -*- coding: utf-8 -*-
"""check_pdf.py —— 生成后的 PDF 客观自检（**禁止用肉眼代替**）

用法：
    python3 check_pdf.py <pdf> [字体路径...]

检查项：
  1. 页数、每页文本量
  2. **空白页**（多于 1 页时，某页文本过少）
  3. **缺字**：把 PDF 文本里的中文逐字去字体 cmap 里查，缺哪个报哪个
     （比"渲染成图用眼睛看"可靠 —— 缺字会渲染成方框，但文本层看不出）

退出码：0 = 未发现问题；1 = 发现问题（含缺字 / 空白页）。
"""
import sys
import os
import fitz  # PyMuPDF

DEFAULT_FONTS = ['/usr/local/share/fonts/custom/NotoSansSC-Regular.ttf',
                 '/usr/local/share/fonts/custom/NotoSansSC-Bold.ttf']


def cmap_cover(paths):
    """合并若干字体文件的 cmap（已覆盖的字符码位集合）。"""
    cov = set()
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    for p in paths:
        if not os.path.exists(p):
            continue
        try:
            f = TTFont(p, fontNumber=0, lazy=True)
            for t in f['cmap'].tables:
                cov |= set(t.cmap.keys())
        except Exception:
            continue
    return cov or None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    pdf = sys.argv[1]
    fonts = sys.argv[2:] or DEFAULT_FONTS
    cov = cmap_cover(fonts)
    doc = fitz.open(pdf)
    problems = []

    print('页数 = %d' % doc.page_count)
    for i, pg in enumerate(doc):
        t = pg.get_text()
        imgs = len(pg.get_images())
        flag = ''
        if doc.page_count > 1 and len(t.strip()) < 30:
            flag = '  ⚠️ 疑似空白页'
            problems.append('第 %d 页疑似空白页（文本仅 %d 字）' % (i + 1, len(t.strip())))
        print('  第 %d 页：文本 %d 字，图片 %d 张%s' % (i + 1, len(t.strip()), imgs, flag))

    if cov is None:
        print('（未安装 fontTools，跳过缺字筛查）')
    else:
        miss = {}
        for i, pg in enumerate(doc):
            for ch in pg.get_text():
                # 只关心 CJK 区，拉丁字母/数字由 Helvetica 兜底
                if ord(ch) > 0x2E80 and ord(ch) not in cov:
                    miss.setdefault(ch, i + 1)
        if miss:
            for ch, p in miss.items():
                problems.append('第 %d 页缺字：%r (U+%04X)' % (p, ch, ord(ch)))
            print('❌ 缺字 %d 个' % len(miss))
        else:
            print('✅ 无缺字')

    if problems:
        print('\n发现问题：')
        for p in problems:
            print('  ✗', p)
        return 1
    print('\n✅ 未发现问题')
    return 0


if __name__ == '__main__':
    sys.exit(main())
