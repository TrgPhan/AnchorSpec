$ErrorActionPreference = 'Stop'
$presentationPath = Join-Path $PSScriptRoot 'results\t\AnchorSpec_Bang_chung_va_gioi_han_20261105.pptx'
$pdfPath = Join-Path $PSScriptRoot 'results\t\AnchorSpec_Bang_chung_va_gioi_han_20261105.pdf'
$powerPoint = New-Object -ComObject PowerPoint.Application
$initialCount = $powerPoint.Presentations.Count
$presentation = $null
try {
    $presentation = $powerPoint.Presentations.Open($presentationPath, $true, $false, $false)
    $presentation.SaveAs($pdfPath, 32)
    Write-Output $pdfPath
}
finally {
    if ($null -ne $presentation) { $presentation.Close() }
    if ($initialCount -eq 0) { $powerPoint.Quit() }
}
