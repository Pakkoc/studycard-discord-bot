$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(\.exe)?$' -and $_.CommandLine -match 'src\\bot\.py' }
if ($procs) {
    foreach ($p in $procs) {
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
            Write-Output "Stopped PID $($p.ProcessId)"
        }
        catch {
            Write-Output "Failed to stop PID $($p.ProcessId): $($_.Exception.Message)"
        }
    }
}
else {
    Write-Output "No matching bot process found."
}


