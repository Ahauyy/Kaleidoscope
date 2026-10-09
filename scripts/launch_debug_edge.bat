@echo off
title Kaleidoscope Flow Studio - Browser Launcher (Edge CDP 9222)
echo =====================================================================
echo  KALEIDOSCOPE FLOW STUDIO - 1-CLICK REMOTE DEBUG LAUNCHER (EDGE)
echo =====================================================================
echo Opening Microsoft Edge on Remote Debugging Port 9222...
echo You can log in to Google Flow once; your session will stay saved!
echo =====================================================================

start msedge.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\FlowStudio_EdgeProfile" https://flow.google.com
echo Edge has been launched. You can now run 'python flow_runner.py run'.
