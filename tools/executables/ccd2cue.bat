@echo off
setlocal

REM First argument is input file (unnamed)
set "INPUT=%~1"
shift

REM Parse other arguments
:parse
if "%~1"=="" goto done
if "%~1"=="-o" (
    set "OUTPUT=%~2"
    shift
    shift
    goto parse
)
echo Unknown argument: %~1
exit /b 1

:done

REM Validate inputs
if not defined INPUT (
    echo Error: Missing input_file
    exit /b 1
)

if not defined OUTPUT (
    echo Error: Missing -o output_file
    exit /b 1
)


REM Extract filename from OUTPUT using FOR loop
for %%F in ("%OUTPUT%") do set "FILENAME=%%~nxF"
REM Replace .cue extension with .bin for the image
set "IMAGE=%FILENAME:.cue=.bin%"

REM Run the conversion tool
myccd2cue.exe --input "%INPUT%" --output "%OUTPUT%" --image "%IMAGE%"

endlocal