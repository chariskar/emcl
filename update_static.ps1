cd "src-frontend"
bunx vite build
Copy-Item dist/* ../src/static/ -Recurse -Force
Remove-Item dist -Recurse -Force
cd ..