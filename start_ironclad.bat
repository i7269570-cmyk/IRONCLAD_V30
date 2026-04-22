@echo off
cd /d "C:\IRONCLAD_V31"

start "STOCK_ENGINE" cmd /k "C:\Users\PC\AppData\Local\Programs\Python\Python310\python.exe RUNTIME\run_stock.py"
start "COIN_ENGINE" cmd /k "C:\Users\PC\AppData\Local\Programs\Python\Python310\python.exe RUNTIME\run_coin.py"