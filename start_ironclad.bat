@echo off

cd /d C:\IRONCLAD_V31\RUNTIME

start "STOCK_ENGINE" cmd /k python run_stock.py
start "COIN_ENGINE"  cmd /k python run_coin.py