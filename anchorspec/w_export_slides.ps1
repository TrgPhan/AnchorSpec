$ErrorActionPreference = 'Stop'
$presentationPath = Join-Path $PSScriptRoot 'results\w\AnchorSpec_Bang_chung_20261104.pptx'
$pdfPath = Join-Path $PSScriptRoot 'results\w\AnchorSpec_Bang_chung_20261104.pdf'
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
