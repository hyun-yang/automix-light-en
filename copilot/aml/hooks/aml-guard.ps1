# Windows PowerShell 5.1 / PowerShell 7. ASCII source for 5.1 compatibility.
$ErrorActionPreference = 'Stop'
try {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [Console]::InputEncoding = $utf8
    [Console]::OutputEncoding = $utf8
    $OutputEncoding = $utf8
    $reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), $utf8)
    $payload = $reader.ReadToEnd()
    # Windows PowerShell's .cmd pipeline may use the system code page.
    # JSON Unicode escapes keep the payload lossless on that path too.
    $payload = [regex]::Replace($payload, '[^\x00-\x7F]', {
        param($match)
        '\u{0:x4}' -f [int][char]$match.Value
    })
    $guardPath = Join-Path $PSScriptRoot 'aml-guard.py'
    foreach ($candidate in @('python3', 'python', 'py')) {
        $prefix = @()
        if ($candidate -eq 'py') { $prefix = @('-3') }
        try {
            $version = & $candidate @prefix -c 'import sys; print(sys.version_info[0])' 2>$null
            if ($LASTEXITCODE -ne 0 -or "$version".Trim() -ne '3') { continue }
        } catch { continue }
        # Native stderr is a valid denial reason, not a PowerShell exception.
        $ErrorActionPreference = 'Continue'
        $payload | & $candidate @prefix $guardPath
        if ($LASTEXITCODE -eq 2) { exit 2 }
        exit 0
    }
} catch { }
exit 0
