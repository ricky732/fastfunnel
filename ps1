<#
.SYNOPSIS
  Lancia Dymola in batch (senza GUI), simula SimpleTest.FirstOrder,
  confronta il valore finale con quello atteso e restituisce exit code 0/1.
  Pensato per girare sia in locale sia in un job GitLab CI.

.EXAMPLE
  .\Run-DymolaTest.ps1
  .\Run-DymolaTest.ps1 -DymolaExe "C:\Program Files\Dymola 2025x Refresh 1\bin64\Dymola.exe"
#>
param(
    [string]$DymolaExe  = $env:DYMOLA_EXE,   # opzionale: percorso esplicito
    [int]   $TimeoutSec = 600
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$out  = Join-Path $root 'out'

# --- 1. Cartella risultati pulita -------------------------------------------
New-Item -ItemType Directory -Force -Path $out | Out-Null
Get-ChildItem $out | Remove-Item -Recurse -Force

# --- 2. Trova Dymola.exe ------------------------------------------------------
if (-not $DymolaExe) {
    $DymolaExe = Get-ChildItem 'C:\Program Files\Dymola*\bin64\Dymola.exe' -ErrorAction SilentlyContinue |
                 Sort-Object FullName -Descending |
                 Select-Object -First 1 -ExpandProperty FullName
}
if (-not $DymolaExe -or -not (Test-Path $DymolaExe)) {
    throw "Dymola.exe non trovato. Passa -DymolaExe oppure imposta la variabile DYMOLA_EXE."
}
Write-Host "Dymola: $DymolaExe"

# --- 3. Genera lo script .mos (Dymola vuole slash '/') ----------------------
$moFile = (Join-Path $root 'SimpleTest.mo') -replace '\\', '/'
$outDir = $out -replace '\\', '/'

$mos = @"
openModel("$moFile", changeDirectory=false);
cd("$outDir");
ok := simulateModel("SimpleTest.FirstOrder", stopTime=5, method="dassl", tolerance=1e-6, resultFile="FirstOrder");
n := readTrajectorySize("FirstOrder.mat");
traj := readTrajectory("FirstOrder.mat", {"y"}, n);
yEnd := traj[1, n];
yRef := 1 - exp(-5);
passed := ok and abs(yEnd - yRef) < 1e-4;
Modelica.Utilities.Streams.print(if passed then "PASS" else "FAIL", "status.txt");
Modelica.Utilities.Streams.print("yEnd=" + String(yEnd) + " yRef=" + String(yRef), "status.txt");
savelog("dymola_log.txt");
exit();
"@

$mosPath = Join-Path $out 'run.mos'
Set-Content -Path $mosPath -Value $mos -Encoding ascii

# --- 4. Esegui Dymola senza finestra e aspetta -------------------------------
$sw = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $DymolaExe -ArgumentList '-nowindow', "`"$mosPath`"" -PassThru
if (-not $proc.WaitForExit($TimeoutSec * 1000)) {
    $proc.Kill()
    Write-Host "TIMEOUT dopo $TimeoutSec s"
    exit 2
}
Write-Host ("Dymola terminato in {0:N1} s" -f $sw.Elapsed.TotalSeconds)

# --- 5. Valuta il risultato (l'exit code di Dymola non è affidabile) --------
$statusFile = Join-Path $out 'status.txt'
$logFile    = Join-Path $out 'dymola_log.txt'

if (Test-Path $logFile) {
    Write-Host "----- log Dymola -----"
    Get-Content $logFile | Write-Host
    Write-Host "----------------------"
}

if (-not (Test-Path $statusFile)) {
    Write-Host "ERRORE: status.txt non creato (Dymola si è fermato prima? licenza?)"
    exit 3
}

$status = Get-Content $statusFile
$status | Write-Host
if ($status[0] -eq 'PASS') { exit 0 } else { exit 1 }
