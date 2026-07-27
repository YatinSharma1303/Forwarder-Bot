# Session Compressor for Railway Deployment
# Run this in PowerShell to compress and encode your session

cd $PSScriptRoot

Write-Host "📦 Compressing session.session..." -ForegroundColor Cyan
Compress-Archive -Path .\session.session -DestinationPath .\session.zip -Force

Write-Host "✅ Compressed to session.zip" -ForegroundColor Green

Write-Host "🔐 Encoding to base64..." -ForegroundColor Cyan
$base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("session.zip"))

Write-Host "💾 Saving to session_b64.txt..." -ForegroundColor Cyan
$base64 | Out-File -Encoding utf8 session_b64.txt

$fileSize = (Get-Item session_b64.txt).Length
$stringLength = $base64.Length

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "✅ DONE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "File created: session_b64.txt" -ForegroundColor White
Write-Host "String length: $stringLength characters" -ForegroundColor White
Write-Host "File size: $fileSize bytes" -ForegroundColor White
Write-Host ""
Write-Host "Add to Railway:" -ForegroundColor Cyan
Write-Host "  Name: SESSION_B64_ZIP" -ForegroundColor White
Write-Host "  Value: [contents of session_b64.txt]" -ForegroundColor White
Write-Host ""
if ($stringLength -lt 32768) {
    Write-Host "✅ String fits Railway limit! Ready to deploy." -ForegroundColor Green
} else {
    Write-Host "⚠️ String still too large. Need alternative method." -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Opening file..." -ForegroundColor Cyan
Start-Process notepad session_b64.txt
