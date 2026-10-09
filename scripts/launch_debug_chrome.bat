@echo off
title Kaleidoscope Flow Studio - Browser Launcher (Chrome CDP 9222)
echo =====================================================================
echo  KALEIDOSCOPE FLOW STUDIO - 1-CLICK REMOTE DEBUG LAUNCHER (CHROME)
echo =====================================================================
echo Opening Google Chrome on Remote Debugging Port 9222...
echo You can log in to Google Flow once; your session will stay saved!
echo =====================================================================

start chrome.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\FlowStudio_ChromeProfile" https://flow.google.com
echo Chrome has been launched. You can now run 'python flow_runner.py run'.
