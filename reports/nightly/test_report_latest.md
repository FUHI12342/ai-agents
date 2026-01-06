============================= test session starts =============================
platform win32 -- Python 3.10.6, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\FHiro\Projects\ai-agents
configfile: pytest.ini
plugins: anyio-4.12.0
collected 12 items / 3 errors

=================================== ERRORS ====================================
_______ ERROR collecting apps/voice-changer/tests/test_voice_changer.py _______
ImportError while importing test module 'C:\Users\FHiro\Projects\ai-agents\apps\voice-changer\tests\test_voice_changer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
apps\voice-changer\tests\test_voice_changer.py:5: in <module>
    from scipy.io import wavfile
E   ModuleNotFoundError: No module named 'scipy'
______________________ ERROR collecting test_all_log.txt ______________________
..\..\AppData\Local\Programs\Python\Python310\lib\pathlib.py:1135: in read_text
    return f.read()
..\..\AppData\Local\Programs\Python\Python310\lib\codecs.py:322: in decode
    (result, consumed) = self._buffer_decode(data, self.errors, final)
E   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
_________________ ERROR collecting test_voice_changer_log.txt _________________
..\..\AppData\Local\Programs\Python\Python310\lib\pathlib.py:1135: in read_text
    return f.read()
..\..\AppData\Local\Programs\Python\Python310\lib\codecs.py:322: in decode
    (result, consumed) = self._buffer_decode(data, self.errors, final)
E   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
=========================== short test summary info ===========================
ERROR apps/voice-changer/tests/test_voice_changer.py
ERROR test_all_log.txt - UnicodeDecodeError: 'utf-8' codec can't decode byte ...
ERROR test_voice_changer_log.txt - UnicodeDecodeError: 'utf-8' codec can't de...
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!
============================== 3 errors in 0.50s ==============================
