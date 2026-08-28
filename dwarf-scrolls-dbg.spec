# -*- mode: python ; coding: utf-8 -*-
# dwarf-scrolls 调试构建（真实冒烟协议）
a = Analysis(
    ['G:/repos/dwarf-scrolls/main.py'],
    pathex=['G:/Temp/rebuild/pkgroot'],
    binaries=[],
    datas=[
        ('F:/Python314/Lib/tkinter/*.py', 'tkinter'),
        ('G:/repos/dwarf-scrolls/content', 'content'),
        ('G:/repos/dwarf-scrolls/content', 'dwarf_scrolls/content'),
    ],
    hiddenimports=[

    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch','cupy','dask','jax','jaxlib','ndonnx','sparse','sqlalchemy','matplotlib','IPython','Cython','setuptools','traitlets','jedi','pygments','yt_dlp','playwright','botocore','boto3','transformers','tokenizers','pyarrow','llvmlite','numba','scipy','sklearn','scikit-learn','imageio','imageio_ffmpeg','tensorflow','keras','moviepy','sympy','statsmodels','nltk','networkx','PyQt5','PyQt6','PySide2','PySide6','pymongo','bson'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='dwarf-scrolls-dbg',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    contents_directory='.',
)