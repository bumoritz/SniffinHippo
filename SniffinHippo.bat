if not "%minimized%"=="" goto :minimized
set minimized=true
start /min cmd /C "%~dpnx0"
goto :EOF
:minimized

cd C:\\Setup\\SniffinHippo
python SniffinHippo.py